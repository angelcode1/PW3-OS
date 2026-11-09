#!/usr/bin/env python3
"""R3877.72: read-only offline U-Boot/normal/diags boot-chain evidence probe.

Never opens serial, SSH, device blocks or network; no file modifications.
Only fixed-size local backups are inspected; never prints raw data or private hashes.
Always HOLD / NOT_BOOTABLE, including after a structurally successful review.
"""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import zlib

SIZE_BOOT0 = 4_194_304
SIZE_PREPART = 33_554_432
KERNEL_OFFSET = {'normal': 0x41000, 'diagnostics': 0xE41000}
TARGET = b'Linux-3.0.35-lab126'

class Hold(Exception):
    pass


def open_fixed(directory, name, expected):
    root = Path(directory).expanduser()
    if root.is_symlink() or not root.is_dir():
        raise Hold('INVALID_ROOT')
    path = root / name
    if path.is_symlink():
        raise Hold('SYMLINK_REFUSED')
    fd = os.open(str(path), os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size != expected:
            raise Hold('IMAGE_WRONG_SIZE_OR_TYPE')
        return os.fdopen(fd, 'rb')
    except BaseException:
        os.close(fd)
        raise


def markers(boot0):
    """Search expected, exact NUL-terminated embedded strings, not live env."""
    required = {
        'uboot_lab126_build_string': b'U-Boot 2009.08-lab126',
        'normal_boot_command': b'bootcmd=bootm 0x41000\0',
        'diagnostics_boot_command': b'bootcmd_diags=bootm 0xE41000\0',
        'serial_baudrate': b'baudrate=115200\0',
    }
    if not all(v in boot0 for v in required.values()):
        raise Hold('EXPECTED_UBOOT_MARKERS_MISSING')
    delays = sorted({int(x) for x in re.findall(rb'bootdelay=([0-9]{1,3})\x00', boot0)})
    if not delays or any(x > 60 for x in delays):
        raise Hold('BOOT_DELAY_MARKERS_UNVERIFIED')
    return {
        'embedded_uboot_version_marker': '2009.08-lab126',
        'normal_boot_command_present': True,
        'diagnostics_boot_command_present': True,
        'serial_baudrate_marker': 115200,
        'bootdelay_values_observed': delays,
        'active_runtime_bootdelay_verified': False,
        'embedded_strings_are_live_environment_proof': False,
    }


def crc_segment(f, offset, size):
    f.seek(offset)
    crc = 0
    while size:
        b = f.read(min(65_536, size))
        if not b:
            raise Hold('SHORT_KERNEL_PAYLOAD')
        crc = zlib.crc32(b, crc)
        size -= len(b)
    return crc & 0xffffffff


def kernel_header(f, offset):
    f.seek(offset)
    h = f.read(64)
    if len(h) != 64:
        raise Hold('SHORT_KERNEL_HEADER')
    magic, hcrc, _timestamp, size, load, entry, dcrc, os_id, arch, typ, comp, name = struct.unpack('>7I4B32s', h)
    if (magic, os_id, arch, typ, comp) != (0x27051956, 5, 2, 2, 0):
        raise Hold('NOT_EXPECTED_ARM_LINUX_UIMAGE')
    if not (0 < size <= 8_388_608 and offset+64+size <= SIZE_PREPART):
        raise Hold('KERNEL_SIZE_INVALID')
    if load != 0x80008000 or entry != load or name.rstrip(b'\0') != TARGET:
        raise Hold('KERNEL_TARGET_UNEXPECTED')
    if zlib.crc32(h[:4] + b'\0'*4 + h[8:]) & 0xffffffff != hcrc:
        raise Hold('KERNEL_HEADER_CRC_MISMATCH')
    if crc_segment(f, offset + 64, size) != dcrc:
        raise Hold('KERNEL_PAYLOAD_CRC_MISMATCH')
    return {'offset_hex': hex(offset), 'payload_bytes': size, 'header_crc_verified': True,
            'payload_crc_verified': True, 'target': 'ARM_LINUX_3_0_35_LAB126'}


def inspect(directory):
    with open_fixed(directory, 'mmcblk0boot0.img', SIZE_BOOT0) as boot:
        text = boot.read(SIZE_BOOT0)
    observed = markers(text)
    with open_fixed(directory, 'mmcblk0-first32MiB.img', SIZE_PREPART) as prepart:
        images = {k: kernel_header(prepart, v) for k, v in KERNEL_OFFSET.items()}
    return {'status': 'OFFLINE_BOOT_CHAIN_STRUCTURAL_EVIDENCE_ONLY',
            'bootloader_markers': observed,
            'kernel_headers': images,
            'bootloader_commands_match_kernel_offsets': True,
            'serial_hardware_present_verified': False,
            'serial_log_captured': False,
            'uboot_console_access_verified': False,
            'diagnostics_boot_performed': False,
            'recovery_restore_tested': False,
            'stock_factory_provenance_verified': False,
            'no_local_files_modified': True,
            'no_device_access': True,
            'raw_names_or_private_digests_published': False}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image-dir')
    p.add_argument('--acknowledge-readonly-offline-boot-chain', action='store_true')
    a = p.parse_args(argv)
    report = {'milestone': 'R3877.72', 'result': 'HOLD', 'immutable_hold': 'NOT_BOOTABLE',
              'hold_category': 'EXPLICIT_OFFLINE_IMAGE_OPT_IN_REQUIRED',
              'kindle_ssh_sessions': 0, 'firmware_write_performed': False,
              'serial_port_opened': False, 'boot_performed': False,
              'local_files_modified': False, 'recovery_verified': False}
    if a.image_dir and a.acknowledge_readonly_offline_boot_chain:
        try:
            report['review'] = inspect(a.image_dir)
            report['hold_category'] = 'RECOVERY_CONSOLE_ACCESS_AND_INDEPENDENT_RESTORE_UNVERIFIED'
        except (OSError, Hold, ValueError, struct.error, OverflowError):
            report['hold_category'] = 'OFFLINE_BOOT_CHAIN_REVIEW_REFUSED'
    print(json.dumps(report, sort_keys=True, separators=(',', ':')))
    return 2

if __name__ == '__main__':
    sys.exit(main())
