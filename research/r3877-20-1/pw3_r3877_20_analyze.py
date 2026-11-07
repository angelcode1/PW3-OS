#!/usr/bin/env python3
"""Fail-closed analysis of a deliberately redacted, read-only PW3 mount inventory.

A root= command-line hint is NOT proof that a partition backs '/' on the
running Kindle. A pseudo rootfs entry is non-dispositive if exactly one ext3 block-root
entry matches mountinfo and sysfs; conflicting physical roots remain unresolved. This analyser cannot authorize device writes or boot changes.
"""
import argparse
import json
import re
import sys
from pathlib import Path

BEGIN = 'R3877_20_MOUNT_MAPPING_BEGIN'
END = 'R3877_20_MOUNT_MAPPING_COMPLETE'
MILESTONE = 'R3877.20.1'
FS = {'rootfs', 'ext2', 'ext3', 'ext4', 'squashfs', 'vfat', 'tmpfs', 'overlay', 'jffs2', 'ubifs', 'ramfs', 'OTHER_REDACTED'}
SRC = {'/dev/mmcblk0p1', '/dev/mmcblk0p2', '/dev/mmcblk0p3', '/dev/mmcblk0p4',
       '/dev/mmcblk0', '/dev/root', 'rootfs', 'none', 'tmpfs', 'overlay', 'OTHER_REDACTED'}
MP = {'/mnt/us', '/var/local', '/mnt/root', '/mnt/mmc', '/mnt/secondary', '/mnt/base-us'}


def base():
    return {
        'milestone': MILESTONE, 'result': 'HOLD', 'hold_category': 'MOUNTINFO_INCOMPLETE',
        'immutable_hold': 'NOT_BOOTABLE', 'root_backing_partition_verified': False,
        'bootloader_location_verified': False, 'bootloader_verified': False,
        'rootfs_backup_verified': False, 'recovery_verified': False,
        'alpine_runtime_verified': False, 'kernel_syscall_compatibility_verified': False,
        'raw_block_data_read': False, 'device_files_written': False,
        'firmware_write_performed': False, 'boot_performed': False,
        'full_kernel_cmdline_captured': False, 'personal_mount_paths_captured': False,
    }


def valid_mm(s):
    if not re.fullmatch(r'\d{1,4}:\d{1,5}', s):
        raise ValueError('MALFORMED_MAJOR_MINOR')
    a, b = (int(x) for x in s.split(':'))
    if a > 4095 or b > 1048575:
        raise ValueError('MALFORMED_MAJOR_MINOR')
    return s


