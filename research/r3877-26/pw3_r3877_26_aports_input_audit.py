#!/usr/bin/env python3
"""R3877.26: host-only pinned Alpine musl input verification + in-memory patch audit.

Does not execute or build any musl/ARM binary, and does not contact a Kindle.
"""
import argparse
import hashlib
import io
import json
import pathlib
import re
import sys
import tarfile

MANIFEST_NAME = 'R3877_26_PINNED_MANIFEST.json'
MAX_FILE = 24 * 1024 * 1024
MAX_ARCHIVE = 24 * 1024 * 1024
MAX_UNPACKED = 120 * 1024 * 1024
MAX_MEMBERS = 14000
MAX_PATCH = 1024 * 1024

class AuditHold(Exception):
    pass

def ensure(ok, code):
    if not ok:
        raise AuditHold(code)

def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()

def valid_rel(name):
    return (isinstance(name, str) and 0 < len(name) < 256 and '\x00' not in name
            and '\\' not in name and not name.startswith('/')
            and all(part not in ('', '.', '..') for part in name.split('/')))

def load_manifest(path):
    obj=json.loads(path.read_text('utf-8'))
    ensure(obj.get('milestone')=='R3877.26','MANIFEST_MILESTONE_MISMATCH')
    ensure(obj.get('aports_commit')=='35f5eb2864e50dd4448758d31f3e2a32f733ab84','MANIFEST_SNAPSHOT_MISMATCH')
    ensure(obj.get('apkbuild_git_blob_sha1')=='b729315a72d9060cc69ba9bddec53c0691c05158','MANIFEST_APKBUILD_PIN_MISMATCH')
    entries=obj['entries']
    ensure(len(entries)==12 and len({e['name'] for e in entries})==12,'MANIFEST_ENTRY_SET')
    ensure(entries[0]['name']=='musl-1.2.6.tar.gz','MANIFEST_UPSTREAM_TARBALL')
    ensure(sum(e['role']=='patch' for e in entries)==6,'MANIFEST_PATCH_COUNT')
    for e in entries:
        ensure(valid_rel(e['name']) and '/' not in e['name'],'MANIFEST_BAD_FILENAME')
        ensure(re.fullmatch(r'[a-f0-9]{128}',e['sha512']) is not None,'MANIFEST_BAD_SHA512')
        if e['role']!='upstream_tarball':
            ensure(re.fullmatch(r'[a-f0-9]{40}',e['git_blob_sha1']) is not None,'MANIFEST_BAD_BLOB')
    return obj

def validate_apkbuild(data, manifest):
    ensure(git_blob(data)==manifest['apkbuild_git_blob_sha1'],'APKBUILD_GIT_BLOB_MISMATCH')
    text=data.decode('utf-8')
    ver=re.search(r'^pkgver=(\S+)\s*$',text,re.M)
    rel=re.search(r'^pkgrel=(\d+)\s*$',text,re.M)
    ensure(ver is not None and rel is not None and ver[1]+'-r'+rel[1]==manifest['expected_apkbuild_version'],'APKBUILD_PACKAGE_VERSION_MISMATCH')
    source=re.search(r'^source="([^\"]+)"',text,re.M|re.S)
    sums=re.search(r'^sha512sums="([^\"]+)"',text,re.M|re.S)
    ensure(source is not None and sums is not None,'APKBUILD_SOURCE_LIST_MISSING')
    declared=source[1].split()
    required=['https://musl.libc.org/releases/musl-$pkgver.tar.gz']+[e['name'] for e in manifest['entries'][1:]]
    ensure(declared==required,'APKBUILD_SOURCE_LIST_MISMATCH')
    checksum_lines=[l.strip().split() for l in sums[1].strip().splitlines() if l.strip()]
    ensure(all(len(x)==2 for x in checksum_lines),'APKBUILD_SUMS_FORMAT')
    checks=[(x[1],x[0]) for x in checksum_lines]
    ensure(checks==[(e['name'],e['sha512']) for e in manifest['entries']],'APKBUILD_CHECKSUM_LIST_MISMATCH')
    return {'source_entries':len(declared),'downstream_patch_count':sum(e['role']=='patch' for e in manifest['entries'])}

def check_inputs(source_dir, manifest):
    ensure(source_dir.is_dir(),'INPUT_DIRECTORY_MISSING')
    apkbuild=source_dir/'APKBUILD'
    ensure(apkbuild.is_file(),'APKBUILD_MISSING')
    raw=apkbuild.read_bytes()
    ensure(len(raw)<MAX_FILE,'APKBUILD_TOO_LARGE')
    apkinfo=validate_apkbuild(raw,manifest)
    rawfiles={}
    for e in manifest['entries']:
        f=source_dir/e['name']
        ensure(f.is_file(),'INPUT_MISSING_'+e['name'])
        ensure(f.stat().st_size<=(MAX_ARCHIVE if e['role']=='upstream_tarball' else MAX_PATCH if e['role']=='patch' else MAX_FILE),'INPUT_TOO_LARGE_'+e['name'])
        raw=f.read_bytes()
        ensure(hashlib.sha512(raw).hexdigest()==e['sha512'],'SHA512_MISMATCH_'+e['name'])
        if e['role']!='upstream_tarball':
            ensure(git_blob(raw)==e['git_blob_sha1'],'GIT_BLOB_MISMATCH_'+e['name'])
        rawfiles[e['name']]=raw
    return rawfiles,apkinfo

