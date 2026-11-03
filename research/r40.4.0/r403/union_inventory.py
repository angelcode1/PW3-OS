#!/usr/bin/env python3
"""R40.3: locally reconcile proven R40.1/R40.2 file opens with R26 manifest.

Outputs counts-only evidence; NEVER a prune list. Original private files stay on host.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys

EXPECTED_R402_SUMMARY_SHA256 = 'cdac30dd46676de490d96a71af582135ca63ee0d9bb705ec0f895afcb652dd1b'
EXPECTED_R402_PRIVATE_SHA256 = 'e28a5f0d51b72545d931e4822099bc7db73d14d2fffcb555c941b4b783be3e41'
MAX_RECORDS = 50_000
MAX_JSON_BYTES = 70 * 1024 * 1024
MAX_BYTES_HASHED = 16 * 1024 * 1024 * 1024
HEX64 = re.compile(r'^[0-9a-f]{64}$')
SAFE = dict(boot_authorized=False, device_access_authorized=False,
            firmware_write_authorized=False, hardware_write_authorized=False,
            file_removal_authorized=False, safe_to_prune_inferred=False,
            complete_dependency_closure_proven=False, immutable_hold='NOT_BOOTABLE')


def digest(p):
    h = hashlib.sha256()
    fd = os.open(p, os.O_RDONLY | (getattr(os, 'O_NOFOLLOW', 0)))
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode): raise ValueError('nonregular input')
        with os.fdopen(fd, 'rb', closefd=False) as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk: break
                h.update(chunk)
        after = os.fstat(fd)
        if (before.st_ino,before.st_dev,before.st_size,before.st_mtime_ns) != (after.st_ino,after.st_dev,after.st_size,after.st_mtime_ns):
            raise ValueError('input changed during read')
    finally: os.close(fd)
    return h.hexdigest()


def read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
        raise ValueError('private evidence unavailable, symlinked or too large')
    with path.open(encoding='utf-8') as f: value=json.load(f)
    if not isinstance(value,dict): raise ValueError('object required')
    return value


def relpath(value):
    if not isinstance(value,str) or not value or '\\' in value or '\x00' in value or '\n' in value:
        raise ValueError('unsafe relative path')
    if value.startswith('./'): value=value[2:]
    if value.startswith('/') or any(part in ('','.','..') for part in value.split('/')):
        raise ValueError('absolute or traversal path')
    return value


def disjoint(stage, others, output):
    stage=Path(stage)
    if stage.is_symlink() or not stage.is_dir():raise ValueError('rootfs must be actual directory')
    outer=stage.parent
    if outer.is_symlink() or not outer.is_dir():raise ValueError('outer stage must be actual directory')
    roots=[stage.resolve(),outer.resolve()]
    for other in others:
        o=Path(other)
        if o.is_symlink() or not o.is_file():raise ValueError('input must be regular')
        p=o.resolve()
        if any(p==r or r in p.parents for r in roots):raise ValueError('input inside stage')
    out=Path(output)
    if out.is_symlink() or out.exists() or out.parent.is_symlink() or not out.parent.is_dir():
        raise ValueError('output must be new in existing real directory')
    resolved=out.resolve()
    for root in roots:
        if resolved==root or root in resolved.parents or resolved in root.parents:raise ValueError('output overlaps stage')
    for other in others:
        if resolved==Path(other).resolve():raise ValueError('output collides with input')


def scan_outer(root):
    root=Path(root)
    rootst=os.lstat(root)
    if not stat.S_ISDIR(rootst.st_mode) or stat.S_ISLNK(rootst.st_mode):raise ValueError('outer stage root invalid')
    records={}
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        dirs.sort();files.sort()
        for name in list(dirs) + list(files):
            full=Path(base)/name
            st=os.lstat(full)
            if st.st_dev !=rootst.st_dev: raise ValueError('cross-device stage entry')
            rel=full.relative_to(root).as_posix()
            if stat.S_ISLNK(st.st_mode):
                kind='symlink';dirs[:]=[x for x in dirs if x!=name]
            elif stat.S_ISDIR(st.st_mode):kind='directory'
            elif stat.S_ISREG(st.st_mode):kind='regular'
            else:raise ValueError('special stage entry hold')
            records[rel]={'type':kind,'size':st.st_size,'mode':stat.S_IMODE(st.st_mode),
                           'link_target':os.readlink(full) if kind=='symlink' else None}
            if len(records)>MAX_RECORDS: raise ValueError('large stage inventory hold')
    return records


def observed_union(stage_records, r401_priv, r401_sum, r402_priv, r402_sum):
    if r401_sum.get('verdict')!='R40_1_STAGE_RUNTIME_CROSSWALK_OBSERVED_NOT_CLOSED':raise ValueError('R40.1 not verified')
    if r402_sum.get('verdict')!='R40_2_SOURCE_BOUND_CWD_CROSSWALK_OBSERVED_NOT_CLOSED':raise ValueError('R40.2 not verified')
    if r402_sum.get('cwd_evidence_status')!='SOURCE_BOUND_CWD_NO_RECORDED_MUTATION':raise ValueError('R40.2 CWD unproven')
    for doc in (r401_sum,r402_sum):
        for k,v in SAFE.items():
            if doc.get(k)!=v: raise ValueError('prior safety hold changed')
    if r401_priv.get('private') is not True or r402_priv.get('private') is not True or r402_priv.get('immutable_hold')!='NOT_BOOTABLE':
        raise ValueError('missing private provenance')
    if not (len(r401_priv.get('stage_records',[]))==r401_sum.get('stage_inventory_entry_count')==r402_sum.get('stage_rootfs_entries')):
        raise ValueError('stage record count mismatch')
    root_records={r['relative_path']:r for r in r401_priv['stage_records'] if isinstance(r,dict) and isinstance(r.get('relative_path'),str)}
    if len(root_records)!=r402_sum['stage_rootfs_entries'] or set('rootfs/'+k for k in root_records)!=set(k for k in stage_records if k.startswith('rootfs/')):
        raise ValueError('R40.1 rootfs stage changed')
    if r401_sum.get('stage_counts_by_type')!=r402_sum.get('stage_type_counts'):
        raise ValueError('stage type count mismatch')
    absolute=set()
    for rel,rec in root_records.items():
        st=stage_records['rootfs/'+rel]
        if rec.get('kind') != {'regular':'REGULAR_HOLD','directory':'DIRECTORY_HOLD','symlink':'SYMLINK_HOLD'}[st['type']]:
            raise ValueError('stage type mismatch')
        if rec.get('observed_status')=='STAGED_SUCCESSFULLY_OPENED':
            if st['type']!='regular' or rec.get('open_success',0)<1: raise ValueError('invalid original absolute observation')
            absolute.add('rootfs/'+rel)
        if rec.get('removal_authorized') is not False:raise ValueError('prior removal hold invalid')
    if len(absolute)!=r402_sum.get('r401_directly_observed_absolute_stage_regular_files') or len(absolute)!=r401_sum.get('stage_counts_by_observation',{}).get('STAGED_SUCCESSFULLY_OPENED'):
        raise ValueError('prior absolute count mismatch')
    relative={}
    for rel,count in r402_priv.get('stage_match_open_counts',{}).items():
        path='rootfs/'+relpath(rel)
        if stage_records.get(path,{}).get('type')!='regular' or type(count)!=int or count<1:raise ValueError('invalid relative open')
        relative[path]=count
    if len(relative)!=r402_sum.get('distinct_stage_regular_files_newly_opened_by_proven_relative_path') or sum(relative.values())!=r402_sum.get('relative_successful_open_events_stage_matched'):
        raise ValueError('relative totals mismatch')
    events=r402_priv.get('resolved_relative_events')
    if not isinstance(events,list) or len(events)!=r402_sum.get('relative_events_examined'):
        raise ValueError('R40.2 events missing')
    cls=collections.Counter(e.get('provenance_classification','')+'::'+e.get('status','') for e in events)
    if dict(cls)!=r402_sum.get('relative_event_classifications') or any(e.get('removal_authorized') is not False for e in events):
        raise ValueError('R40.2 provenance mismatch')
    open_events=collections.Counter()
    for e in events:
        if e.get('provenance_classification')=='CWD_PROVEN_REGULAR_STAGE_MATCH' and e.get('status')=='success' and e.get('syscall') in ('open','openat','openat2','creat','execve'):
            path='rootfs/'+relpath(e['stage_relative_path'])
            if path not in relative:raise ValueError('R40.2 private open mismatch')
            open_events[path]+=1
    if dict(open_events)!=relative:raise ValueError('R40.2 per-file open counts differ')
    return absolute,relative


def parse_inventory(r26):
    """Return (records, schema) or (None, unsupported); never infer missing hashes."""
    candidates=[('entries',r26.get('entries')),('inventory',r26.get('inventory')),
                ('files',r26.get('files')),('stage_entries',r26.get('stage_entries'))]
    for key,blob in candidates:
        if isinstance(blob,list):
            if not blob or not all(isinstance(r,dict) for r in blob):continue
            pairs=[]
            for r in blob:
                path=r.get('path',r.get('relative_path'))
                if not isinstance(path,str):break
                pairs.append((path,r))
            else:return dict_checked(pairs),key+'[]'
        if isinstance(blob,dict) and blob:
            if all(isinstance(k,str) and isinstance(v,dict) for k,v in blob.items()):
                return dict_checked(blob.items()),key+'{}'
    return None,'unsupported'


def dict_checked(pairs):
    d={}
    for path,rec in pairs:
        rel=relpath(path)
        if rel in d:raise ValueError('duplicate R26 path')
        d[rel]=rec
        if len(d)>MAX_RECORDS:raise ValueError('R26 manifest too large')
    return d


def kind_from_record(r):
    v=r.get('type',r.get('kind',r.get('file_type')))
    if not isinstance(v,str):return None
    v=v.lower().replace('_','-').replace(' ','-')
    if v in ('file','regular','regular-file','regularfile'):return 'regular'
    if v in ('dir','directory'):return 'directory'
    if v in ('link','symlink','symbolic-link'):return 'symlink'
    return None


def inspect_r26_inventory(outer,stage_records,r26):
    """Full SHA+symlink verification only if all records expose expected fields.

    Return counts and hold reason, never filenames. R26 is user-supplied evidence,
    not a signed trust root even on perfect content agreement.
    """
    records,schema=parse_inventory(r26)
    result={'r26_manifest_schema':schema,'r26_provenance_authenticated':False,
            'r26_static_inventory_hash_reconciled':False,'r26_entry_count':len(records) if records else None,
            'r26_manifest_status':'SCHEMA_UNSUPPORTED_HOLD','r26_regular_files_sha256_verified':0,
            'r26_symlink_targets_verified':0,'r26_directories_type_verified':0}
    if records is None:return result
    if set(records)!=set(stage_records):
        result['r26_manifest_status']='PATH_SET_DIFFERENT_HOLD'
        result['r26_path_set_mismatch_count']=len(set(records)^set(stage_records))
        return result
    info={}
    for path,record in records.items():
        kind=kind_from_record(record)
        if kind != stage_records[path]['type']:
            result['r26_manifest_status']='TYPE_MISSING_OR_DIFFERENT_HOLD'
            return result
        if kind=='regular':
            sha=record.get('sha256',record.get('sha256_digest',record.get('sha')))
            if not isinstance(sha,str) or not HEX64.fullmatch(sha.lower()):
                result['r26_manifest_status']='FILE_HASH_MISSING_HOLD';return result
            info[path]=sha.lower()
        elif kind=='symlink':
            target=record.get('symlink_target',record.get('link_target',record.get('target')))
            if not isinstance(target,str):
                result['r26_manifest_status']='SYMLINK_TARGET_MISSING_HOLD';return result
            if target!=stage_records[path]['link_target']:
                result['r26_manifest_status']='SYMLINK_TARGET_DIFFERENT_HOLD';return result
            result['r26_symlink_targets_verified']+=1
        else:result['r26_directories_type_verified']+=1
    # Hash only regular files, bounded and O_NOFOLLOW; no executing files.
    bytes_total=sum(stage_records[p]['size'] for p in info)
    if bytes_total>MAX_BYTES_HASHED:
        result['r26_manifest_status']='HASH_INPUT_VOLUME_LIMIT_HOLD';return result
    for path,expected in sorted(info.items()):
        full=Path(outer)/path
        if digest(full)!=expected:
            result['r26_manifest_status']='FILE_SHA_DIFFERENT_HOLD';return result
        result['r26_regular_files_sha256_verified']+=1
    result['r26_manifest_status']='ALL_RECORDED_ENTRIES_MATCH_UNAUTHENTICATED'
    result['r26_static_inventory_hash_reconciled']=True
    return result


def summarize(root, r401_priv, r401_sum, r402_priv, r402_sum, r26=None):
    stage_records=scan_outer(root)
    stage_count=len(stage_records)
    if stage_count!=2070:raise ValueError('unexpected enclosing stage entry count')
    absfiles,relfiles=observed_union(stage_records,r401_priv,r401_sum,r402_priv,r402_sum)
    union=absfiles|set(relfiles)
    regular_count=sum(x['type']=='regular' for x in stage_records.values())
    summary={
        'verdict':'R40_3_DEDUPLICATED_RUNTIME_STAGE_UNION_OBSERVED_NOT_CLOSED',
        'r40_1_original_absolute_distinct_stage_regular_opened':len(absfiles),
        'r40_2_source_bound_relative_distinct_stage_regular_opened':len(relfiles),
        'duplicate_files_seen_in_absolute_and_relative_paths':len(absfiles & set(relfiles)),
        'deduplicated_stage_regular_files_observed_open':len(union),
        'stage_regular_files_not_observed_open_retained':regular_count-len(union),
        'stage_outer_entries':stage_count,
        'stage_regular_file_count':regular_count,
        'prior_r40_2_verdict':r402_sum['verdict'],
        'original_r39_4_11_arm_verdict_preserved':'R39_4_11_THREE_SOURCE_BOUND_READS_ARM_PASS',
        'partial_scenario_only':True,
        'decoder_incomplete':True,
        'private_source_paths_exported':False,
        'all_unobserved_staged_files_retained':True,
        'r26_inventory_supplied':r26 is not None,
        **SAFE
    }
    if r26 is None:
        summary.update({'r26_manifest_status':'NOT_SUPPLIED_HOLD','r26_static_inventory_hash_reconciled':False,'r26_provenance_authenticated':False})
    else:summary.update(inspect_r26_inventory(root,stage_records,r26))
    return summary


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('stage','r401-private','r401-summary','r402-private','r402-summary','summary-out'):
        ap.add_argument('--'+key,required=True,type=Path)
    ap.add_argument('--r26-inventory',type=Path,default=None)
    a=ap.parse_args(argv)
    stage=a.stage;root=stage.parent
    if stage.name!='rootfs' or stage.is_symlink() or not stage.is_dir():raise ValueError('exact rootfs required')
    other=[a.r401_private,a.r401_summary,a.r402_private,a.r402_summary]
    if a.r26_inventory:other.append(a.r26_inventory)
    disjoint(stage,other,a.summary_out)
    if digest(a.r402_summary)!=EXPECTED_R402_SUMMARY_SHA256 or digest(a.r402_private)!=EXPECTED_R402_PRIVATE_SHA256:
        raise ValueError('R40.2 private and public evidence pin mismatch')
    s401=read_json(a.r401_summary);p401=read_json(a.r401_private)
    s402=read_json(a.r402_summary);p402=read_json(a.r402_private)
    if not isinstance(p401.get('stage'),str) or Path(p401['stage']).resolve()!=stage.resolve():
        raise ValueError('R40.1 crosswalk uses different stage')
    r26=read_json(a.r26_inventory) if a.r26_inventory else None
    summary=summarize(root,p401,s401,p402,s402,r26)
    # Only aggregated, filenames-free public output; no private report produced.
    flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,'O_NOFOLLOW',0)
    fd=os.open(a.summary_out,flags,0o644)
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        json.dump(summary,f,sort_keys=True,indent=2);f.write('\n')
    print(summary['verdict']+'; PRIVATE_PATHS_NOT_EXPORTED; NOT_BOOTABLE')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,TypeError,KeyError,IndexError,json.JSONDecodeError):
        print('R40_3_REFUSED; source, stage or evidence contract invalid; NOT_BOOTABLE',file=sys.stderr)
        sys.exit(1)