def analyze(raw):
    out = base()
    if len(raw) > 65536 or '\x00' in raw:
        return {**out, 'hold_category': 'EXCESS_OR_BINARY_INPUT'}
    lines = [x.strip() for x in raw.splitlines() if x.strip()]
    if lines.count(BEGIN) != 1 or lines.count(END) != 1 or lines.index(BEGIN) >= lines.index(END):
        return {**out, 'hold_category': 'MISSING_OR_DUPLICATE_SENTINELS'}
    rows = lines[lines.index(BEGIN) + 1:lines.index(END)]
    scalars = {}
    root_proc, root_info, selected, sys_map = [], [], [], {}
    names = {'kernel_release','machine','boot_root_hint','boot_root_hint_count',
             'proc_mount_root_count','mountinfo_root_count','selected_mount_count'}
    try:
        for line in rows:
            if '=' not in line:
                raise ValueError('UNKNOWN_RECORD')
            key, val = line.split('=', 1)
            if key in names:
                if key in scalars:
                    raise ValueError('DUPLICATE_SCALAR')
                scalars[key] = val
            elif key == 'proc_mount_root':
                src, fs, ro = val.split('|')
                if src not in SRC or fs not in FS or ro not in ('ro', 'rw'):
                    raise ValueError('INVALID_ROOT_PROC_MOUNT')
                root_proc.append(dict(source=src, fstype=fs, access=ro))
            elif key == 'mountinfo_root':
                mm, fs, src, inroot, ro = val.split('|')
                valid_mm(mm)
                if fs not in FS or src not in SRC or inroot not in ('/', 'OTHER_REDACTED') or ro not in ('ro','rw'):
                    raise ValueError('INVALID_MOUNTINFO_ROOT')
                root_info.append(dict(major_minor=mm, fstype=fs, source=src, in_filesystem_root=inroot, access=ro))
            elif key == 'selected_mount':
                mp, mm, fs, src = val.split('|')
                valid_mm(mm)
                if mp not in MP or fs not in FS or src not in SRC:
                    raise ValueError('INVALID_SELECTED_MOUNT')
                selected.append(dict(mountpoint=mp, major_minor=mm, fstype=fs, source=src))
            elif key == 'sysfs_map':
                name, mm = val.split('|')
                if name not in ('mmcblk0p1','mmcblk0p2','mmcblk0p3','mmcblk0p4') or name in sys_map:
                    raise ValueError('INVALID_SYSFS_MAPPING')
                valid_mm(mm)
                sys_map[name] = mm
            else:
                raise ValueError('UNKNOWN_RECORD')
        if scalars.get('kernel_release') != '3.0.35-lab126' or scalars.get('machine') != 'armv7l':
            raise ValueError('WRONG_TARGET')
        needed = {'boot_root_hint','boot_root_hint_count','proc_mount_root_count','mountinfo_root_count','selected_mount_count'}
        if not needed.issubset(scalars):
            raise ValueError('MISSING_METADATA')
        hint = scalars['boot_root_hint']
        if hint not in {'/dev/mmcblk0p1','/dev/mmcblk0p2','/dev/mmcblk0p3','/dev/mmcblk0p4','/dev/root','rootfs',
                        'PARTUUID_PRESENT','UUID_PRESENT','OTHER_REDACTED','MULTIPLE_REDACTED','NOT_EXPOSED','NOT_PRESENT'}:
            raise ValueError('UNREDACTED_CMDLINE_TOKEN')
        hcount = scalars['boot_root_hint_count']
        if not re.fullmatch(r'\d{1,3}',hcount):
            raise ValueError('INVALID_HINT_COUNT')
        if (int(hcount) > 1) != (hint == 'MULTIPLE_REDACTED'):
            raise ValueError('INCONSISTENT_HINT_COUNT')
        for key, arr in [('proc_mount_root_count',root_proc),('mountinfo_root_count',root_info),('selected_mount_count',selected)]:
            count = scalars[key]
            if count == 'NOT_EXPOSED':
                if arr:
                    raise ValueError('INCONSISTENT_MOUNT_COUNT')
            elif not re.fullmatch(r'\d{1,4}',count) or int(count) != len(arr):
                raise ValueError('INCONSISTENT_MOUNT_COUNT')
        if not root_info and not root_proc:
            raise ValueError('ROOT_METADATA_NOT_PRESENT')
        if len(root_info)>16 or len(root_proc)>16 or len(selected)>32:
            raise ValueError('TOO_MANY_RECORDS')
        for name, mm in sys_map.items():
            if mm != f'179:{int(name[-1])}':
                raise ValueError('UNEXPECTED_SYSFS_MAJOR_MINOR')
    except (ValueError, TypeError) as e:
        reason = str(e) if isinstance(e, ValueError) else 'MALFORMED_RECORD'
        if reason not in {
            'UNKNOWN_RECORD','DUPLICATE_SCALAR','INVALID_ROOT_PROC_MOUNT',
            'INVALID_MOUNTINFO_ROOT','INVALID_SELECTED_MOUNT','INVALID_SYSFS_MAPPING',
            'MALFORMED_MAJOR_MINOR','WRONG_TARGET','MISSING_METADATA',
            'UNREDACTED_CMDLINE_TOKEN','INVALID_HINT_COUNT','INCONSISTENT_HINT_COUNT',
            'INCONSISTENT_MOUNT_COUNT','ROOT_METADATA_NOT_PRESENT','TOO_MANY_RECORDS',
            'UNEXPECTED_SYSFS_MAJOR_MINOR'}:
            reason='MALFORMED_RECORD'
        return {**out, 'hold_category': reason}

    physical = None
    # /proc/mounts may show both early virtual rootfs and the mounted
    # block-backed ext3 filesystem at /. Only one *physical* root entry is
    # acceptable. Do not mistake rootfs itself for the block backing.
    proc_pseudo = [r for r in root_proc if r['source'] == 'rootfs' and r['fstype'] == 'rootfs']
    proc_nonpseudo = [r for r in root_proc if not (r['source'] == 'rootfs' and r['fstype'] == 'rootfs')]
    root_metadata_ambiguous = (len(root_info) != 1 or len(proc_nonpseudo) != 1 or len(proc_pseudo) > 1)

    # The actual VFS mountinfo st_dev must equal a specific sysfs partition
    # major:minor, and the unique non-pseudo /proc/mounts root must agree on
    # source (including /dev/root alias), filesystem and read-only status.
    # A root= boot hint never substitutes for live mount metadata.
    if not root_metadata_ambiguous:
        ri, rp = root_info[0], proc_nonpseudo[0]
        for n in range(1, 5):
            name = f'mmcblk0p{n}'
            dev = f'/dev/{name}'
            if (ri['major_minor'] == f'179:{n}' and sys_map.get(name) == f'179:{n}'
                and ri['in_filesystem_root'] == '/'
                and ri['fstype'] == rp['fstype'] and ri['fstype'] in ('ext2', 'ext3', 'ext4')
                and ri['source'] in (dev, '/dev/root')
                and rp['source'] in (dev, '/dev/root')
                and ri['access'] == rp['access']):
                physical = name
                break

    out['inventory'] = {
        'kernel_release': scalars['kernel_release'],
        'machine': scalars['machine'],
        'boot_root_hint': hint,
        'boot_root_hint_is_runtime_proof': False,
        'root_proc_mounts': root_proc,
        'root_mountinfo_entries': root_info,
        'selected_nonroot_mounts': selected,
        'sysfs_partition_major_minor': dict(sorted(sys_map.items())),
        'root_partition_supported_by_direct_live_mount_metadata': physical,
        'rootfs_pseudo_mount_prevents_partition_inference': bool(root_info) and all(x['fstype'] == 'rootfs' for x in root_info),
        'root_metadata_ambiguous': root_metadata_ambiguous,
        'rootfs_pseudo_mount_observed': bool(proc_pseudo),
        'rootfs_pseudo_mount_ignored_for_physical_root_crosscheck': physical is not None and bool(proc_pseudo),
        'nonpseudo_proc_root_mount_count': len(proc_nonpseudo),
        'root_partition_evidence_type': 'LIVE_VFS_MOUNTINFO_PROC_MOUNTS_SYSFS_METADATA' if physical is not None else 'UNRESOLVED',
    }
    out['root_backing_partition_verified'] = physical is not None
    out['result'] = 'PASS_MOUNT_MAPPING_METADATA_ONLY'
    out['hold_category'] = 'NOT_BOOTABLE'
    return out


def main(argv=None):
    ap=argparse.ArgumentParser(description='Offline root mount metadata analyzer')
    ap.add_argument('inventory_file')
    args=ap.parse_args(argv)
    try:
        data=Path(args.inventory_file).read_text(encoding='utf-8')
        out=analyze(data)
    except (OSError,UnicodeError):
        out={**base(),'hold_category':'INPUT_UNREADABLE'}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out['result']=='PASS_MOUNT_MAPPING_METADATA_ONLY' else 2

if __name__=='__main__':
    raise SystemExit(main())