def patch_path(path):
    ensure(path.startswith(('a/','b/')) and valid_rel(path[2:]),'PATCH_UNSAFE_TARGET_PATH')
    return path[2:]

def parse_patch(raw):
    ensure(len(raw)<=MAX_PATCH,'PATCH_TOO_LARGE')
    text=raw.decode('latin-1')
    ls=text.splitlines(keepends=True)
    starts=[i for i,l in enumerate(ls) if l.startswith('diff --git ')]
    ensure(bool(starts) and len(starts)<40,'PATCH_MISSING_OR_EXCESSIVE_DIFF')
    chunks=[]
    for start,end in zip(starts,starts[1:]+[len(ls)]):
        block=ls[start:end]
        head=re.fullmatch(r'diff --git (a/[^\n]+) (b/[^\n]+)\n?',block[0])
        ensure(head is not None,'PATCH_DIFF_HEADER_MALFORMED')
        a,b=patch_path(head[1]),patch_path(head[2])
        ensure(a==b,'PATCH_RENAME_NOT_SUPPORTED')
        oi=next((i for i,z in enumerate(block[1:],1) if z.startswith('--- ')),None)
        ensure(oi is not None and oi+1<len(block),'PATCH_UNIFIED_HEADER_MISSING')
        old=block[oi][4:].strip().split('\t',1)[0]
        new=block[oi+1][4:].strip().split('\t',1)[0] if block[oi+1].startswith('+++ ') else ''
        ensure((old=='/dev/null' or patch_path(old)==a) and new.startswith('b/') and patch_path(new)==b,'PATCH_PATH_MISMATCH')
        create=old=='/dev/null'
        idx=oi+2
        hunks=[]
        while idx<len(block):
            if not block[idx].startswith('@@ '):
                if hunks:
                    break
                idx+=1
                continue
            m=re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',block[idx])
            ensure(m is not None,'PATCH_HUNK_HEADER_MALFORMED')
            oldstart,oldlen,newstart,newlen=int(m[1]),int(m[2] or '1'),int(m[3]),int(m[4] or '1')
            idx+=1
            oldchunk=[];newchunk=[];oc=nc=0
            while oc<oldlen or nc<newlen:
                ensure(idx<len(block),'PATCH_HUNK_TRUNCATED')
                line=block[idx];idx+=1
                ensure(line.startswith((' ','+','-')) and line.endswith('\n'),'PATCH_HUNK_UNSUPPORTED_LINE')
                if line[0] in (' ','-'): oldchunk.append(line[1:]);oc+=1
                if line[0] in (' ','+'): newchunk.append(line[1:]);nc+=1
                ensure(oc<=oldlen and nc<=newlen,'PATCH_HUNK_COUNTS_OVERFLOW')
            hunks.append((oldstart,oldlen,newstart,newlen,oldchunk,newchunk))
        ensure(bool(hunks),'PATCH_NO_HUNKS')
        chunks.append((b,create,hunks))
    return chunks

def tar_source_files(targz, wanted):
    ensure(len(targz)<MAX_ARCHIVE,'SOURCE_TARBALL_TOO_LARGE')
    contents={}
    seen=set();total=0
    try:
        with tarfile.open(fileobj=io.BytesIO(targz),mode='r:gz') as tf:
            members=tf.getmembers()
            ensure(len(members)<=MAX_MEMBERS,'SOURCE_TARBALL_TOO_MANY_MEMBERS')
            for m in members:
                name=m.name.removeprefix('./').rstrip('/')
                ensure(valid_rel(name),'SOURCE_TARBALL_UNSAFE_PATH')
                ensure(name not in seen,'SOURCE_TARBALL_DUPLICATE_PATH')
                seen.add(name)
                ensure(name=='musl-1.2.6' and m.isdir() or name.startswith('musl-1.2.6/'),'SOURCE_TARBALL_BAD_PREFIX')
                ensure(m.isfile() or m.isdir() or m.issym(),'SOURCE_TARBALL_UNSUPPORTED_MEMBER_TYPE')
                if m.isfile():
                    ensure(0<=m.size<=MAX_FILE,'SOURCE_TARBALL_MEMBER_TOO_LARGE')
                    total+=m.size
                    ensure(total<=MAX_UNPACKED,'SOURCE_TARBALL_UNPACKED_TOO_LARGE')
                short=name[len('musl-1.2.6/'):]
                if short in wanted:
                    ensure(m.isfile(),'PATCH_TARGET_NOT_REGULAR_FILE')
                    contents[short]=tf.extractfile(m).read()
    except (tarfile.TarError,OSError,EOFError) as e:
        raise AuditHold('SOURCE_TARBALL_PARSE_ERROR') from e
    ensure(len(contents)==len(wanted),'SOURCE_PATCH_TARGET_MISSING')
    return contents,len(members)

