#!/usr/bin/env python3
"""Host-only, pinned upstream Linux v3.0 ARM syscall-names crosscheck.

Research only. NEVER contacts or executes on Kindle; no Docker, SSH, root or raw block IO.
The checked Git blob is upstream, NOT proof of the Kindle 3.0.35-lab126 kernel tree.
"""
import argparse
import hashlib
import json
import pathlib
import sys
from pw3_r3877_21_arm_syscall_matrix import (
    AuditError, safe_read, audit as audit21, parse_arm_syscalls, CORE_SYSCALL_NAMES,
    NEWER_SYSCALLS,
)

EXPECTED_UPSTREAM_GIT_BLOB = '2c04ed5efeb50707ac3353958434d37691841839'
EXPECTED_SOURCE = 'https://raw.githubusercontent.com/torvalds/linux/v3.0/arch/arm/include/asm/unistd.h'
EXPECTED_KERNEL = '3.0.35-lab126'
REQUIRED_SENTINELS = {
    'read': 3, 'write': 4, 'close': 6, 'brk': 45,
    'clone': 120, 'mprotect': 125, 'rt_sigaction': 174,
    'rt_sigprocmask': 175, 'futex': 240, 'clock_gettime': 263,
}


def git_blob_sha1(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def assess(header, evidence, expected_blob_sha=EXPECTED_UPSTREAM_GIT_BLOB):
    if not isinstance(header, bytes) or not (1000 <= len(header) <= 256000):
        raise AuditError('SOURCE_SIZE_OUT_OF_BOUNDS')
    observed_blob_sha = git_blob_sha1(header)
    if observed_blob_sha != expected_blob_sha:
        raise AuditError('UPSTREAM_SOURCE_GIT_BLOB_MISMATCH')
    if b'arch/arm/include/asm/unistd.h' not in header:
        raise AuditError('SOURCE_PATH_MARKER_MISSING')
    baseline = audit21(evidence)
    if evidence['kernel_release'] != EXPECTED_KERNEL:
        raise AuditError('TARGET_KERNEL_BASELINE_CHANGED')
    nums = parse_arm_syscalls(header)
    for name, number in REQUIRED_SENTINELS.items():
        if nums.get(name) != number:
            raise AuditError('ARM_SYSCALL_SENTINEL_MISMATCH')
    # Report alias/conditional absence as unknown. Do NOT infer kernel dispatch.
    result = {
        'milestone': 'R3877.22',
        'result': 'PASS_PINNED_UPSTREAM_ARM_SOURCE_NAMES_ONLY',
        'hold_category': 'NOT_BOOTABLE',
        'immutable_hold': 'NOT_BOOTABLE',
        'source': {
            'label': 'linux_v3.0_upstream',
            'canonical_url': EXPECTED_SOURCE,
            'git_blob_sha1': observed_blob_sha,
            'sha256': hashlib.sha256(header).hexdigest(),
            'parsed_definitions': len(nums),
            'matches_exact_git_blob': True,
            'same_as_running_vendor_kernel_verified': False,
            'vendor_kernel_dispatch_verified': False,
        },
        'reference_kernel_release': EXPECTED_KERNEL,
        'core_arm_syscall_definitions': {
            n: {'upstream_arm_eabi_number':nums.get(n),
                'present_in_upstream_v3_0_header':n in nums,
                'kindle_vendor_dispatch_verified': False}
            for n in CORE_SYSCALL_NAMES
        },
        'post_v3_0_syscalls': {
            n: {'name_defined_in_upstream_v3_0':n in nums,
                'vendor_backport_checked': False,
                'application_requirement_checked': False}
            for n in NEWER_SYSCALLS
        },
        'upstream_all_20_core_names_defined': all(n in nums for n in CORE_SYSCALL_NAMES),
        'kernel_config_baseline_confirmed': baseline['reference_kernel_release'] == EXPECTED_KERNEL,
        'musl_exact_source_fallbacks_verified': False,
        'alpine_application_syscall_requirements_verified': False,
        'target_kernel_syscall_dispatch_verified': False,
        'runtime_syscall_execution_verified': False,
        'target_musl_runtime_verified': False,
        'recovery_verified': False,
        'original_r13_stage_provenance_verified': False,
        'physical_device_access_performed': False,
        'device_files_written': False,
        'boot_performed': False,
        'firmware_write_performed': False,
    }
    # If upstream header is incomplete for listed core calls, classify as HOLD.
    if not result['upstream_all_20_core_names_defined']:
        raise AuditError('UPSTREAM_SOURCE_CORE_DEFINITIONS_INCOMPLETE')
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('header',help='Locally downloaded original torvalds/linux v3.0 arch/arm/include/asm/unistd.h')
    parser.add_argument('evidence_json',help='Sanitized R3877.21 input JSON')
    args=parser.parse_args(argv)
    try:
        result=assess(safe_read(args.header,256000),json.loads(safe_read(args.evidence_json,32768)))
        print(json.dumps(result,sort_keys=True,indent=2))
        return 0
    except (AuditError,OSError,UnicodeError,ValueError,KeyError) as e:
        category=str(e) if isinstance(e,AuditError) else 'INPUT_DECODE_OR_IO_ERROR'
        print(json.dumps({'milestone':'R3877.22','result':'HOLD','hold_category':category,
            'immutable_hold':'NOT_BOOTABLE','boot_performed':False,
            'physical_device_access_performed':False,'device_files_written':False,
            'firmware_write_performed':False,'target_musl_runtime_verified':False},sort_keys=True,indent=2))
        return 2

if __name__=='__main__':
    sys.exit(main())
