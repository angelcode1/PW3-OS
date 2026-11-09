#!/usr/bin/env python3
"""R3877.81: offline glibc LuaJIT ELF provider/ABI closure preflight.

Pure Python, read-only and no executable launch, shell/network/Kindle calls,
mounts, or local stage modifications. Always exits 2 / NOT_BOOTABLE.
"""
import argparse
from collections import deque
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys

APP_REL = 'opt/koreader-compat/app/luajit'
LOADER_NAME = 'ld-linux.so.3'
ELF_LIMIT = 32 * 1024 * 1024
STAGE_LIMIT = 50000
OBJECT_LIMIT = 48
KNOWN_INTERPRETERS = ('/lib/ld-linux.so.3', '/lib/ld-linux-armhf.so.3')
VALID_NAME = re.compile(r'^[A-Za-z0-9_.+\-]{1,128}$')


class Refused(Exception):
    def __init__(self, code):
        super().__init__(code)


def raw_file(path):
    if path.is_symlink():
        raise Refused('SYMLINK_PROVIDER_UNVERIFIED')
    fd = os.open(str(path), os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size < 52 or before.st_size > ELF_LIMIT:
            raise Refused('ELF_PROVIDER_SIZE_OR_TYPE_INVALID')
        chunks = []
        remaining = before.st_size
        while remaining:
            b = os.read(fd, min(1024*1024, remaining))
            if not b:
                raise Refused('ELF_PROVIDER_SHORT_READ')
            chunks.append(b)
            remaining -= len(b)
        after = os.fstat(fd)
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns) != (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
            raise Refused('ELF_PROVIDER_CHANGED_DURING_READ')
        return b''.join(chunks)
    finally:
        os.close(fd)


def span(b, offset, n):
    if offset < 0 or n < 0 or offset > len(b) or n > len(b) - offset:
        raise Refused('ELF_BOUNDS_INVALID')
    return b[offset:offset+n]


def cstring(b, offset):
    if offset < 0 or offset >= len(b):
        raise Refused('ELF_STRING_OFFSET_INVALID')
    end = b.find(b'\0', offset)
    if end < 0:
        raise Refused('ELF_STRING_UNTERMINATED')
    try:
        return b[offset:end].decode('ascii')
    except UnicodeDecodeError:
        raise Refused('ELF_STRING_NONASCII') from None


def parse_elf(data):
    if len(data) < 52 or data[:7] != b'\x7fELF\x01\x01\x01':
        raise Refused('ELF32_ARM_LITTLE_ENDIAN_REQUIRED')
    etype, machine, version, entry, phoff, _shoff, flags, ehsize, entsize, nph, *_ = struct.unpack_from('<HHIIIIIHHHHHH',data,16)
    if machine != 40 or version != 1 or etype not in (2,3) or (flags >> 24) != 5 or ehsize != 52 or entsize != 32 or not 1 <= nph <= 128:
        raise Refused('ELF_ARM_EABI5_INVALID')
    if flags & 0x600 == 0x600:
        raise Refused('ELF_CONFLICTING_FLOAT_FLAGS')
    span(data,phoff,nph*entsize)
    segs = []
    for n in range(nph):
        p=struct.unpack_from('<8I',data,phoff+n*32)
        if p[0] in (1,2,3):
            span(data,p[1],p[4])
        segs.append(p)
    interps=[p for p in segs if p[0]==3]
    ds=[p for p in segs if p[0]==2]
    if len(interps)>1 or len(ds)>1:
        raise Refused('ELF_MULTIPLE_SPECIAL_SEGMENTS')
    interp=None
    if interps:
        p=interps[0]
        raw=span(data,p[1],p[4])
        if len(raw)<2 or len(raw)>128 or not raw.endswith(b'\x00'):
            raise Refused('ELF_INTERP_INVALID')
        interp=cstring(raw,0)
    tags=[]
    if ds:
        p=ds[0]
        if p[4]>131072 or p[4]%8:
            raise Refused('ELF_DYNAMIC_BOUNDS_INVALID')
        ended=False
        for off in range(p[1],p[1]+p[4],8):
            tag,value=struct.unpack_from('<II',data,off)
            if tag==0:
                ended=True
                break
            tags.append((tag,value))
        if not ended:
            raise Refused('ELF_DYNAMIC_UNTERMINATED')
    strings={}
    if any(t in (1,14,15,29) for t,_ in tags):
        vals={}
        for t,v in tags:
            if t in (5,10):
                if t in vals and vals[t]!=v:
                    raise Refused('ELF_DYNAMIC_STRING_CONFLICT')
                vals[t]=v
        if 5 not in vals or 10 not in vals or vals[10]>1048576:
            raise Refused('ELF_STRING_TABLE_INVALID')
        va,n=vals[5],vals[10]
        mapped=[]
        for p in segs:
            if p[0]==1 and p[2]<=va and va-p[2]<=p[4] and n<=p[4]-(va-p[2]):
                mapped.append(span(data,p[1]+va-p[2],n))
        if len(mapped)!=1:
            raise Refused('ELF_STRING_TABLE_UNMAPPED')
        for tag, value in tags:
            if tag in (1,14,15,29):
                strings.setdefault(tag,[]).append(cstring(mapped[0],value))
    deps=strings.get(1,[])
    if len(deps)>64 or any(not VALID_NAME.fullmatch(x) for x in deps):
        raise Refused('ELF_NEEDED_NAME_INVALID')
    return {
        'elf_type':'EXEC' if etype==2 else 'DYN',
        'eabi5':True,
        'float_flag':'soft' if flags&0x200 else 'hard' if flags&0x400 else 'unspecified',
        'interpreter':interp,
        'needed':deps,
        'rpath_values':strings.get(15,[]),
        'runpath_values':strings.get(29,[]),
        'has_dynamic':bool(ds),
        'has_entrypoint':entry!=0,
    }


def classify_path(value):
    tokens=value.split(':')
    if any(not t for t in tokens):
        return 'EMPTY_PATH_ELEMENT_HOLD'
    if all(t.startswith('$ORIGIN/') or t.startswith('${ORIGIN}/') for t in tokens):
        if all(all(p not in ('', '.') for p in re.split(r'/',re.sub(r'^\$\{?ORIGIN\}?/', '',t).lstrip('/')))
               for t in tokens):
            return 'ORIGIN_RELATIVE_REVIEW_NEEDED'
    if any(t.startswith('/') for t in tokens):
        return 'ABSOLUTE_DEVICE_PATH_NOT_RELOCATABLE'
    if any('$' in t for t in tokens):
        return 'VARIABLE_EXPANSION_REVIEW_NEEDED'
    return 'RELATIVE_OR_OTHER_REVIEW_NEEDED'


def collect_index(root):
    regular={}
    links={}
    num_regular=num_links=0
    for base,dirs,files in os.walk(root,topdown=True,followlinks=False):
        keep=[]
        for name in dirs:
            p=Path(base)/name
            if p.is_symlink():
                num_links+=1
                links.setdefault(name,[]).append(p)
            else:
                keep.append(name)
        dirs[:]=keep
        for name in files:
            p=Path(base)/name
            if p.is_symlink():
                num_links+=1
                links.setdefault(name,[]).append(p)
                continue
            mode=p.lstat().st_mode
            if stat.S_ISREG(mode):
                num_regular+=1
                regular.setdefault(name,[]).append(p)
        if num_regular+num_links>STAGE_LIMIT:
            raise Refused('STAGE_ENTRY_LIMIT_EXCEEDED')
    return regular, links, num_regular, num_links


def audit(root):
    root=Path(root).expanduser()
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise Refused('STAGE_ROOT_INVALID')
    target=root/APP_REL
    cur=root
    for component in APP_REL.split('/')[:-1]:
        cur=cur/component
        if not cur.is_dir() or cur.is_symlink():
            raise Refused('ENTRYPOINT_PARENT_UNTRUSTED')
    if target.is_symlink() or not target.is_file():
        raise Refused('ENTRYPOINT_MISSING_OR_SYMLINK')
    regular,links,nfiles,nlinks=collect_index(root)
    app=parse_elf(raw_file(target))
    if not app['has_entrypoint'] or app['elf_type']!='EXEC' or app['interpreter']!='/lib/ld-linux.so.3' or not app['needed']:
        raise Refused('ENTRYPOINT_GLIBC_CONTRACT_CHANGED')
    if app['float_flag']!='soft':
        raise Refused('ENTRYPOINT_SOFT_FLOAT_NOT_MATCHED')
    pending=deque([('ld-linux.so.3','interpreter'), *((n,'needed') for n in app['needed'])])
    visited={}
    problems=[]
    edges=[]
    while pending:
        basename,kind=pending.popleft()
        if basename in visited:
            continue
        if len(visited)>=OBJECT_LIMIT:
            raise Refused('TRANSITIVE_PROVIDER_LIMIT_EXCEEDED')
        options=regular.get(basename,[])
        link_opts=links.get(basename,[])
        if len(options)!=1:
            code='MISSING_REGULAR_PROVIDER' if not options else 'DUPLICATE_REGULAR_PROVIDERS'
            if link_opts and not options:
                code='SYMLINK_ONLY_PROVIDER_NOT_FOLLOWED'
            problems.append({'name':basename,'category':code,'regular_matches':len(options),'symlink_matches':len(link_opts)})
            visited[basename]=None
            continue
        # Stage-local basename uniqueness alone does not prove the dynamic loader
        # searches this directory or that an ELF symbol version resolves.
        blob=raw_file(options[0])
        elf=parse_elf(blob)
        if elf['interpreter'] is not None:
            problems.append({'name':basename,'category':'SHARED_PROVIDER_HAS_INTERPRETER'})
        if elf['float_flag']=='hard':
            problems.append({'name':basename,'category':'HARD_FLOAT_VS_SOFT_ENTRYPOINT'})
        elif elf['float_flag']=='unspecified':
            problems.append({'name':basename,'category':'PROVIDER_FLOAT_ABI_UNSPECIFIED'})
        if elf['elf_type']!='DYN':
            problems.append({'name':basename,'category':'PROVIDER_NOT_ET_DYN'})
        visited[basename]=dict(name=basename,stage_relative_path=options[0].relative_to(root).as_posix(),
                               elf_type=elf['elf_type'],arm_eabi5=True,float_flag=elf['float_flag'],
                               needed=elf['needed'],rpath_categories=[classify_path(s) for s in elf['rpath_values']],
                               runpath_categories=[classify_path(s) for s in elf['runpath_values']])
        for dep in elf['needed']:
            edges.append([basename,dep])
            pending.append((dep,'needed'))
    return {
        'entrypoint':APP_REL,'interpreter':app['interpreter'],
        'entrypoint_float_flag':app['float_flag'],
        'entrypoint_direct_needed':app['needed'],
        'entrypoint_rpath_categories':[classify_path(s) for s in app['rpath_values']],
        'entrypoint_runpath_categories':[classify_path(s) for s in app['runpath_values']],
        'stage_regular_file_count':nfiles,'stage_symlink_count':nlinks,
        'r26_recorded_regular_files':1448,
        'stage_identity_revalidated_against_R26':False,
        'provider_list':[visited[x] if visited[x] is not None else {'name':x,'unresolved':True} for x in sorted(visited)],
        'unresolved_or_ambiguous':problems,
        'transitive_dependency_edges':edges,
        'all_needed_names_unique_regular':all(x is not None for x in visited.values()),
        'dynamic_loader_resolution_verified':False,
        'symbol_version_compatibility_verified':False,
        'arm_build_attributes_verified':False,
        'koreader_device_runtime_verified':False,
    }


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',required=True)
    p.add_argument('--acknowledge-host-only-glibc-dependency-audit',action='store_true')
    a=p.parse_args(argv)
    result={'milestone':'R3877.81','result':'HOLD','immutable_hold':'NOT_BOOTABLE',
            'hold_category':'HOST_ONLY_DEPENDENCY_AUDIT_NOT_AUTHORIZED',
            'device_execution_performed':False,'device_access_performed':False,
            'stage_files_modified':False,'boot_hook_modified':False,
            'recovery_verified':False}
    if a.acknowledge_host_only_glibc_dependency_audit:
        try:
            result['review']=audit(a.stage)
            result['hold_category']='GLIBC_DYNAMIC_LOADER_AND_VERSION_RUNTIME_UNVERIFIED'
        except (Refused,OSError,struct.error,ValueError):
            result['hold_category']='OFFLINE_GLIBC_CLOSURE_REVIEW_REFUSED'
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
    return 2

if __name__=='__main__':
    sys.exit(main())