def apply_patch_chunks(chunks, contents):
    changes=[]
    for path,create,hunks in chunks:
        if create:
            ensure(path not in contents,'PATCH_CREATE_TARGET_EXISTS')
            buf=[]
        else:
            ensure(path in contents,'PATCH_TARGET_MISSING')
            buf=contents[path].decode('latin-1').splitlines(keepends=True)
        delta=0
        for oldstart,oldlen,newstart,newlen,oldchunk,newchunk in hunks:
            pos=(oldstart-1 if oldstart else 0)+delta
            ensure(0<=pos<=len(buf) and buf[pos:pos+len(oldchunk)]==oldchunk,'PATCH_CONTEXT_NOT_EXACT')
            ensure(len(oldchunk)==oldlen and len(newchunk)==newlen,'PATCH_HUNK_COUNT_MISMATCH')
            buf[pos:pos+len(oldchunk)]=newchunk
            delta+=len(newchunk)-len(oldchunk)
        contents[path]=''.join(buf).encode('latin-1')
        changes.append(path)
    return changes

def inspect_source(targz, patches):
    parsed=[(name,parse_patch(raw)) for name,raw in patches]
    existing={path for _,diffs in parsed for path,create,_ in diffs if not create}
    source,count=tar_source_files(targz,existing)
    touched=[];summary=[]
    for name,diffs in parsed:
        before=len(touched)
        touched+=apply_patch_chunks(diffs,source)
        summary.append({'patch':name,'diff_blocks':len(diffs),'file_edit_operations':len(touched)-before,'target_paths':sorted(set(x[0] for x in diffs))})
    paths=sorted(set(touched))
    return {'patches':summary,'changed_files':paths,'patched_file_sha256':{p:hashlib.sha256(source[p]).hexdigest() for p in paths},'upstream_tar_members_checked':count}

def main(argv=None):
    p=argparse.ArgumentParser(description='Host-only pinned Alpine musl sources and memory-only patch verifier.')
    p.add_argument('--source-dir',required=True)
    p.add_argument('--manifest',default=str(pathlib.Path(__file__).with_name(MANIFEST_NAME)))
    p.add_argument('--inputs-only',action='store_true',help='Verify all pinned inputs but do not apply the patches in memory')
    a=p.parse_args(argv)
    report={'milestone':'R3877.26','result':'HOLD','hold_category':'INPUT_NOT_VERIFIED','immutable_hold':'NOT_BOOTABLE','kindle_ssh_sessions':0,'physical_device_access_performed':False,'new_kindle_binary_installed_or_executed':False,'firmware_write_performed':False,'boot_performed':False,'original_r13_stage_accessed':False,'recovery_verified':False,'target_musl_runtime_verified':False,'vendor_kernel_dispatch_verified':False,'binary_provenance_to_patched_source_verified':False,'patched_source_to_binary_reproducibility_verified':False,'verified_input_file_count':0,'in_memory_patch_application_verified':False}
    rc=2
    try:
        manifest=load_manifest(pathlib.Path(a.manifest))
        raw,apki=check_inputs(pathlib.Path(a.source_dir),manifest)
        report['verified_input_file_count']=len(raw)+1
        report['source_version']=manifest['expected_apkbuild_version']
        report['source_git_snapshot']=manifest['aports_commit']
        report['source_validation']=apki
        report['patches_pinned_and_sha512_verified']=True
        if a.inputs_only:
            report.update(result='PASS_PINNED_APORTS_INPUT_BYTES_ONLY',hold_category='NOT_BOOTABLE')
        else:
            patch_inputs=[(e['name'],raw[e['name']]) for e in manifest['entries'] if e['role']=='patch']
            patched=inspect_source(raw[manifest['source_tarball']],patch_inputs)
            report['in_memory_patch_application_verified']=True
            report['patch_audit']=patched
            report.update(result='PASS_PINNED_APORTS_SOURCE_PATCH_MEMORY_APPLY_ONLY',hold_category='NOT_BOOTABLE')
        rc=0
    except (AuditHold,ValueError,UnicodeError,KeyError,OSError,TypeError,MemoryError) as e:
        report['hold_category']=(str(e) if isinstance(e,AuditHold) else 'HOST_INPUT_OR_ANALYSIS_ERROR')[:140]
    print(json.dumps(report,indent=2,sort_keys=True))
    return rc

if __name__=='__main__':
    sys.exit(main())
