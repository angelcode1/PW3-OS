#!/usr/bin/env python3
"""R3877.52: offline pinned source audit of musl ARM TLS and old-kernel fallbacks.

Research/educational only. Never SSH, Docker, run binaries, inspect block devices,
change firmware, boot the Kindle, or establish deployed kernel ABI compatibility.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

MILESTONE = 'R3877.52'
HOLD = 'NOT_BOOTABLE'
ALPINE_APORTS_COMMIT = '35f5eb2864e50dd4448758d31f3e2a32f733ab84'
MUSL_TAG = 'v1.2.6'
LAB126_REV = '7ac2585f384573da8cbdcc987a3503e2e6ff1fb4'

# Paths are fixed in code, never constructed from user-provided repository names.
# Source identity is the Git SHA1 of the original *blob*, not the GitHub HTML page.
PINS = {
    'musl/src/thread/arm/__set_thread_area.c': '09de65aab04aa8a225d62515d74b61740a4ba8b7',
    'musl/src/thread/arm/clone.s': '4ff0c0e88b1d8892f914fc3b1703a1bf8a13239a',
    'musl/src/thread/pthread_create.c': '087f6206d5d64165bc54ae741e77099994ae96e0',
    'musl/arch/arm/pthread_arch.h': '157e2eae66d21203f13647cf12a3b556bbcd9642',
    'musl/src/time/clock_gettime.c': '4d2ec22f38a0012867632c7fcea763f090246174',
    'musl/src/time/clock_nanosleep.c': 'e195499cc0729ad4561e5244445f3e570b3aed1d',
    'musl/src/thread/__timedwait.c': '666093be98516a1c84b2997f075a8dbfcb797b2c',
    'musl/src/stat/fstatat.c': '9eed063b26bcfb1a0d52b700d153ac3ad718774f',
    'musl/src/linux/getrandom.c': '6cc6f6b047c18c9c8c564b5ece3f80a2f2b1f65f',
    'musl/src/misc/getentropy.c': '651ea95f14310cda867b88378a0aedf2225d4462',
    'lab126/arch/arm/include/asm/unistd.h': '2c04ed5efeb50707ac3353958434d37691841839',
    'lab126/arch/arm/kernel/traps.c': 'fcbf7c85bb1005091525f3417d202655d4727553',
    'lab126/arch/arm/kernel/entry-common.S': 'b2a27b6b0046ee6c1e0f0928c3269ab5f6c63cd2',
}

EXPECTED_CONFIG = {
    'CONFIG_AEABI': 'y', 'CONFIG_BINFMT_ELF': 'y', 'CONFIG_CPU_V7': 'y',
    'CONFIG_FUTEX': 'y', 'CONFIG_EPOLL': 'y', 'CONFIG_EVENTFD': 'y',
    'CONFIG_SIGNALFD': 'y', 'CONFIG_TIMERFD': 'y',
    'CONFIG_INOTIFY_USER': 'y', 'CONFIG_HIGH_RES_TIMERS': 'y',
    'CONFIG_UNIX': 'y', 'CONFIG_VFP': 'y', 'CONFIG_NEON': 'y',
    'CONFIG_SECCOMP': 'n', 'CONFIG_KALLSYMS': 'y', 'CONFIG_IKCONFIG': 'y',
    'CONFIG_IKCONFIG_PROC': 'y', 'CONFIG_SMP': 'n',
}
EXPECTED_COMPRESSED_SHA256 = 'dfaeb63750131da2259c37edd9b69a3574d4dd843b1f1e58eb7ad82b105ce4a2'
EXPECTED_DECODED_SHA256 = 'a305846a0ea0621f864f3f1d50e87fc95fb2c5b37886cc4a19b94a12711bbca8'

class AuditHold(Exception):
    pass


def git_blob_sha1(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def limited_file(path, maximum=131072):
    p = Path(path)
    # Do not follow symlinked files OR symlinked parent directories.
    if any(x.is_symlink() for x in (p, *p.parents)):
        raise AuditHold('SYMLINK_REJECTED')
    if not p.is_file() or p.stat().st_size < 1 or p.stat().st_size > maximum:
        raise AuditHold('SOURCE_MISSING_OR_SIZE_OUT_OF_BOUNDS')
    return p.read_bytes()


def load_sources(source_dir, pins=PINS):
    root = Path(source_dir)
    if not root.is_dir() or root.is_symlink():
        raise AuditHold('SOURCE_DIRECTORY_UNAVAILABLE')
    data = {}
    for path, expected in pins.items():
        try:
            b = limited_file(root / path)
        except OSError as e:
            raise AuditHold('SOURCE_IO_ERROR_' + path.replace('/', '_')) from e
        if git_blob_sha1(b) != expected:
            raise AuditHold('SOURCE_GIT_BLOB_MISMATCH_' + path.replace('/', '_'))
        try:
            data[path] = b.decode('utf-8')
        except UnicodeError as e:
            raise AuditHold('SOURCE_UTF8_INVALID_' + path.replace('/', '_')) from e
    return data


def require(src, pieces, label):
    if any(piece not in src for piece in pieces):
        raise AuditHold('MISSING_SOURCE_PATTERN_' + label)


def assess_live_selected(report):
    if not isinstance(report, dict):
        raise AuditHold('R51_EVIDENCE_NOT_AN_OBJECT')
    expected = {
        'milestone': 'R3877.51.3',
        'result': 'PASS_LOCAL_DECODED_KERNEL_CONFIG_AND_PRIOR_LIVE_SYMBOL_NAMES_ONLY',
        'immutable_hold': HOLD,
        'kernel_release': '3.0.35-lab126',
        'architecture': 'armv7l',
        'compressed_sha256': EXPECTED_COMPRESSED_SHA256,
        'decoded_sha256': EXPECTED_DECODED_SHA256,
        'config_decoder': 'MAC_PYTHON_ZLIB_GZIP',
        'config_known_count': 18,
        'config_unknown_count': 0,
        'previous_live_kallsyms_symbol_names_present': 14,
        'previous_live_kallsyms_symbol_names_checked': 14,
        'core_abi_config_flags_enabled': True,
        'target_musl_linux_3_0_35_compatibility_verified': False,
        'exact_source_to_kernel_binary_attestation_verified': False,
        'recovery_verified': False,
    }
    if any(report.get(key) != value for key, value in expected.items()):
        raise AuditHold('R51_SELECTED_PASS_EVIDENCE_CHANGED')
    if report.get('kconfig_allowlist_status') != EXPECTED_CONFIG:
        raise AuditHold('R51_CONFIG_VALUES_CHANGED')
    return {'kernel_release': '3.0.35-lab126', 'architecture': 'armv7l',
            'selected_config_count': len(EXPECTED_CONFIG),
            'core_abi_config_flags_enabled': True,
            'source': 'USER_REPORTED_R3877_51_3_READONLY_MAC_DECODE',
            'running_kernel_syscall_dispatch_verified': False}


def assess_sources(s):
    # Strong Git blob pins are mandatory in load_sources; semantic assertions
    # add interpretation checks, but NEVER amount to executed-branch proof.
    tls = s['musl/src/thread/arm/__set_thread_area.c']
    clone = s['musl/src/thread/arm/clone.s']
    create = s['musl/src/thread/pthread_create.c']
    arch = s['musl/arch/arm/pthread_arch.h']
    clock = s['musl/src/time/clock_gettime.c']
    nanosleep = s['musl/src/time/clock_nanosleep.c']
    futex = s['musl/src/thread/__timedwait.c']
    stat = s['musl/src/stat/fstatat.c']
    gr = s['musl/src/linux/getrandom.c']
    ent = s['musl/src/misc/getentropy.c']
    header = s['lab126/arch/arm/include/asm/unistd.h']
    traps = s['lab126/arch/arm/kernel/traps.c']
    entry = s['lab126/arch/arm/kernel/entry-common.S']

    require(tls, ['__syscall(0xf0005, p)', 'HWCAP_TLS'], 'ARM_PRIVATE_TLS_CALL')
    if not re.search(r'^\s*#define\s+__ARM_NR_set_tls\s*\(\s*__ARM_NR_BASE\s*\+\s*5\s*\)', header, re.M):
        raise AuditHold('LAB126_PRIVATE_TLS_NUMBER_MISMATCH')
    require(traps, ['case NR(set_tls):', 'thread->tp_value[0] = regs->ARM_r0;', 'if (has_tls_reg)'], 'LAB126_TLS_HANDLER')
    require(entry, ['__ARM_NR_BASE', 'arm_syscall'], 'LAB126_ARM_PRIVATE_DISPATCH')
    require(arch, ['mrc p15,0,%0,c13,c0,3', 'TLS_ABOVE_TP'], 'MUSL_ARM_THREAD_POINTER_READ')
    require(clone, ['mov r7,#120', 'svc 0'], 'MUSL_LEGACY_CLONE')
    require(create, ['CLONE_SETTLS', '__clone((', 'if (!libc.can_do_threads) return ENOSYS', 'CLONE_THREAD'], 'PTHREAD_CREATE_SOURCE')
    require(clock, ['SYS_clock_gettime64', 'r!=-ENOSYS', '__syscall(SYS_clock_gettime, clk, ts32)'], 'CLOCK_GETTIME_FALLBACK')
    require(nanosleep, ['SYS_clock_nanosleep_time64', 'r!=-ENOSYS', 'SYS_clock_nanosleep', 'SYS_nanosleep'], 'CLOCK_NANOSLEEP_FALLBACK')
    require(futex, ['SYS_futex_time64', 'r!=-ENOSYS', '__syscall_cp(SYS_futex', 'CLAMP(s)'], 'TIMED_FUTEX_FALLBACK')
    require(stat, ['SYS_statx', 'ret!=-ENOSYS', 'fstatat_kstat', '#ifdef SYS_fstatat'], 'FSTATAT_FALLBACK')
    require(gr, ['syscall_cp(SYS_getrandom, buf, buflen, flags)'], 'GETRANDOM_WRAPPER')
    require(ent, ['ret = getrandom(pos, len, 0)', 'if (errno == EINTR) continue;', 'else break;'], 'GETENTROPY_PROPAGATION')
    if any(x in gr or x in ent for x in ('/dev/urandom', '/dev/random', 'O_RDONLY')):
        raise AuditHold('GETRANDOM_ENTROPY_FALLBACK_SOURCE_CHANGED')

    return {
        'pinned_upstream_musl_source_version': '1.2.6',
        'pinned_aports_recipe_version_from_prior_evidence': '1.2.6-r3',
        'pinned_public_lab126_source_revision': LAB126_REV,
        'verified_public_git_blob_count': len(PINS),
        'arm_private_set_tls_number': '0x0f0005',
        'arm_private_set_tls_call_and_public_handler_source_present': True,
        'legacy_arm_clone_syscall_number': 120,
        'musl_pthread_create_uses_legacy_clone_and_clonettls': True,
        'musl_arm_thread_pointer_uses_cp15_source_path': True,
        'clock_gettime_time64_to_legacy_fallback_source_present': True,
        'clock_nanosleep_time64_to_legacy_fallback_source_present': True,
        'futex_time64_to_legacy_fallback_source_present': True,
        'fstatat_statx_to_legacy_fallback_source_present': True,
        'getrandom_and_getentropy_no_internal_device_fallback_source': True,
        'application_getrandom_callers_and_entropy_source_verified': False,
        'patched_musl_init_tls_source_and_built_loader_equivalence_verified': False,
        'conditional_compilation_verified': False,
        'kernel_arm_tls_private_dispatch_runtime_verified': False,
        'kernel_legacy_clone_runtime_verified': False,
    }


def run(source_dir, r51_report, *, pins=PINS):
    # Identity checks precede semantic checks; no network, shell or device ops.
    source = load_sources(source_dir, pins)
    selected = json.loads(limited_file(r51_report, 65536))
    live = assess_live_selected(selected)
    audit = assess_sources(source)
    return {
        'milestone': MILESTONE,
        'result': 'PASS_PINNED_UPSTREAM_MUSL_ARM_TLS_AND_OLDER_KERNEL_FALLBACK_SOURCE_ONLY',
        'hold_category': HOLD,
        'immutable_hold': HOLD,
        'source_audit': audit,
        'selected_live_metadata': live,
        'pinned_source_git_blob_sha1_by_path': dict(PINS),
        'public_source_to_running_kernel_binary_verified': False,
        'original_patched_musl_binary_reproducibility_verified': False,
        'actual_vendor_syscall_dispatch_verified': False,
        'target_musl_linux_3_0_35_compatibility_verified': False,
        'entropy_application_fallback_verified': False,
        'multithreaded_runtime_on_kindle_verified': False,
        'recovery_verified': False,
        'kindle_ssh_sessions': 0,
        'physical_device_access_performed': False,
        'firmware_write_performed': False,
        'boot_performed': False,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-dir', help='Local previously downloaded PUBLIC pinned source files')
    ap.add_argument('--r51-report', help='Sanitized R3877.51.3 selected PASS JSON; NOT the raw config')
    args = ap.parse_args(argv)
    result = {'milestone': MILESTONE, 'result': 'HOLD',
              'hold_category': 'EXPLICIT_PINNED_SOURCE_AND_R51_INPUT_REQUIRED',
              'immutable_hold': HOLD, 'kindle_ssh_sessions': 0,
              'physical_device_access_performed': False,
              'firmware_write_performed': False, 'boot_performed': False,
              'actual_vendor_syscall_dispatch_verified': False,
              'target_musl_linux_3_0_35_compatibility_verified': False,
              'recovery_verified': False}
    try:
        if args.source_dir and args.r51_report:
            result = run(Path(args.source_dir), Path(args.r51_report))
    except (AuditHold, OSError, UnicodeError, ValueError, TypeError, KeyError) as e:
        result['hold_category'] = str(e) if isinstance(e, AuditHold) else 'INPUT_INVALID_OR_IO_ERROR'
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['result'].startswith('PASS_') else 2


if __name__ == '__main__':
    sys.exit(main())
