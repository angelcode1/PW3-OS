#!/usr/bin/env python3
"""R40.1: offline, non-mutating local stage <-> R40 QEMU path observation crosswalk.

No deletion sets, no authorization for boot, no automatic rootfs construction.
Full path-level output stays in the private local file; summary has no paths.
"""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

MAX_EVENTS = 250000
MAX_PRIVATE_BYTES = 64 * 1024 * 1024
GUEST_STAGE = '/stage/rootfs'
EXPECTED_R40_SUMMARY_SHA256 = 'b8fdcf502fa791816430c528feae57237872932631a369b674f272352c3739e2'
EXPECTED_R40_REVIEW_SHA256 = 'd23d2bf43d6995c9fee73dd096e081dfc934d3d82269b4ab36b556d394b9302f'
OPEN_LIKE = frozenset(('open', 'openat', 'openat2', 'creat', 'execve', 'execveat'))
SAFE = {
    'immutable_hold':'NOT_BOOTABLE',
    'boot_authorized':False,
    'device_access_authorized':False,
    'firmware_write_authorized':False,
    'hardware_write_authorized':False,
    'file_removal_authorized':False,
    'safe_to_prune_inferred':False,
    'complete_dependency_closure_proven':False,
}


def read_obj(path, max_bytes=MAX_PRIVATE_BYTES):
    path = Path(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > max_bytes:
        raise ValueError('input not a regular bounded file')
    obj = json.loads(path.read_text('utf-8'))
    if not isinstance(obj, dict):
        raise ValueError('JSON object required')
    return obj


def canonical_path(path):
    return Path(path).resolve(strict=False)


def under(path, root):
    path,root = canonical_path(path),canonical_path(root)
    return path == root or root in path.parents


def assert_disjoint(stage, evidence, private_out, public_out):
    stage=Path(stage)
    evidence=Path(evidence)
    if not stage.is_dir() or stage.is_symlink():
        raise ValueError('stage root must be a real directory')
    if not evidence.is_dir() or evidence.is_symlink():
        raise ValueError('R40 evidence root must be a real directory')
    if under(evidence,stage) or under(stage,evidence):
        raise ValueError('R40 evidence and stage must be disjoint')
    outputs=[Path(private_out),Path(public_out)]
    if canonical_path(outputs[0])==canonical_path(outputs[1]):
        raise ValueError('colliding outputs')
    for dest in outputs:
        if dest.exists() or dest.is_symlink():
            raise ValueError('refuse to overwrite existing output')
        if not dest.parent.is_dir() or dest.parent.is_symlink():
            raise ValueError('output parent must be real and already exist')
        for src in (stage, evidence):
            if under(dest,src) or under(src,dest):
                raise ValueError('output may not overlap source/evidence')
    return True


def map_guest_path(quoted):
    """Return only unambiguous absolute paths inside /stage/rootfs.

    QEMU sometimes logs relative names or escaped C-string syntax. Without a
    trustworthy cwd/fd trace, do NOT fabricate stage matches for them.
    """
    if not isinstance(quoted,str) or not quoted or '\\' in quoted or '\x00' in quoted:
        return None,'escaped_or_invalid'
    if not quoted.startswith('/'):
        return None,'relative_unresolved'
    if quoted == GUEST_STAGE:
        return '', 'staged_root'
    if not quoted.startswith(GUEST_STAGE + '/'):
        if quoted.startswith('/tmp/r25-ko-home/'):
            return None,'synthetic_home'
        if quoted.startswith(('/proc/', '/sys/', '/dev/')):
            return None,'virtual_guest'
        return None,'external_guest_path'
    rel=quoted[len(GUEST_STAGE)+1:]
    parts=rel.split('/')
    if any(x in ('','.','..') for x in parts):
        return None,'ambiguous_or_traversal'
    return rel,'stage_relative'


def scan_stage(stage_root, max_entries=50000):
    """lstat metadata only; do not follow symlinks or read contents."""
    stage_root=Path(stage_root)
    out={}
    counter=collections.Counter()
    for base,dirs,files in os.walk(stage_root, topdown=True, followlinks=False):
        # deterministic; symlinked directories are represented, never traversed
        dirs.sort();files.sort()
        for name in list(dirs) + list(files):
            p=Path(base)/name
            rel=p.relative_to(stage_root).as_posix()
            st=p.lstat()
            if st.st_dev != stage_root.lstat().st_dev:
                raise ValueError('stage crosses a filesystem boundary')
            if stat.S_ISLNK(st.st_mode):
                kind='SYMLINK_HOLD'
                if name in dirs:dirs.remove(name)
            elif stat.S_ISDIR(st.st_mode):kind='DIRECTORY_HOLD'
            elif stat.S_ISREG(st.st_mode):kind='REGULAR_HOLD'
            else:kind='SPECIAL_HOLD'
            out[rel]=kind
            counter[kind]+=1
            if len(out)>max_entries:
                raise ValueError('stage entry safety cap exceeded')
    return out,counter


def analyze(stage,private,summary,review):
    for field,expected in (
            ('raw_trace_kept_private',True),('reported_pathnames',False),
            ('unobserved_files_safely_removable',False),
            ('trace_guest_stderr_runtime_error_signals',0),
            ('trace_guest_stderr_lifecycle_markers',0),
            ('trace_stdout_qemu_line_count',0)):
        if summary.get(field)!=expected:
            raise ValueError('original R40 trace boundary not proven')
    if review.get('incomplete_syscall_decoder') is not True or review.get('partial_scenario_coverage_only') is not True or review.get('private_runtime_events_not_shared') is not True:
        raise ValueError('R40 review safety scope missing')
    if review.get('verdict') != 'R40_OFFLINE_QEMU_FILE_OBSERVATION_PASS' or review.get('traced_guest_original_and_separate_reviewer_pass') is not True:
        raise ValueError('previous independent R40 review not PASS')
    if summary.get('verdict')!='R40_QEMU_SYSCALLS_OBSERVED_NOT_CLOSED' or summary.get('trace_capture_mode')!='separate_guest_stdout_and_qemu_stderr':
        raise ValueError('R40 split trace summary not confirmed')
    for obj in (summary,review):
        for k,v in SAFE.items():
            if k in obj and obj[k]!=v:
                raise ValueError('unsafe R40 evidence flag')
    if review.get('observed_path_syscalls') != summary.get('observed_path_syscall_count'):
        raise ValueError('public R40 summary/review mismatch')
    if private.get('private') is not True or not isinstance(private.get('events'),list):
        raise ValueError('R40 private events unavailable')
    events=private['events']
    if len(events) != summary.get('observed_path_syscall_count') or len(events)>MAX_EVENTS:
        raise ValueError('R40 private/public event count mismatch')
    stages,stage_counts=scan_stage(stage)
    by_syscall=collections.Counter()
    by_cat=collections.Counter()
    by_result=collections.Counter()
    matched=collections.defaultdict(lambda: {'open_success':0,'metadata_success':0,'failed':0})
    event_status=collections.Counter()
    private_events=[]
    for e in events:
        if not isinstance(e,dict) or not all(k in e for k in ('syscall','path_raw_escaped','status','category','return_value','pid')):
            raise ValueError('R40 malformed private event')
        name=e['syscall'];res=e['status'];category=e['category']
        if not all(isinstance(x,str) and x for x in (name,res,category)) or res not in ('success','failure'):
            raise ValueError('invalid event field')
        if (res=='success') != (e['return_value']>=0 and e.get('errno') is None):
            raise ValueError('inconsistent R40 return/errno')
        if not isinstance(e['pid'],int) or e['pid']<0:
            raise ValueError('invalid pid')
        by_syscall[name]+=1;by_cat[category+'::'+res]+=1;by_result[res]+=1
        rel,kind=map_guest_path(e['path_raw_escaped'])
        status=kind
        if rel is not None:
            if rel in stages:
                kind=stages[rel]
                status='matched_'+kind
                info=matched[rel]
                if res=='failure':info['failed']+=1
                elif name in OPEN_LIKE:info['open_success']+=1
                else:info['metadata_success']+=1
            else:
                status='stage_path_not_found'
        event_status[status+'::'+res]+=1
        private_events.append({'path':e['path_raw_escaped'],'stage_relative_path':rel,'syscall':name,'status':res,'stage_classification':status})
    if dict(sorted(by_syscall.items())) != summary.get('path_syscalls_by_name') or dict(sorted(by_cat.items())) != summary.get('path_syscalls_by_category_and_result') or dict(sorted(by_result.items())) != summary.get('path_syscalls_by_result'):
        raise ValueError('R40 private events disagree with all summary counters')
    # Do not equate successful stat/access with loaded file. Never infer deletion.
    file_states=collections.Counter()
    private_stage=[]
    for path,kind in sorted(stages.items()):
        counts=matched.get(path,{})
        if kind=='REGULAR_HOLD' and counts.get('open_success',0)>0:
            designation='STAGED_SUCCESSFULLY_OPENED'
        elif kind=='REGULAR_HOLD' and counts.get('metadata_success',0)>0:
            designation='STAGED_METADATA_LOOKUP_ONLY'
        elif kind=='REGULAR_HOLD' and counts.get('failed',0)>0:
            designation='STAGED_FAILED_LOOKUP_ONLY'
        else:
            designation=kind
        file_states[designation]+=1
        private_stage.append({'relative_path':path,'kind':kind,'observed_status':designation,'open_success':counts.get('open_success',0),'metadata_success':counts.get('metadata_success',0),'failed_lookup':counts.get('failed',0),'removal_authorized':False})
    share={
        'verdict':'R40_1_STAGE_RUNTIME_CROSSWALK_OBSERVED_NOT_CLOSED',
        'source_r40_verdict':review['verdict'],
        'source_r40_summary_sha256':EXPECTED_R40_SUMMARY_SHA256,
        'source_r40_review_sha256':EXPECTED_R40_REVIEW_SHA256,
        'stage_inventory_entry_count':len(stages),
        'stage_counts_by_type':dict(sorted(stage_counts.items())),
        'stage_counts_by_observation':dict(sorted(file_states.items())),
        'runtime_event_count':len(events),
        'runtime_event_match_classification':dict(sorted(event_status.items())),
        'stage_guest_mount':GUEST_STAGE,
        'relative_qemu_paths_not_guessed':True,
        'symlinks_not_followed':True,
        'private_path_level_report_kept_local':True,
        'R26_static_inventory_reconciled':False,
        'all_unobserved_stage_entries_retained':True,
        'guest_syscall_decoder_incomplete':True,
        'coverage':'one offline same-session double-PDF scenario only',
        **SAFE,
    }
    priv={'private':True,'stage':str(stage),'source_r40_verdict':review['verdict'],'stage_records':private_stage,'observed_events':private_events, 'safe_to_prune_inferred':False, 'immutable_hold':'NOT_BOOTABLE'}
    return priv,share


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',required=True,type=Path,help='R13 stage rootfs directory (NOT stage outer directory)')
    p.add_argument('--r40',required=True,type=Path,help='R40.0.2 local output root')
    p.add_argument('--private-out',required=True,type=Path)
    p.add_argument('--summary-out',required=True,type=Path)
    a=p.parse_args(argv)
    assert_disjoint(a.stage,a.r40,a.private_out,a.summary_out)
    for path,expected in ((a.r40/'R40-SUMMARY.json',EXPECTED_R40_SUMMARY_SHA256),(a.r40/'R40-REVIEW.json',EXPECTED_R40_REVIEW_SHA256)):
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('R40.0.2 public input SHA-256 mismatched verified evidence')
    private=read_obj(a.r40/'trace/R40-PRIVATE-EVENTS.json')
    summary=read_obj(a.r40/'R40-SUMMARY.json')
    review=read_obj(a.r40/'R40-REVIEW.json')
    details,public=analyze(a.stage,private,summary,review)
    # No overwrites, no path leaks to stdout. Private report only in user-chosen local destination.
    targets=[(a.private_out,details),(a.summary_out,public)]
    for target,_ in targets:
        if target.exists() or target.is_symlink():raise FileExistsError('output collision')
    for target,obj in targets:
        with target.open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')
    print('R40_1_STAGE_RUNTIME_CROSSWALK_OBSERVED_NOT_CLOSED; PRIVATE_PATHS_NOT_EXPORTED; NOT_BOOTABLE')
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError) as e:
        # avoid echoing private user paths from exceptions
        print('R40_1_REFUSED; input, source, or output safety contract failed; NOT_BOOTABLE',file=sys.stderr)
        sys.exit(1)
