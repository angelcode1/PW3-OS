#!/usr/bin/env python3
"""Reproduce one public-source config fingerprint; does not inspect Amazon archive.

This is only SHA-1/length reconciliation of a user-reported observation.
No network, archive extraction, device access, guest execution or boot.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

MILESTONE = 'R40.4.3.7.64'
REFERENCE = Path(__file__).resolve().parent.parent / 'r40.4.3.7.62' / 'corrected' / 'imx60_wario_defconfig'
OLD_SIZE = 59582
OLD_BLOB_SHA1 = 'bbc2f92713d05dfd6ea52973fc7d958e49fa6464'
OBSERVED_SIZE = 59593
OBSERVED_BLOB_SHA1 = 'b4ed2a1f317de6c11f75582327d847b30eae2547'
RECONSTRUCTED_SHA256 = '71eca1037a4428e11fb8a03c66e3ef78d5f0d24d5338035588c7963ed28b1833'
BEFORE = b'CONFIG_COMPAT_BRK=y\n'
AFTER = b'# CONFIG_COMPAT_BRK is not set\n'


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\x00' + data).hexdigest()


def read_reference():
    """Only read a regular pinned repository file; no symlink component."""
    p = Path(os.path.abspath(str(REFERENCE)))
    for node in (p, *p.parents):
        if stat.S_ISLNK(node.lstat().st_mode):
            raise ValueError('REFERENCE_SYMLINK_HOLD')
    fd = os.open(p, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        a = os.fstat(fd)
        if not stat.S_ISREG(a.st_mode) or a.st_size != OLD_SIZE:
            raise ValueError('REFERENCE_SIZE_HOLD')
        data = os.read(fd, OLD_SIZE + 1)
        b = os.fstat(fd)
        if (a.st_dev, a.st_ino, a.st_mtime_ns, a.st_size) != (b.st_dev, b.st_ino, b.st_mtime_ns, b.st_size):
            raise ValueError('REFERENCE_CHANGED_HOLD')
    finally:
        os.close(fd)
    if len(data) != OLD_SIZE or git_blob(data) != OLD_BLOB_SHA1:
        raise ValueError('REFERENCE_PIN_MISMATCH_HOLD')
    return data


def calculate(reference):
    if len(reference) != OLD_SIZE or git_blob(reference) != OLD_BLOB_SHA1:
        raise ValueError('REFERENCE_PIN_MISMATCH_HOLD')
    if reference.count(BEFORE) != 1 or AFTER in reference:
        raise ValueError('REFERENCE_COMPAT_BRK_UNEXPECTED_HOLD')
    candidate = reference.replace(BEFORE, AFTER)
    if len(candidate) != OBSERVED_SIZE or git_blob(candidate) != OBSERVED_BLOB_SHA1:
        raise ValueError('OBSERVED_BLOB_NOT_REPRODUCED_HOLD')
    sha256 = hashlib.sha256(candidate).hexdigest()
    if sha256 != RECONSTRUCTED_SHA256:
        raise ValueError('RECONSTRUCTION_SHA256_HOLD')
    return {
        'milestone': MILESTONE,
        'result': 'SINGLE_SETTING_FINGERPRINT_REPRODUCED_STATIC_ONLY',
        'reference_size_bytes': len(reference),
        'reference_blob_git_sha1': git_blob(reference),
        'reconstructed_size_bytes': len(candidate),
        'reconstructed_blob_git_sha1': git_blob(candidate),
        'reconstructed_sha256': sha256,
        'line_removed': BEFORE.decode().strip(),
        'line_inserted': AFTER.decode().strip(),
        'observed_amazon_blob_hash_matched': True,
        'actual_amazon_archive_opened': False,
        'amazon_config_full_bytes_compared': False,
        'r13_image_provenance_authenticated': False,
        'actual_pw3_running_kernel_verified': False,
        'kernel_abi_runtime_compatibility_verified': False,
        'guest_execution_authorized': False,
        'device_access_authorized': False,
        'firmware_write_authorized': False,
        'mapping_applied': False,
        'prune_authorized': False,
        'boot_authorized': False,
        'immutable_hold': 'NOT_BOOTABLE',
    }


def main():
    try:
        result = calculate(read_reference())
        code = 0
    except (ValueError, OSError) as exc:
        result = {
            'result': 'HOLD',
            'hold_category': str(exc) if isinstance(exc, ValueError) else 'REFERENCE_READ_HOLD',
            'milestone': MILESTONE,
            'boot_authorized': False,
            'immutable_hold': 'NOT_BOOTABLE',
        }
        code = 2
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
