#!/usr/bin/env python3
"""R3877.53: fail-closed, entirely host-only public source entropy ABI audit.

Research/educational only. No Kindle connection, Docker, QEMU, firmware or boot
operation; never claim running-vendor binary equivalence. NOT_BOOTABLE immutable.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

MILESTONE = 'R3877.53'
RESULT = 'PASS_PINNED_PUBLIC_LINUX3_ENTROPY_ABI_AND_MUSL_CALLPATH_SOURCE_ONLY'
PRIOR_RESULT = 'PASS_PINNED_UPSTREAM_MUSL_ARM_TLS_AND_OLDER_KERNEL_FALLBACK_SOURCE_ONLY'
SOURCE_PINS = {
    'lab126/arch/arm/include/asm/unistd.h': ('katadelos/linux-3.0.35-lab126', '7ac2585f384573da8cbdcc987a3503e2e6ff1fb4', 'arch/arm/include/asm/unistd.h', '2c04ed5efeb50707ac3353958434d37691841839'),
    'lab126/arch/arm/kernel/calls.S': ('katadelos/linux-3.0.35-lab126', '7ac2585f384573da8cbdcc987a3503e2e6ff1fb4', 'arch/arm/kernel/calls.S', '80f7896cc0164ad6f74469f1e777b90c1f306443'),
    'musl/src/linux/getrandom.c': ('ifduyue/musl', 'v1.2.6', 'src/linux/getrandom.c', '6cc6f6b047c18c9c8c564b5ece3f80a2f2b1f65f'),
    'musl/src/misc/getentropy.c': ('ifduyue/musl', 'v1.2.6', 'src/misc/getentropy.c', '651ea95f14310cda867b88378a0aedf2225d4462'),
    'musl/src/env/__libc_start_main.c': ('ifduyue/musl', 'v1.2.6', 'src/env/__libc_start_main.c', 'c5b277bdcf2e6b927dd93090137ea66dcb1c76a4'),
    'musl/src/env/__stack_chk_fail.c': ('ifduyue/musl', 'v1.2.6', 'src/env/__stack_chk_fail.c', 'e53526020f751d34542f07c6b30d94c5dc08bf72'),
}

class AuditHold(Exception):
    pass


def git_blob_sha1(raw):
    return hashlib.sha1(f'blob {len(raw)}\0'.encode('ascii') + raw).hexdigest()


def safe_read(path, max_bytes):
    """Reject file and any path ancestor that is a symlink, never follow one."""
    if not isinstance(path, Path):
        path = Path(path)
    for p in (path, *path.parents):
        if p.is_symlink():
            raise AuditHold('SYMLINK_REJECTED')
    if not path.exists():
        raise AuditHold('FILE_MISSING_OR_OUT_OF_BOUNDS')
    try:
        stat = path.stat()
        if not path.is_file() or not (1 <= stat.st_size <= max_bytes):
            raise AuditHold('FILE_MISSING_OR_OUT_OF_BOUNDS')
        raw = path.read_bytes()
    except OSError as e:
        raise AuditHold('FILE_READ_FAILED') from e
    if len(raw) != stat.st_size:
        raise AuditHold('FILE_CHANGED_DURING_READ')
    return raw


def load_sources(root, pins=SOURCE_PINS):
    root = Path(root)
    bodies = {}
    verified = {}
    for name, entry in pins.items():
        if len(entry) != 4 or not re.fullmatch(r'[a-zA-Z0-9_./-]+', name) or '..' in Path(name).parts or name.startswith('/'):
            raise AuditHold('PIN_MALFORMED')
        raw = safe_read(root / name, 65536)
        digest = git_blob_sha1(raw)
        if digest != entry[3]:
            raise AuditHold('PINNED_GIT_BLOB_MISMATCH_' + Path(name).name.replace('.', '_'))
        try:
            bodies[name] = raw.decode('utf-8')
        except UnicodeError as e:
            raise AuditHold('SOURCE_NOT_UTF8') from e
        verified[name] = digest
    return bodies, verified


def token(source, pattern, reason):
    if not re.search(pattern, source, flags=re.M):
        raise AuditHold(reason)


def check_source(bodies):
    expected = set(SOURCE_PINS)
    if set(bodies) != expected:
        raise AuditHold('SOURCE_INPUT_SET_CHANGED')
    header = bodies['lab126/arch/arm/include/asm/unistd.h']
    calls = bodies['lab126/arch/arm/kernel/calls.S']
    wrapper = bodies['musl/src/linux/getrandom.c']
    entropy = bodies['musl/src/misc/getentropy.c']
    init = bodies['musl/src/env/__libc_start_main.c']
    stack = bodies['musl/src/env/__stack_chk_fail.c']
    token(header, r'^#define\s+__NR_set_tid_address\s+\(__NR_SYSCALL_BASE\s*\+\s*256\)', 'PUBLIC_ARM_HEADER_UNRECOGNIZED')
    token(calls, r'CALL\s*\(sys_set_tid_address\)', 'PUBLIC_ARM_CALL_TABLE_UNRECOGNIZED')
    if re.search(r'^\s*#\s*define\s+__NR_getrandom\b', header, re.M):
        raise AuditHold('PUBLIC_ARM_HEADER_GETRANDOM_DEFINITION_UNEXPECTED')
    if re.search(r'\bCALL\s*\(\s*(?:sys_)?getrandom\s*\)', calls):
        raise AuditHold('PUBLIC_ARM_CALL_TABLE_GETRANDOM_UNEXPECTED')
    token(wrapper, r'\breturn\s+syscall_cp\s*\(\s*SYS_getrandom\s*,\s*buf\s*,\s*buflen\s*,\s*flags\s*\)', 'GETRANDOM_DIRECT_WRAPPER_MISSING')
    if 'ENOSYS' in wrapper or '/dev/urandom' in wrapper or 'SYS_open' in wrapper:
        raise AuditHold('GETRANDOM_WRAPPER_FALLBACK_CHANGED')
    token(entropy, r'\bret\s*=\s*getrandom\s*\(\s*pos\s*,\s*len\s*,\s*0\s*\)', 'GETENTROPY_CALLPATH_CHANGED')
    token(entropy, r'if\s*\(\s*errno\s*==\s*EINTR\s*\)\s*continue\s*;', 'GETENTROPY_EINTR_PATH_CHANGED')
    token(entropy, r'else\s+break\s*;', 'GETENTROPY_ERROR_PROPAGATION_CHANGED')
    if '/dev/urandom' in entropy or 'ENOSYS' in entropy:
        raise AuditHold('GETENTROPY_FALLBACK_CHANGED')
    token(init, r'__init_ssp\s*\(\s*\(void\s*\*\)\s*aux\s*\[\s*AT_RANDOM\s*\]\s*\)', 'AT_RANDOM_STARTUP_PATH_MISSING')
    token(stack, r'if\s*\(entropy\)\s*memcpy\s*\(&__stack_chk_guard,\s*entropy,\s*sizeof\(uintptr_t\)\)', 'STACK_CANARY_ENTROPY_SOURCE_CHANGED')
    token(stack, r'else\s+__stack_chk_guard\s*=\s*\(uintptr_t\)&__stack_chk_guard\s*\*\s*1103515245', 'STACK_CANARY_MISSING_AUX_FALLBACK_CHANGED')
    # Public source presence / absence is NOT equivalent to running vendor kernel.
    return {
        'public_linux3_arm_getrandom_syscall_definition_present': False,
        'public_linux3_arm_getrandom_dispatch_entry_present': False,
        'musl_getrandom_direct_syscall_wrapper_without_device_fallback_source': True,
        'musl_getentropy_uses_getrandom_without_enosys_fallback_source': True,
        'musl_stack_canary_seeded_from_kernel_auxv_AT_RANDOM_when_available_source': True,
        'musl_stack_canary_missing_auxv_uses_nonrandom_address_fallback_source': True,
        'AT_RANDOM_not_the_getrandom_syscall': True,
        'running_vendor_kernel_getrandom_availability_verified': False,
        'application_level_entropy_fallback_verified': False,
        'running_vendor_kernel_AT_RANDOM_contents_verified': False,
        'stack_canary_randomness_quality_verified': False,
        'musl_binary_equivalent_to_pinned_source_verified': False,
    }


def load_prior(path):
    raw = safe_read(Path(path), 32768)
    try:
        d = json.loads(raw)
    except (UnicodeError, ValueError) as e:
        raise AuditHold('PRIOR_JSON_INVALID') from e
    if not isinstance(d, dict) or d.get('result') != PRIOR_RESULT or d.get('immutable_hold') != 'NOT_BOOTABLE' or d.get('exit_code_reported') != 0:
        raise AuditHold('PRIOR_R52_PASS_EVIDENCE_REQUIRED')
    if d.get('verified_public_git_blob_count') != 13 or d.get('actual_vendor_syscall_dispatch_verified') is not False or d.get('target_musl_linux_3_0_35_compatibility_verified') is not False:
        raise AuditHold('PRIOR_R52_PASS_SCOPE_CHANGED')
    metadata = d.get('selected_live_metadata')
    if not isinstance(metadata, dict) or metadata.get('architecture') != 'armv7l' or metadata.get('kernel_release') != '3.0.35-lab126' or metadata.get('selected_config_count') != 18 or metadata.get('core_abi_config_flags_enabled') is not True:
        raise AuditHold('PRIOR_R52_LIVE_CONTEXT_CHANGED')
    return {'result':PRIOR_RESULT,'verified_public_git_blob_count':13,'kernel_release':'3.0.35-lab126','architecture':'armv7l'}


def run(source_dir, prior_path, pins=SOURCE_PINS):
    prior = load_prior(prior_path)
    bodies, digests = load_sources(source_dir, pins)
    source_audit = check_source(bodies)
    return {
        'milestone': MILESTONE,
        'result': RESULT,
        'hold_category': 'NOT_BOOTABLE',
        'immutable_hold': 'NOT_BOOTABLE',
        'selected_prior_user_reported_R52_1_evidence': prior,
        'public_source_git_blob_count': len(digests),
        'public_source_git_blob_sha1_by_path': digests,
        'source_audit': source_audit,
        'public_source_identical_to_running_vendor_binary_verified':False,
        'target_musl_linux_3_0_35_compatibility_verified':False,
        'firmware_write_performed':False,
        'kindle_ssh_sessions':0,
        'physical_device_access_performed':False,
        'arm_executable_launched':False,
        'docker_used':False,
        'boot_performed':False,
        'recovery_verified':False,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-dir')
    ap.add_argument('--r52-report')
    args = ap.parse_args(argv)
    data = {'milestone': MILESTONE, 'result':'HOLD', 'hold_category':'INPUTS_REQUIRED',
            'immutable_hold':'NOT_BOOTABLE','kindle_ssh_sessions':0,
            'physical_device_access_performed':False,'firmware_write_performed':False,
            'boot_performed':False,'target_musl_linux_3_0_35_compatibility_verified':False}
    if args.source_dir and args.r52_report:
        try:
            data = run(args.source_dir, args.r52_report)
        except AuditHold as e:
            data['hold_category'] = str(e)
        except (ValueError, OSError, UnicodeError):
            data['hold_category'] = 'LOCAL_INPUT_ERROR'
    print(json.dumps(data, sort_keys=True, separators=(',', ':')))
    return 0 if data['result'] == RESULT else 2

if __name__ == '__main__':
    sys.exit(main())
