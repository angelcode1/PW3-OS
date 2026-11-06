#!/usr/bin/env python3
"""R4043762: verify a public PW3-family reference kernel defconfig, offline and read-only.

This is NOT the live PW3 kernel configuration or runtime compatibility proof.
All output is a non-sensitive count/category summary. No device or rootfs inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

MILESTONE = 'R40.4.3.7.62'
REFERENCE_REPO = 'katadelos/linux-3.0.35-lab126'
REFERENCE_COMMIT = '7ac2585f384573da8cbdcc987a3503e2e6ff1fb4'
REFERENCE_BLOB_SHA1 = 'bbc2f92713d05dfd6ea52973fc7d958e49fa6464'
REFERENCE_BLOB_SIZE = 59582
REFERENCE_PATH = 'arch/arm/configs/imx60_wario_defconfig'
MAX_SIZE = 128 * 1024

FEATURES = {
    'ARM_EXECUTION': ('CONFIG_ARM', 'CONFIG_MMU', 'CONFIG_ARCH_MXC', 'CONFIG_ARCH_MX6'),
    'ARM_ELF_ABI': ('CONFIG_AEABI', 'CONFIG_OABI_COMPAT', 'CONFIG_BINFMT_ELF', 'CONFIG_BINFMT_MISC'),
    'PROCESS_THREADING': ('CONFIG_FUTEX', 'CONFIG_EPOLL', 'CONFIG_EVENTFD', 'CONFIG_INOTIFY_USER'),
    'CPU_INSTRUCTION_SET': ('CONFIG_ARM_THUMB', 'CONFIG_ARM_THUMBEE', 'CONFIG_VFP', 'CONFIG_VFPv3', 'CONFIG_NEON'),
    'KERNEL_POLICY': ('CONFIG_SECCOMP', 'CONFIG_FHANDLE', 'CONFIG_HIGH_RES_TIMERS', 'CONFIG_SMP'),
    'TLS_METADATA_FOLLOWUP': ('CONFIG_TLS_REG_EMUL', 'CONFIG_KUSER_HELPERS'),
}
# Confirmed directly from the public source, not inferred from PW3 hardware.
EXPECTED = {
    'CONFIG_ARM': 'ENABLED', 'CONFIG_MMU': 'ENABLED',
    'CONFIG_ARCH_MXC': 'ENABLED', 'CONFIG_ARCH_MX6': 'ENABLED',
    'CONFIG_AEABI': 'ENABLED', 'CONFIG_OABI_COMPAT': 'NOT_SET',
    'CONFIG_BINFMT_ELF': 'ENABLED', 'CONFIG_BINFMT_MISC': 'NOT_SET',
    'CONFIG_FUTEX': 'ENABLED', 'CONFIG_EPOLL': 'ENABLED',
    'CONFIG_EVENTFD': 'ENABLED', 'CONFIG_INOTIFY_USER': 'ENABLED',
    'CONFIG_ARM_THUMB': 'ENABLED', 'CONFIG_ARM_THUMBEE': 'NOT_SET',
    'CONFIG_VFP': 'ENABLED', 'CONFIG_VFPv3': 'ENABLED',
    'CONFIG_NEON': 'ENABLED', 'CONFIG_SECCOMP': 'NOT_SET',
    'CONFIG_FHANDLE': 'NOT_SET', 'CONFIG_HIGH_RES_TIMERS': 'ENABLED',
    'CONFIG_SMP': 'NOT_SET', 'CONFIG_TLS_REG_EMUL': 'NOT_DECLARED',
    'CONFIG_KUSER_HELPERS': 'NOT_DECLARED',
}

class Hold(Exception):
    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


def read_nofollow(path: Path) -> bytes:
    """Reject symlink path components and content changes while reading."""
    path = Path(os.path.abspath(str(path)))
    for parent in (path, *path.parents):
        try:
            st = parent.lstat()
        except OSError:
            raise Hold('REFERENCE_INPUT_MISSING_HOLD')
        if stat.S_ISLNK(st.st_mode):
            raise Hold('REFERENCE_PATH_SYMLINK_HOLD')
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0))
    except OSError:
        raise Hold('REFERENCE_OPEN_HOLD')
    try:
        a = os.fstat(fd)
        if not stat.S_ISREG(a.st_mode) or a.st_size <= 0 or a.st_size > MAX_SIZE:
            raise Hold('REFERENCE_NONREGULAR_OR_SIZE_HOLD')
        parts, size = [], 0
        while True:
            chunk = os.read(fd, 16384)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_SIZE:
                raise Hold('REFERENCE_OVERSIZE_HOLD')
            parts.append(chunk)
        b = os.fstat(fd)
        if (a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns) != (b.st_dev, b.st_ino, b.st_size, b.st_mtime_ns):
            raise Hold('REFERENCE_CHANGED_DURING_READ_HOLD')
        if size != a.st_size:
            raise Hold('REFERENCE_SHORT_READ_HOLD')
        return b''.join(parts)
    except OSError:
        raise Hold('REFERENCE_READ_HOLD')
    finally:
        os.close(fd)


def git_blob_id(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\x00' + data).hexdigest()


def require_reference_blob(data: bytes):
    if len(data) != REFERENCE_BLOB_SIZE or git_blob_id(data) != REFERENCE_BLOB_SHA1:
        raise Hold('PINNED_PUBLIC_REFERENCE_BLOB_MISMATCH_HOLD')


_CONF = re.compile(r'^(CONFIG_[A-Za-z0-9_]+)=(.*)$')
_UNSET = re.compile(r'^# (CONFIG_[A-Za-z0-9_]+) is not set$')

def parse_configuration(data: bytes) -> dict[str, str]:
    if b'\x00' in data or b'\r' in data:
        raise Hold('REFERENCE_NONCANONICAL_TEXT_HOLD')
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError:
        raise Hold('REFERENCE_NOT_UTF8_HOLD')
    if not text.startswith('#\n# Automatically generated make config: don\'t edit\n'):
        raise Hold('REFERENCE_CONFIG_HEADER_HOLD')
    if '# Linux/arm 3.0.35 Kernel Configuration' not in text[:512]:
        raise Hold('REFERENCE_KERNEL_VERSION_HEADER_HOLD')
    options: dict[str, str] = {}
    for line in text.splitlines():
        match = _CONF.fullmatch(line)
        if match:
            key, value = match.groups()
            if key in options:
                raise Hold('REFERENCE_DUPLICATE_OPTION_HOLD')
            if value == 'y':
                options[key] = 'ENABLED'
            elif value == 'm':
                options[key] = 'MODULE'
            elif value == 'n':
                options[key] = 'NOT_SET'
            elif not value or len(value) > 256:
                raise Hold('REFERENCE_INVALID_OPTION_HOLD')
            else:
                options[key] = 'OTHER_VALUE'
            continue
        match = _UNSET.fullmatch(line)
        if match:
            key = match.group(1)
            if key in options:
                raise Hold('REFERENCE_DUPLICATE_OPTION_HOLD')
            options[key] = 'NOT_SET'
    return options


def report_feature_groups(options: dict[str, str]) -> tuple[dict[str,dict[str,str]],int]:
    per_group = {group: {key: options.get(key, 'NOT_DECLARED') for key in fields}
                 for group, fields in FEATURES.items()}
    drift = sum(value != EXPECTED[key] for records in per_group.values() for key,value in records.items())
    return per_group,drift


def audit_bytes(data: bytes) -> dict:
    require_reference_blob(data)
    fields = parse_configuration(data)
    per_group, drift = report_feature_groups(fields)
    if drift:
        raise Hold('REFERENCE_FEATURE_TABLE_DISAGREEMENT_HOLD')
    return dict(milestone=MILESTONE,
                result='PUBLIC_WARIO_KERNEL_CONFIG_REFERENCE_STATIC_ONLY',
                source_repo=REFERENCE_REPO,
                source_commit_pinned=True,
                source_git_blob_sha1_verified=True,
                source_blob_size_verified=True,
                public_reference_kernel_version='3.0.35',
                reference_feature_groups=per_group,
                tracked_public_feature_keys=len(EXPECTED),
                tracked_reference_feature_disagreements=0,
                actual_pw3_running_kernel_config_verified=False,
                exact_device_firmware_kernel_identity_verified=False,
                kernel_abi_runtime_compatibility_verified=False,
                kernel_tls_runtime_compatibility_verified=False,
                kernel_config_omission_is_not_proof_of_absent_runtime_feature=True,
                guest_interpreter_path_resolved=False,
                original_r13_stage_modified=False,
                historical_inventory_hashes_changed=False,
                original_r26_image_origin_authenticated=False,
                mapping_applied=False,
                guest_execution_authorized=False,
                device_access_authorized=False,
                firmware_write_authorized=False,
                prune_authorized=False,
                boot_authorized=False,
                immutable_hold='NOT_BOOTABLE')


def main(argv=None):
    ap = argparse.ArgumentParser(description='R3762 SHA-pinned public kernel reference; no guest code')
    ap.add_argument('--reference-defconfig', required=True, type=Path)
    args = ap.parse_args(argv)
    try:
        obj = audit_bytes(read_nofollow(args.reference_defconfig))
        rc = 0
    except Hold as exc:
        obj = dict(milestone=MILESTONE, result='HOLD', hold_category=exc.category,
                   source_git_blob_sha1_verified=False,
                   actual_pw3_running_kernel_config_verified=False,
                   kernel_abi_runtime_compatibility_verified=False,
                   guest_interpreter_path_resolved=False,
                   original_r13_stage_modified=False, mapping_applied=False,
                   guest_execution_authorized=False, device_access_authorized=False,
                   boot_authorized=False, firmware_write_authorized=False,
                   prune_authorized=False, immutable_hold='NOT_BOOTABLE')
        rc = 2
    print(json.dumps(obj, sort_keys=True))
    return rc

if __name__ == '__main__':
    sys.exit(main())
