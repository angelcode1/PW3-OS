#!/usr/bin/env python3
"""R3877.21 host-only ARM Linux syscall *source-names* and ABI risk matrix.

No subprocess, SSH, device access, guest execution, or writes except caller stdout.
Input 1 is a sanitized user-evidence JSON. Optional input 2 is local kernel
source arch/arm/include/asm/unistd.h, whose version is supplied explicitly.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

# All introduced-after evidence refers to mainstream Linux releases; vendor
# backports and custom syscall implementations are deliberately not ruled out.
NEWER_SYSCALLS = {
    'renameat2': ((3, 15), 'renameat2 flags require separate fallback/handling'),
    'getrandom': ((3, 17), 'verify entropy fallback; do not assume /dev/urandom correctness'),
    'statx': ((4, 11), 'verify stat/fstatat fallback if the application needs statx'),
    'clock_gettime64': ((5, 1), '32-bit ARM musl time64 fallback requires source/runtime audit'),
    'futex_time64': ((5, 1), '32-bit ARM musl timed synchronization requires fallback audit'),
    'clone3': ((5, 3), 'verify clone fallback for programs requesting clone3'),
    'openat2': ((5, 6), 'not all openat2 path-resolution guarantees have fallback'),
}
CORE_SYSCALL_NAMES = [
    'read', 'write', 'close', 'mmap2', 'mprotect', 'munmap', 'brk',
    'rt_sigaction', 'rt_sigprocmask', 'clone', 'set_tid_address',
    'futex', 'epoll_ctl', 'epoll_wait', 'eventfd2', 'signalfd4',
    'timerfd_create', 'clock_gettime', 'clock_nanosleep', 'openat',
]
REQUIRED_CONFIG = [
    'CONFIG_AEABI', 'CONFIG_BINFMT_ELF', 'CONFIG_CPU_V7',
    'CONFIG_FUTEX', 'CONFIG_EPOLL', 'CONFIG_EVENTFD', 'CONFIG_SIGNALFD',
    'CONFIG_TIMERFD', 'CONFIG_INOTIFY_USER', 'CONFIG_HIGH_RES_TIMERS',
]
# Linux's minimum documented musl general/POSIX kernel requirement.
GENERAL_MUSL_MIN = (2, 6, 39)
RELEASE = re.compile(r'^(\d+)\.(\d+)\.(\d+)(?:-[A-Za-z0-9_.-]+)?$')
SYSCALL = re.compile(
    r'^\s*#\s*define\s+__NR_([a-z][a-z0-9_]*)\s+' 
    r'\(\s*__NR_SYSCALL_BASE\s*\+\s*(\d+)\s*\)', re.M
)

class AuditError(Exception):
    pass


def safe_read(path, limit):
    p = pathlib.Path(path)
    if not p.is_file() or p.is_symlink():
        raise AuditError('INPUT_MISSING_OR_SYMLINK')
    if p.stat().st_size > limit or p.stat().st_size == 0:
        raise AuditError('INPUT_SIZE_OUT_OF_BOUNDS')
    return p.read_bytes()


def parse_kernel_version(value):
    if not isinstance(value, str):
        raise AuditError('KERNEL_RELEASE_INVALID')
    m = RELEASE.fullmatch(value)
    if not m:
        raise AuditError('KERNEL_RELEASE_INVALID')
    return tuple(int(v) for v in m.groups()[:3])


def parse_arm_syscalls(data):
    # Parse source text only; never preprocess, compile or evaluate macros.
    # Remove C comments to avoid reporting commented-out macros as real.
    s = data.decode('utf-8', 'strict')
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    s = re.sub(r'//[^\n]*', '', s)
    if '#define __NR_SYSCALL_BASE' not in s:
        raise AuditError('ARM_SOURCE_BASE_MISSING')
    numbers = {}
    for match in SYSCALL.finditer(s):
        name, n = match.group(1), int(match.group(2))
        if name in numbers and numbers[name] != n:
            raise AuditError('ARM_SYSCALL_DUPLICATE_CONFLICT')
        numbers[name] = n
    # Require a reasonable ARM header, rather than accepting a fabricated
    # tiny snippet as evidence of the complete upstream syscall table.
    if len(numbers) < 150:
        raise AuditError('ARM_SOURCE_TOO_FEW_ENTRIES')
    expected = {'read': 3, 'write': 4, 'futex': 240, 'clock_gettime': 263}
    if any(numbers.get(name) != nr for name, nr in expected.items()):
        raise AuditError('ARM_SOURCE_SENTINELS_MISMATCH')
    return numbers


def audit(evidence, arm_header=None, source_label=None, source_sha=None):
    if not isinstance(evidence, dict):
        raise AuditError('EVIDENCE_INVALID')
    kernel = parse_kernel_version(evidence.get('kernel_release'))
    if evidence.get('machine') != 'armv7l':
        raise AuditError('MACHINE_NOT_ARMV7L')
    if evidence.get('immutable_hold') != 'NOT_BOOTABLE':
        raise AuditError('HOLD_NOT_CONFIRMED')
    if evidence.get('root_backing_partition_verified') is not True or evidence.get('root_backing_partition') != 'mmcblk0p1':
        raise AuditError('ROOT_BASELINE_INCONSISTENT')
    if evidence.get('binary_runtime_on_target_verified') is not False or evidence.get('recovery_verified') is not False:
        raise AuditError('RUNTIME_OR_RECOVERY_BASELINE_INCONSISTENT')
    config = evidence.get('kconfig')
    if not isinstance(config, dict) or evidence.get('kconfig_status') != 'AVAILABLE':
        raise AuditError('KCONFIG_UNAVAILABLE')
    if any(config.get(k) not in ('BUILTIN', 'MODULE', 'DISABLED', 'NOT_LISTED') for k in REQUIRED_CONFIG):
        raise AuditError('KCONFIG_VALUE_INVALID')
    if evidence.get('hwcap_tls_reported') is not True:
        raise AuditError('HWCAP_TLS_BASELINE_UNAVAILABLE')
    if (arm_header is None) != (source_label is None):
        raise AuditError('HEADER_AND_SOURCE_LABEL_REQUIRED_TOGETHER')
    if source_label not in (None, 'upstream_linux_v3_0', 'vendor_3_0_35_unverified'):
        raise AuditError('SOURCE_LABEL_UNKNOWN')
    if source_sha is not None and arm_header is None:
        raise AuditError('SHA_ONLY_WITH_SOURCE')
    if arm_header is not None:
        digest = hashlib.sha256(arm_header).hexdigest()
        if source_sha is not None and source_sha.lower() != digest:
            raise AuditError('ARM_SOURCE_SHA256_MISMATCH')
        numbers = parse_arm_syscalls(arm_header)
    else:
        digest, numbers = None, None

    newer = {}
    for name, (introduced, why) in NEWER_SYSCALLS.items():
        newer[name] = {
            'mainline_first_kernel': '.'.join(map(str, introduced)),
            'mainline_postdates_device_kernel': kernel[:2] < introduced,
            'vendor_backport_checked': False,
            'actual_target_syscall_verified': False,
            'arm_source_number': numbers.get(name) if numbers else None,
            'review': why,
        }
    old = {k: {'arm_v3_0_source_number': numbers.get(k) if numbers else None,
               'source_name_in_supplied_header': k in numbers if numbers else None,
               'actual_target_dispatch_verified': False} for k in CORE_SYSCALL_NAMES}
    config_checks = {name: {'reported_status': config.get(name),
                            'actual_syscall_dispatch_verified': False}
                     for name in REQUIRED_CONFIG}
    return {
        'milestone': 'R3877.21',
        'result': 'PASS_UPSTREAM_ARM_SYSCALL_NAMES_METADATA_ONLY' if numbers and source_label == 'upstream_linux_v3_0' else 'PASS_VERSION_CONFIG_RISK_MATRIX_ONLY',
        'hold_category': 'NOT_BOOTABLE',
        'immutable_hold': 'NOT_BOOTABLE',
        'reference_kernel_release': evidence['kernel_release'],
        'kernel_version_exceeds_musl_general_minimum': kernel >= GENERAL_MUSL_MIN,
        'musl_general_minimum_is_not_application_compatibility_proof': True,
        'root_backing_partition_confirmed_from_prior_live_metadata': 'mmcblk0p1',
        'source': {
            'label': source_label,
            'sha256': digest,
            'parsed_arm_syscall_definitions': len(numbers) if numbers else 0,
            'same_as_running_vendor_kernel_verified': False,
            'kernel_table_binding_verified': False,
        },
        'kernel_config_reports': config_checks,
        'core_arm_syscall_names': old,
        'newer_mainline_syscall_baseline': newer,
        'vendor_backports_verified': False,
        'musl_exact_source_fallbacks_verified': False,
        'alpine_application_syscall_requirements_verified': False,
        'runtime_syscall_execution_verified': False,
        'koreader_dependency_closure_verified': False,
        'original_r13_stage_provenance_verified': False,
        'bootloader_verified': False,
        'rootfs_backup_verified': False,
        'recovery_verified': False,
        'physical_device_access_performed': False,
        'raw_device_bytes_read': False,
        'firmware_write_performed': False,
        'boot_performed': False,
    }


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('evidence_json')
    ap.add_argument('--kernel-arm-header',help='Optional local, known-origin ARM Linux unistd.h')
    ap.add_argument('--source-label',choices=['upstream_linux_v3_0', 'vendor_3_0_35_unverified'])
    ap.add_argument('--source-sha256',help='Optional pinned checksum of the provided kernel header')
    a=ap.parse_args(argv)
    try:
        evidence=json.loads(safe_read(a.evidence_json, 32_768))
        h=safe_read(a.kernel_arm_header, 256_000) if a.kernel_arm_header else None
        result=audit(evidence,h,a.source_label,a.source_sha256)
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0
    except (AuditError,UnicodeError,ValueError,json.JSONDecodeError, OSError) as exc:
        cat=str(exc) if isinstance(exc,AuditError) else 'INPUT_DECODE_OR_IO_ERROR'
        print(json.dumps({
            'milestone':'R3877.21','result':'HOLD','hold_category':cat,
            'immutable_hold':'NOT_BOOTABLE', 'boot_performed':False,
            'firmware_write_performed':False, 'physical_device_access_performed':False,
            'runtime_syscall_execution_verified':False,
        },indent=2,sort_keys=True))
        return 2
if __name__ == '__main__':
    sys.exit(main())
