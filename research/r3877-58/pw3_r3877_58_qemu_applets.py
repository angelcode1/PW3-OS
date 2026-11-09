#!/usr/bin/env python3
"""PW3 R3877.58: explicit off-device QEMU runtime tests on pinned ARMv7 BusyBox.

Research / education only. No Kindle operations, firmware writes, boots, host
binfmt setup, network, mounts, or new guest binaries except the pinned AArch64
QEMU executable in a disposable guest. Default preflight invokes NO Docker.
The pinned R49.3 isolation/cleanup runner is deliberately reused unchanged.
NOT_BOOTABLE is immutable. QEMU uses the host kernel, not Kindle Linux 3.0.35.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import re
import sys
from unittest.mock import patch

import pw3_r3877_49_3_controlled_trace as r49

MILESTONE = 'R3877.58'
PASS = 'PASS_PINNED_QEMU_BUSYBOX_ASH_STAT_DATE_URANDOM_RUNTIME_ONLY'
BASE_SHA256 = '5fa8ae5a386d32427ee67e068af55d4dd23a9e61b312357b00d9c0ed6d6ad659'
ASH_COMMAND = "printf 'PW3_R58_ASH_OK\\n'"
PROBE_ARGS = (
    ('qemu_version', ('--version',)),
    ('busybox_true_control', ('/bin/busybox', 'true')),
    ('ash_control', ('/bin/busybox','ash','-c',ASH_COMMAND)),
    ('stat_control', ('/bin/busybox','stat','-c','%s','/bin/busybox')),
    ('date_control', ('/bin/busybox','date','+%s')),
    ('urandom_control', ('/bin/busybox','od','-An','-tx1','-N16','/dev/urandom')),
    ('ash_trace', ('-strace','/bin/busybox','ash','-c',ASH_COMMAND)),
    ('stat_trace', ('-strace','/bin/busybox','stat','-c','%s','/bin/busybox')),
    ('date_trace', ('-strace','/bin/busybox','date','+%s')),
    ('urandom_trace', ('-strace','/bin/busybox','od','-An','-tx1','-N16','/dev/urandom')),
)
TRACES = frozenset({'ash_trace','stat_trace','date_trace','urandom_trace'})
CONTROLS = frozenset({'busybox_true_control','ash_control','stat_control','date_control','urandom_control'})
PAIRS = {'ash_trace':'ash_control','stat_trace':'stat_control','date_trace':'date_control','urandom_trace':'urandom_control'}
ORIGINAL_PROBE_OK = r49.probe_ok
NEW_CONTROLS = frozenset({'ash_control','stat_control','date_control','urandom_control'})

class Hold(Exception):
    pass


def require_base():
    p=Path(r49.__file__)
    if p.is_symlink() or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=BASE_SHA256:
        raise Hold('PINNED_R49_3_RUNNER_CHANGED')
    if r49.PARENT_ID!='sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a':
        raise Hold('PINNED_PARENT_IMAGE_ID_CHANGED')
    if r49.QEMU_SHA256!='3347b95a4006c1eb19b93ba09469a2c42b04fe5d89a430ce96cbf2a2367cf5c1':
        raise Hold('PINNED_QEMU_BYTES_CHANGED')
    if r49.BUSYBOX_SHA256!='df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c':
        raise Hold('PINNED_BUSYBOX_BYTES_CHANGED')
    return True


def control_output_ok(name, exit_code, output):
    """Strict, bounded validation of independent untraced applet outputs."""
    if not isinstance(output,str) or len(output.encode('utf-8'))>4096:
        return False
    if name=='qemu_version' or name=='busybox_true_control':
        return ORIGINAL_PROBE_OK(name,exit_code,output)
    if exit_code != 0:
        return False
    if name=='ash_control':
        return output=='PW3_R58_ASH_OK\n'
    if name=='stat_control':
        return bool(re.fullmatch(r'[1-9][0-9]{0,9}\n',output))
    if name=='date_control':
        return bool(re.fullmatch(r'[0-9]{10}\n',output) and 1577836800 <= int(output.strip()) <= 4102444800)
    if name=='urandom_control':
        # BusyBox od -An -tx1 -N16: 16 hex octets, optionally across lines.
        return len(output)<=128 and bool(re.fullmatch(r'(?:[ \t\r\n]*[0-9a-fA-F]{2}){16}[ \t\r\n]*',output))
    return False


def preflight():
    return dict(milestone=MILESTONE,result='HOLD',hold_category='OFFLINE_QEMU_OPT_IN_REQUIRED',
        immutable_hold='NOT_BOOTABLE',docker_used=False,offline_qemu_authorized=False,
        arm_guest_execution_performed=False,kindle_ssh_sessions=0,
        physical_device_access_performed=False,firmware_write_performed=False,
        boot_performed=False,host_binfmt_registration_changed=False,
        guest_network_enabled=False,host_mounts_enabled=False,
        target_musl_linux_3_0_35_compatibility_verified=False,
        vendor_kernel_syscall_dispatch_verified=False,
        arm_thread_clone_runtime_verified=False,
        runtime_getrandom_enosys_fallback_verified=False,
        qemu_guest_host_kernel_not_kindle_kernel=True,recovery_verified=False)


def assess_base(result):
    """Only promote R49 PASS when every new probe and cleanup is evidenced."""
    if not isinstance(result,dict) or result.get('result') != 'PASS_QEMU_SYSCALL_NAMES_AND_UNTRACED_APPLET_CONTROLS_ONLY':
        raise Hold('PINNED_R49_RUNTIME_HOLD')
    if result.get('original_image_unchanged') is not True or result.get('all_created_containers_removed') is not True:
        raise Hold('GUEST_CLEANUP_OR_PARENT_UNVERIFIED')
    if result.get('authorized_qemu_execution_performed') is not True or result.get('independent_untraced_controls_verified') is not True:
        raise Hold('QEMU_EXECUTION_OR_CONTROLS_UNVERIFIED')
    if result.get('qemu_binary_sha256')!=r49.QEMU_SHA256 or result.get('busybox_sha256')!=r49.BUSYBOX_SHA256:
        raise Hold('RUNTIME_BINARY_PINS_MISMATCH')
    probes=result.get('runtime_probes')
    if not isinstance(probes,dict) or set(probes)!={n for n,_ in PROBE_ARGS}:
        raise Hold('RUNTIME_PROBES_INCOMPLETE')
    for name in CONTROLS:
        if probes[name].get('status')!='PASS' or probes[name].get('exit_code')!=0 or probes[name].get('expected_applet_output_matches') is not True:
            raise Hold('UNTRACED_CONTROL_FAILED_'+name)
    diag={}
    for traced,control in PAIRS.items():
        p=probes[traced]
        t=p.get('trace',{})
        if (p.get('control_probe')!=control or p.get('untraced_control_verified') is not True
            or not str(p.get('status','')).startswith('TRACE_OBSERVED_')
            or p.get('exit_code')!=0 or not isinstance(t,dict)
            or not isinstance(t.get('syscall_record_count'),int) or t['syscall_record_count']<1):
            raise Hold('QEMU_TRACE_OR_UNTRACED_CONTROL_UNVERIFIED_'+traced)
        diag[traced]={
            'syscall_record_count':t['syscall_record_count'],
            'syscall_names':t.get('syscall_names',[]),
            'trace_unknown_record_count':t.get('trace_unknown_record_count'),
            'trace_enosys_record_count':t.get('trace_enosys_record_count'),
            'trace_unclassified_lines_present':p.get('trace_unclassified_lines_present'),
            'trace_output_attribution': 'UNVERIFIED',
        }
    return diag


def execute(allow_disposable_writable_layer=False):
    report=preflight()
    report.update(docker_used=True,offline_qemu_authorized=True,
        disposable_writable_layer_additional_opt_in=bool(allow_disposable_writable_layer))
    try:
        require_base()
        # Reuse the audited R49.3 isolation, QEMU injection, prior image ID,
        # Docker inspect policies, guest cleanup, and trace parser unchanged.
        with ExitStack() as patches:
            patches.enter_context(patch.object(r49,'PROBES',PROBE_ARGS))
            patches.enter_context(patch.object(r49,'TRACE_PROBES',TRACES))
            patches.enter_context(patch.object(r49,'CONTROL_PROBES',CONTROLS))
            patches.enter_context(patch.object(r49,'TRACE_TO_CONTROL',PAIRS))
            patches.enter_context(patch.object(r49,'probe_ok',control_output_ok))
            underlying=r49.run(allow_disposable_writable_layer)
        report['base_r49_result']=underlying.get('result')
        report['base_error_category']=underlying.get('error_category')
        report['original_image_unchanged']=underlying.get('original_image_unchanged',False)
        report['all_created_containers_removed']=underlying.get('all_created_containers_removed',False)
        report['arm_guest_execution_performed']=underlying.get('authorized_qemu_execution_performed',False)
        report['writable_fallback_used']=underlying.get('writable_fallback_used',False)
        report['read_only_copy_probe']=underlying.get('read_only_copy_probe')
        report['trace_stream_unclassified_output_present']=underlying.get('trace_stream_unclassified_output_present',False)
        report['baseline_probe_statuses']={k:v.get('status') for k,v in underlying.get('runtime_probes',{}).items()}
        diag=assess_base(underlying)
        report.update(result=PASS,hold_category='NOT_BOOTABLE',trace_diagnostics=diag,
            qemu_binary_sha256=r49.QEMU_SHA256,busybox_sha256=r49.BUSYBOX_SHA256,
            controls={'musl_startup_busybox_true':'PASS',
                      'ash_builtin_printf':'PASS','stat_existing_busybox_file':'PASS',
                      'date_seconds':'PASS','od_dev_urandom_16_bytes':'PASS'},
            note='QEMU guest runs on host Linux kernel, NOT on Kindle Linux 3.0.35')
    except (Hold,KeyError,TypeError,ValueError) as e:
        report.update(result='HOLD',hold_category=str(e).splitlines()[0][:140])
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--authorize-offline-qemu',action='store_true')
    p.add_argument('--allow-disposable-writable-layer',action='store_true')
    args=p.parse_args(argv)
    if args.allow_disposable_writable_layer and not args.authorize_offline_qemu:
        r=preflight();r['hold_category']='WRITABLE_OPT_IN_REQUIRES_QEMU_AUTHORIZATION'
    elif args.authorize_offline_qemu:
        r=execute(args.allow_disposable_writable_layer)
    else:
        r=preflight()
    print(json.dumps(r,sort_keys=True,separators=(',',':')))
    return 0 if r['result']==PASS else 2

if __name__=='__main__':sys.exit(main())
