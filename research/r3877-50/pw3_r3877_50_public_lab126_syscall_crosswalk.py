#!/usr/bin/env python3
"""R3877.50: offline crosswalk of user-reported QEMU names to pinned public Lab126 mirror source.

Never runs Docker/QEMU or contacts a Kindle. The presence of a source table entry
is not proof of the actual Kindle kernel binary's dispatch or ABI semantics.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

MILESTONE = 'R3877.50'
HOLD = 'NOT_BOOTABLE'
MIRROR_REPO = 'katadelos/linux-3.0.35-lab126'
MIRROR_COMMIT = '7ac2585f384573da8cbdcc987a3503e2e6ff1fb4'
HEADER_BLOB = '2c04ed5efeb50707ac3353958434d37691841839'
CALLS_BLOB = '80f7896cc0164ad6f74469f1e777b90c1f306443'
UPSTREAM_V3_HEADER_BLOB = '2c04ed5efeb50707ac3353958434d37691841839'
PARENT_IMAGE_ID = 'sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a'
BUSYBOX_HASH = 'df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c'
QEMU_HASH = '3347b95a4006c1eb19b93ba09469a2c42b04fe5d89a430ce96cbf2a2367cf5c1'
BASELINE = {
    'busybox_true_trace': (17, ('brk','exit_group','getgid32','getuid32','mmap2','mprotect','rt_sigprocmask','set_tid_address','setgid32','setuid32')),
    'busybox_uname_trace': (20, ('brk','exit_group','getgid32','getuid32','ioctl','mmap2','mprotect','rt_sigprocmask','set_tid_address','setgid32','setuid32','uname','writev')),
    'busybox_echo_trace': (18, ('brk','exit_group','getgid32','getuid32','mmap2','mprotect','rt_sigprocmask','set_tid_address','setgid32','setuid32','write')),
}
ENTRY_EXPECTED = {
    'brk':'sys_brk','exit_group':'sys_exit_group','getgid32':'sys_getgid',
    'getuid32':'sys_getuid','ioctl':'sys_ioctl','mmap2':'sys_mmap2',
    'mprotect':'sys_mprotect','rt_sigprocmask':'sys_rt_sigprocmask',
    'set_tid_address':'sys_set_tid_address','setgid32':'sys_setgid',
    'setuid32':'sys_setuid','uname':'sys_newuname','write':'sys_write','writev':'sys_writev'
}
SYSCALL_DEFINE = re.compile(r'^\s*#\s*define\s+__NR_([a-z][a-z0-9_]*)\s+\(\s*__NR_SYSCALL_BASE\s*\+\s*(\d+)\s*\)', re.M)
GROUP = re.compile(r'/\*\s*(\d+)\s*\*/')
CALL = re.compile(r'\bCALL\(([^\n]+?)\)')

class AuditHold(Exception):
    pass

def sha_git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()

def safe_read(name, cap):
    p = Path(name)
    if p.is_symlink() or not p.is_file():
        raise AuditHold('MISSING_OR_SYMLINK_INPUT')
    n = p.stat().st_size
    if n <= 0 or n > cap:
        raise AuditHold('INPUT_SIZE_OUT_OF_BOUNDS')
    return p.read_bytes()

def parse_header(raw):
    s=raw.decode('utf-8','strict')
    if 'arch/arm/include/asm/unistd.h' not in s or '#define __NR_SYSCALL_BASE' not in s:
        raise AuditHold('UNISTD_HEADER_MARKER_INVALID')
    no_comments=re.sub(r'/\*.*?\*/','',s,flags=re.S)
    no_comments=re.sub(r'//[^\n]*','',no_comments)
    entries={}
    for m in SYSCALL_DEFINE.finditer(no_comments):
        name,num=m[1],int(m[2])
        if name in entries and entries[name]!=num:
            raise AuditHold('UNISTD_DUPLICATE_CONFLICT')
        entries[name]=num
    if len(entries)<300 or any(entries.get(n)!=v for n,v in {'brk':45,'mmap2':192,'exit_group':248,'rt_sigprocmask':175,'write':4}.items()):
        raise AuditHold('UNISTD_DEFINITIONS_OR_SENTINELS_INVALID')
    return entries

def parse_calls(raw):
    s=raw.decode('utf-8','strict')
    if 'arch/arm/kernel/calls.S' not in s or 'included thrice' not in s:
        raise AuditHold('CALLS_SOURCE_MARKER_INVALID')
    markers=list(GROUP.finditer(s))
    if len(markers)!=76 or [int(m[1]) for m in markers] != list(range(0,376,5)):
        raise AuditHold('CALLS_GROUP_MARKER_SEQUENCE_INVALID')
    entries={}
    for i,m in enumerate(markers):
        base=int(m[1]);stop=markers[i+1].start() if i+1<len(markers) else len(s)
        chunk=s[m.end():stop]
        if base==375:
            chunk=chunk.split('#ifndef syscalls_counted',1)[0]
        names=CALL.findall(chunk)
        if len(names)!=(1 if base==375 else 5):
            raise AuditHold('CALLS_GROUP_CARDINALITY_INVALID')
        for off,entry in enumerate(names):
            if '\t' in entry or len(entry)>90:
                raise AuditHold('CALLS_ENTRY_SYNTAX_INVALID')
            entries[base+off]=entry
    if len(entries)!=376:
        raise AuditHold('CALLS_TABLE_LENGTH_INVALID')
    return entries

def baseline_check(evidence):
    if not isinstance(evidence,dict) or evidence.get('milestone')!='R3877.49.3' or evidence.get('result')!='PASS_QEMU_SYSCALL_NAMES_AND_UNTRACED_APPLET_CONTROLS_ONLY':
        raise AuditHold('R49_3_BASELINE_NOT_A_PASS')
    if evidence.get('immutable_hold')!=HOLD or evidence.get('independent_untraced_controls_verified') is not True:
        raise AuditHold('R49_3_HOLD_OR_CONTROLS_INVALID')
    if (evidence.get('original_image_id_sha256')!=PARENT_IMAGE_ID or evidence.get('busybox_sha256')!=BUSYBOX_HASH or evidence.get('qemu_binary_sha256')!=QEMU_HASH):
        raise AuditHold('R49_3_RUNTIME_PINS_MISMATCH')
    for flag in ('all_created_containers_removed','original_image_unchanged','authorized_qemu_execution_performed'):
        if evidence.get(flag) is not True:
            raise AuditHold('R49_3_EXECUTION_OR_CLEANUP_INVALID')
    for flag in ('boot_performed','firmware_write_performed','physical_device_access_performed','host_mounts_or_guest_network_enabled','vendor_linux_3_0_35_syscalls_verified'):
        if evidence.get(flag) is not False:
            raise AuditHold('R49_3_SAFETY_OR_SCOPE_INVALID')
    p=evidence.get('runtime_probes')
    if not isinstance(p,dict):
        raise AuditHold('R49_3_PROBES_MISSING')
    required_control=('busybox_true_control','busybox_uname_control','busybox_echo_control')
    for k in required_control:
        a=p.get(k,{})
        if a.get('status')!='PASS' or a.get('exit_code')!=0 or a.get('expected_applet_output_matches') is not True:
            raise AuditHold('R49_3_UNTRACED_CONTROL_FAILED')
    observed={}
    for k,(count,names) in BASELINE.items():
        a=p.get(k,{})
        t=a.get('trace',{})
        if a.get('exit_code')!=0 or a.get('untraced_control_verified') is not True or a.get('guest_argv_verified_by_inspect') is not True:
            raise AuditHold('R49_3_TRACED_CONTROL_FAILED')
        if t.get('syscall_record_count')!=count or t.get('trace_enosys_record_count')!=0 or t.get('trace_unknown_record_count')!=0:
            raise AuditHold('R49_3_TRACE_COUNTS_CHANGED')
        ns=t.get('syscall_names')
        if not isinstance(ns,list) or ns!=sorted(names) or len(ns)!=len(set(ns)):
            raise AuditHold('R49_3_TRACE_NAME_SET_CHANGED')
        observed[k]=ns
    return observed

def audit(report,header,calls,*,expected_header=HEADER_BLOB,expected_calls=CALLS_BLOB):
    observed=baseline_check(report)
    if sha_git_blob(header)!=expected_header or sha_git_blob(calls)!=expected_calls:
        raise AuditHold('PUBLIC_SOURCE_GIT_BLOB_PIN_MISMATCH')
    nums=parse_header(header)
    entries=parse_calls(calls)
    union=sorted(set(x for values in observed.values() for x in values))
    if union!=sorted(ENTRY_EXPECTED):
        raise AuditHold('TRACE_UNION_UNEXPECTED')
    crosswalk=[]
    for name in union:
        n=nums.get(name)
        if n is None or entries.get(n)!=ENTRY_EXPECTED[name]:
            raise AuditHold('PUBLIC_SOURCE_HEADER_TO_CALLS_MISMATCH:'+name)
        crosswalk.append({'guest_qemu_syscall':name,'source_arm_eabi_number':n,'public_calls_s_entry':entries[n],
                          'source_entry_found':True,'physical_vendor_kernel_dispatch_verified':False})
    return {
        'milestone':MILESTONE,
        'result':'PASS_PINNED_PUBLIC_LAB126_SOURCE_SYSCALL_CROSSWALK_ONLY',
        'immutable_hold':HOLD,
        'source_repo':MIRROR_REPO,'source_revision':MIRROR_COMMIT,
        'source_provenance':'GitHub public mirror Git-blob-pinned source; not authenticated against running Kindle binary',
        'public_header_git_blob_sha1':sha_git_blob(header),'public_calls_git_blob_sha1':sha_git_blob(calls),
        'public_header_identical_to_upstream_linux_v3_header':sha_git_blob(header)==UPSTREAM_V3_HEADER_BLOB,
        'observed_guest_qemu_trace_record_count':sum(x[0] for x in BASELINE.values()),
        'distinct_observed_qemu_syscall_names':len(union),
        'source_crosswalk':crosswalk,
        'observed_trace_enosys_count':0,
        'source_presence_not_actual_runtime_compatibility':True,
        'public_source_not_authenticated_running_vendor_kernel':True,
        'trace_stream_output_attribution_verified':False,
        'actual_vendor_syscall_dispatch_verified':False,
        'target_musl_linux_3_0_35_compatibility_verified':False,
        'kernel_configuration_and_preprocessor_variants_verified':False,
        'source_to_running_kernel_binary_reproducibility_verified':False,
        'kindle_ssh_sessions':0,
        'arm_binary_execution_performed':False,
        'firmware_write_performed':False,'physical_device_access_performed':False,'boot_performed':False,
        'recovery_verified':False,
    }

def preflight():
    return {'milestone':MILESTONE,'result':'HOLD','hold_category':'LOCAL_INPUTS_NOT_SUPPLIED',
            'immutable_hold':HOLD,'arm_binary_execution_performed':False,
            'physical_device_access_performed':False,'firmware_write_performed':False,'boot_performed':False}

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--r49-report')
    ap.add_argument('--header')
    ap.add_argument('--calls')
    a=ap.parse_args(argv)
    if not any((a.r49_report,a.header,a.calls)):
        print(json.dumps(preflight(),sort_keys=True));return 2
    if not all((a.r49_report,a.header,a.calls)):
        result=preflight();result['hold_category']='ALL_THREE_PINNED_INPUTS_REQUIRED'
        print(json.dumps(result,sort_keys=True));return 2
    try:
        report=json.loads(safe_read(a.r49_report,256000))
        result=audit(report,safe_read(a.header,256000),safe_read(a.calls,256000))
        print(json.dumps(result,indent=2,sort_keys=True));return 0
    except (OSError,UnicodeError,ValueError,TypeError,AuditHold,json.JSONDecodeError) as e:
        result=preflight();result['hold_category']=str(e) if isinstance(e,AuditHold) else 'INPUT_IO_OR_PARSE_FAILURE'
        print(json.dumps(result,sort_keys=True));return 2

if __name__=='__main__':
    sys.exit(main())
