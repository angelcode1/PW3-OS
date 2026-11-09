#!/usr/bin/env python3
"""Host-only diagnostics for R3877.59's first failing ARMv7 control.

The R59 test's underlying R49 runner records failed-control exit status but
R59's HOLD JSON omits it. This wrapper preserves those bounded diagnostics
without changing the underlying R49 runner, the pinned ARM ELF or its expected
output. No raw guest output or arbitrary environment text appears in JSON.

NOT_BOOTABLE is immutable. QEMU runs on Colima's host Linux, not Kindle kernel.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pw3_r3877_59_qemu_pthread_tls as r59

MILESTONE = 'R3877.59.1'
PASS = 'PASS_R59_PINNED_QEMU_PTHREAD_TLS_CONTROL_WITH_DIAGNOSTIC_ONLY'
R59_SCRIPT_SHA256 = 'c6151873a881f68fa13dd88910cfe712780d2db139c2e94596fca4381602d234'
KNOWN_MARKERS = frozenset({
 'R59_FAIL_MAIN_TLS_INIT',
 'R59_FAIL_PTHREAD_CREATE',
 'R59_FAIL_PTHREAD_TLS_OR_JOIN',
 'R59_PASS_ARMV7_PTHREAD_TLS',
 'R59_OBS_GETRANDOM_SUPPORTED_BY_HOST',
 'R59_OBS_GETRANDOM_ENOSYS',
 'R59_FAIL_GETRANDOM_UNEXPECTED',
 'R59_OBS_GETENTROPY_SUPPORTED_BY_HOST',
 'R59_FAIL_GETENTROPY',
 'R59_PASS_QEMU_ARMV7_MUSL_PROBE_ONLY',
})


def base_report():
    return dict(milestone=MILESTONE, result='HOLD',
        hold_category='OFFLINE_QEMU_OPT_IN_REQUIRED', immutable_hold='NOT_BOOTABLE',
        docker_used=False, arm_guest_execution_performed=False,
        physical_device_access_performed=False, firmware_write_performed=False,
        kindle_ssh_sessions=0, boot_performed=False,
        vendor_kernel_syscall_dispatch_verified=False,
        target_musl_linux_3_0_35_compatibility_verified=False,
        recovery_verified=False, runtime_getrandom_enosys_fallback_verified=False,
        original_patched_musl_binary_reproducibility_verified=False,
        raw_guest_output_published=False, no_changes_to_pinned_arm_elf=True,
        qemu_guest_uses_host_kernel_not_kindle_kernel=True)


def pin_check():
    source = Path(r59.__file__)
    if source.is_symlink() or not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != R59_SCRIPT_SHA256:
        raise ValueError('PINNED_R59_SCRIPT_CHANGED')
    r59.require_pinned()


def classified_output(name, rc, output, real_control, diagnostics):
    result=real_control(name,rc,output)
    if name=='r59_probe_control':
        if not isinstance(output,str) or len(output.encode('utf-8'))>1000000:
            raise ValueError('PROBE_OUTPUT_UNSAFE_OR_OVERSIZE')
        # Markers are ONLY exact strings compiled into the known ARM test. Other
        # stdout/stderr is represented by a digest/length, never raw text.
        lines=output.splitlines()
        found=sorted(set(lines) & KNOWN_MARKERS)
        diagnostics['control_output']={
            'exit_code':rc if isinstance(rc,int) else None,
            'output_bytes':len(output.encode('utf-8')),
            'output_sha256':hashlib.sha256(output.encode('utf-8')).hexdigest(),
            'allowlisted_program_markers':found,
            'unrecognized_line_count':sum(bool(x) and x not in KNOWN_MARKERS for x in lines),
            'expected_exact_output_matched':result,
            'raw_output_published':False,
        }
    return result


def sanitized_r49_details(raw):
    if not isinstance(raw,dict):
        raise ValueError('R49_RUN_RETURNED_INVALID_DATA')
    probes=raw.get('runtime_probes',{})
    if not isinstance(probes,dict): probes={}
    allowed_status={'PASS','HOLD','TRACE_OBSERVED_CLEAN_STREAM','TRACE_OBSERVED_UNCLASSIFIED_STREAM'}
    safe={}
    for name in ('qemu_version','busybox_true_control','r59_probe_control','r59_probe_trace'):
        v=probes.get(name)
        if not isinstance(v,dict):continue
        rc=v.get('exit_code')
        status=v.get('status')
        out={
            'status':status if status in allowed_status else 'UNKNOWN',
            'exit_code':rc if isinstance(rc,int) and -1024<=rc<=1024 else None,
            'expected_applet_output_matches':v.get('expected_applet_output_matches') if isinstance(v.get('expected_applet_output_matches'),bool) else None,
        }
        for field in ('program_output_sha256','output_sha256'):
            sha=v.get(field)
            if isinstance(sha,str) and len(sha)==64 and all(c in '0123456789abcdef' for c in sha):
                out[field]=sha
        n=v.get('program_output_bytes')
        if isinstance(n,int) and 0<=n<=1000000:out['program_output_bytes']=n
        safe[name]=out
    return dict(
        base_result=raw.get('result') if raw.get('result') in ('HOLD','PASS_QEMU_SYSCALL_NAMES_AND_UNTRACED_APPLET_CONTROLS_ONLY') else 'UNKNOWN',
        base_error_category=raw.get('error_category') if raw.get('error_category') in (
            None,'GUEST_PROBE_FAILED:r59_probe_control',
            'READONLY_COPY_REJECTED_WRITABLE_FALLBACK_NOT_AUTHORIZED') else 'OTHER_HOLD',
        baseline_probe_statuses=safe,
        all_created_containers_removed=raw.get('all_created_containers_removed') is True,
        original_image_unchanged=raw.get('original_image_unchanged') is True,
        arm_guest_execution_performed=raw.get('authorized_qemu_execution_performed') is True,
        writable_fallback_used=raw.get('writable_fallback_used') is True,
        read_only_copy_classification=((raw.get('read_only_copy_probe') or {}).get('classification') if (raw.get('read_only_copy_probe') or {}).get('classification') in ('READONLY_ROOTFS_COPY_REJECTED','READONLY_COPY_ACCEPTED') else 'UNKNOWN'),
    )


def execute(allow_writable):
    report=base_report()
    report.update(docker_used=True, offline_qemu_authorized=True,
                  disposable_writable_layer_additional_opt_in=bool(allow_writable))
    captured={}
    try:
        pin_check()
        original_run=r59.r49.run
        original_control=r59.control_output_ok
        def capture_underlying(allow):
            x=original_run(allow)
            captured['base']=sanitized_r49_details(x)
            return x
        def capture_output(name,rc,output):
            return classified_output(name,rc,output,original_control,captured)
        with ExitStack() as stack:
            stack.enter_context(patch.object(r59.r49,'run',capture_underlying))
            stack.enter_context(patch.object(r59,'control_output_ok',capture_output))
            underlying_r59=r59.execute(allow_writable)
        report['r59_result']=underlying_r59.get('result')
        report['r59_hold_category']=underlying_r59.get('hold_category')
        if 'base' in captured:
            report['diagnostics']=captured['base']
            report['arm_guest_execution_performed']=captured['base']['arm_guest_execution_performed']
            report['all_created_containers_removed']=captured['base']['all_created_containers_removed']
            report['original_image_unchanged']=captured['base']['original_image_unchanged']
            report['writable_fallback_used']=captured['base']['writable_fallback_used']
        if 'control_output' in captured:
            report['diagnostic_control_output']=captured['control_output']
        if underlying_r59.get('result')==r59.PASS:
            if not (report.get('all_created_containers_removed') is True and
                    report.get('original_image_unchanged') is True and
                    report.get('arm_guest_execution_performed') is True):
                raise ValueError('QEMU_PARENT_OR_CLEANUP_HOLD')
            report.update(result=PASS,hold_category='NOT_BOOTABLE',
                 arm_pthread_tls_host_qemu_verified=True,
                 getrandom_host_kernel_qemu_verified=True)
        else:
            report['hold_category']='R59_UNTRACED_CONTROL_OR_RUNTIME_HOLD'
    except (ValueError,TypeError,OSError,r59.Hold) as e:
        report.update(result='HOLD',hold_category=str(e).splitlines()[0][:140])
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--authorize-offline-qemu',action='store_true')
    p.add_argument('--allow-disposable-writable-layer',action='store_true')
    a=p.parse_args(argv)
    if a.allow_disposable_writable_layer and not a.authorize_offline_qemu:
        r=base_report();r['hold_category']='WRITABLE_OPT_IN_REQUIRES_QEMU_AUTHORIZATION'
    elif a.authorize_offline_qemu:r=execute(a.allow_disposable_writable_layer)
    else:r=base_report()
    print(json.dumps(r,sort_keys=True,separators=(',',':')))
    return 0 if r['result']==PASS else 2

if __name__=='__main__':sys.exit(main())
