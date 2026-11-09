#!/usr/bin/env python3
"""PW3 R3877.71: read-only, offline structural verification of private device images.

No physical device, SSH, mounts, execution, filesystem modifications, or raw hash
and filename publication. Results are structural evidence, never restore approval.
"""
import argparse
import json
from pathlib import Path
import stat
import struct
import sys
import zlib

EXPECTED = {
    'mmcblk0-first32MiB.img': 33_554_432,
    'mmcblk0p1.img': 471_859_200,
    'mmcblk0p2.img': 67_108_864,
    'mmcblk0boot0.img': 4_194_304,
    'mmcblk0boot1.img': 4_194_304,
}
GEOMETRY = ((0x83, 1, 65_536, 921_600),
            (0x83, 0, 987_136, 131_072),
            (0x83, 0, 1_118_208, 131_072),
            (0x0b, 0, 1_249_280, 6_385_664))

class Hold(Exception):
    pass


def images(root):
    root = Path(root).expanduser()
    if not root.is_dir() or root.is_symlink():
        raise Hold('IMAGE_DIRECTORY_INVALID')
    result = {}
    for name, size in EXPECTED.items():
        p = root / name
        if p.is_symlink():
            raise Hold('SYMLINK_IMAGE_REFUSED')
        if name == 'mmcblk0p1.img' and not p.exists():
            continue  # Allows reviewing the four uploaded images without falsely claiming p1 checked.
        s = p.stat()
        if not stat.S_ISREG(s.st_mode) or s.st_size != size:
            raise Hold('MISSING_OR_WRONG_SIZED_IMAGE')
        result[name] = p
    return result


def read_at(path, offset, length):
    with path.open('rb') as f:
        f.seek(offset)
        data = f.read(length)
    if len(data) != length:
        raise Hold('SHORT_IMAGE_READ')
    return data


def mbr_entries(sector):
    if len(sector) != 512 or sector[510:512] != b'\x55\xaa':
        raise Hold('MBR_SIGNATURE_INVALID')
    rows = []
    for i in range(4):
        b = sector[446 + i*16:462 + i*16]
        start, sectors = struct.unpack_from('<II', b, 8)
        rows.append((b[4], 1 if b[0] == 0x80 else 0, start, sectors))
    if tuple(rows) != GEOMETRY:
        raise Hold('MBR_GEOMETRY_OR_BOOT_FLAGS_MISMATCH')
    return rows


def crc_file_range(path, start, count):
    crc = 0
    with path.open('rb') as f:
        f.seek(start)
        while count:
            chunk = f.read(min(count, 65_536))
            if not chunk:
                raise Hold('KERNEL_PAYLOAD_SHORT_READ')
            crc = zlib.crc32(chunk, crc)
            count -= len(chunk)
    return crc & 0xffffffff


def uimage(path, offset):
    h = read_at(path, offset, 64)
    magic, hcrc, _stamp, n, load, entry, dcrc, os_id, arch, typ, comp, name = struct.unpack('>7I4B32s', h)
    if (magic, os_id, arch, typ, comp) != (0x27051956, 5, 2, 2, 0):
        raise Hold('EXPECTED_ARM_LINUX_UIMAGE_MISSING')
    if not (0 < n <= 8_388_608 and offset + 64 + n <= EXPECTED['mmcblk0-first32MiB.img']):
        raise Hold('UIMAGE_LENGTH_INVALID')
    blanked = h[:4] + b'\0\0\0\0' + h[8:]
    if zlib.crc32(blanked) & 0xffffffff != hcrc:
        raise Hold('UIMAGE_HEADER_CRC_MISMATCH')
    if crc_file_range(path, offset + 64, n) != dcrc:
        raise Hold('UIMAGE_DATA_CRC_MISMATCH')
    if load != 0x80008000 or entry != load or name.rstrip(b'\0') != b'Linux-3.0.35-lab126':
        raise Hold('UIMAGE_TARGET_METADATA_MISMATCH')
    return {'offset_hex': hex(offset), 'payload_bytes': n, 'header_crc_valid': True,
            'payload_crc_valid': True, 'target': 'ARM_LINUX_3_0_35_LAB126'}


def ext3_magic(path):
    if read_at(path, 1024 + 56, 2) != b'\x53\xef':
        raise Hold('EXT_FAMILY_SUPERBLOCK_MISSING')
    compat = struct.unpack('<I', read_at(path, 1024 + 92, 4))[0]
    # EXT3 commonly has the HAS_JOURNAL compatible feature (bit 2).
    if not (compat & 0x4):
        raise Hold('EXT3_JOURNAL_FEATURE_MISSING')
    return True


def any_nonzero(path):
    found = False
    with path.open('rb') as f:
        while True:
            part = f.read(65_536)
            if not part:
                break
            found = found or any(part)
    return found


def boot0_markers(path):
    # Only search for fixed, publicly documented markers, never emit raw bytes.
    needed = (b'U-Boot 2009.08-lab126', b'bootm 0x41000',
              b'bootm 0xE41000', b'bist fastboot')
    with path.open('rb') as f:
        buf = f.read(EXPECTED['mmcblk0boot0.img'])
    if not all(n in buf for n in needed):
        raise Hold('BOOT0_EXPECTED_MARKERS_MISSING')
    return True


def inspect(root):
    p = images(root)
    pre = p['mmcblk0-first32MiB.img']
    mbr_entries(read_at(pre, 0, 512))
    kernels = [uimage(pre, x) for x in (0x41000, 0xE41000)]
    if 'mmcblk0p1.img' in p:
        ext3_magic(p['mmcblk0p1.img'])
    ext3_magic(p['mmcblk0p2.img'])
    boot0_markers(p['mmcblk0boot0.img'])
    if any_nonzero(p['mmcblk0boot1.img']):
        raise Hold('BOOT1_NOT_ZERO_FILLED')
    p1_checked = 'mmcblk0p1.img' in p
    return {'complete_selected_image_set': p1_checked, 'image_count': len(p),
            'p1_image_structurally_checked': p1_checked,
            'mbr_four_partition_geometry_verified': True,
            'user_area_initial_gap_bytes': 33_554_432,
            'normal_and_diagnostics_kernels': kernels,
            'root_ext3_superblock_checked': p1_checked,
            'diagnostics_ext3_superblock_checked': True,
            'boot0_uboot_and_boot_commands_present': True,
            'boot1_zero_filled': True,
            'contains_raw_hashes_or_device_identifiers': False,
            'independent_restore_verified': False,
            'vendor_kernel_compatibility_verified': False}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--image-dir')
    ap.add_argument('--acknowledge-readonly-offline-images', action='store_true')
    args = ap.parse_args(argv)
    report = {'milestone': 'R3877.71', 'result': 'HOLD', 'immutable_hold': 'NOT_BOOTABLE',
              'hold_category': 'EXPLICIT_OFFLINE_IMAGE_ACCESS_REQUIRED',
              'kindle_ssh_sessions': 0, 'firmware_write_performed': False,
              'images_modified': False, 'raw_image_hashes_published': False,
              'independent_restore_verified': False}
    if args.image_dir and args.acknowledge_readonly_offline_images:
        try:
            report['review'] = inspect(args.image_dir)
            report['hold_category'] = 'RECOVERY_ACCESS_AND_INDEPENDENT_RESTORE_UNVERIFIED'
        except (Hold, OSError, ValueError, struct.error):
            report['hold_category'] = 'OFFLINE_IMAGE_STRUCTURAL_REVIEW_REFUSED'
    print(json.dumps(report, sort_keys=True, separators=(',', ':')))
    return 2


if __name__ == '__main__':
    sys.exit(main())
