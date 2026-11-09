#!/usr/bin/env python3
"""Fail-closed analyzer for PW3 R3877.73 redacted kernel serial metadata.

Never opens devices, SSH, filesystems or UART; only reads one local text report.
A parsed report does not prove active U-Boot UART access or recoverability.
"""
import argparse
import json
from pathlib import Path
import re
import sys

KEYS = frozenset((
    'kernel', 'machine', 'cmdline_console_count', 'cmdline_console_class',
    'active_console_imx0', 'active_console_imx1', 'active_console_other_count',
    'sysfs_tty_ttymxc0_present', 'sysfs_tty_ttymxc1_present',
    'boot_mmcblk0boot0_force_ro', 'boot_mmcblk0boot1_force_ro',
    'boot_mmcblk0boot0_ro', 'boot_mmcblk0boot1_ro',
))
CONSOLE_CLASSES = frozenset((
    'NONE', 'IMX_UART0_115200', 'IMX_UART1_115200',
    'LOCAL_TTY', 'OTHER_REDACTED', 'MULTIPLE_REDACTED', 'UNAVAILABLE',
))


def analyze(data):
    result = dict(milestone='R3877.73', result='HOLD', immutable_hold='NOT_BOOTABLE',
                  hold_category='SERIAL_METADATA_INCOMPLETE_OR_INVALID',
                  physical_serial_console_verified=False,
                  active_uboot_environment_verified=False,
                  independent_restore_verified=False,
                  firmware_write_performed=False,
                  device_readonly_metadata_only=True)
    lines = data.splitlines()
    if len(lines) > 40 or lines.count('R3877_73_BEGIN') != 1 or lines.count('R3877_73_END') != 1:
        return result
    start, end = lines.index('R3877_73_BEGIN'), lines.index('R3877_73_END')
    if start >= end or lines[:start] or lines[end+1:]:
        return result
    values = {}
    for line in lines[start+1:end]:
        if '=' not in line:
            return result
        key, value = line.split('=', 1)
        if key not in KEYS or key in values or len(value) > 40:
            return result
        values[key] = value
    if set(values) != KEYS or values['kernel'] != '3.0.35-lab126' or values['machine'] != 'armv7l':
        return result
    n = values['cmdline_console_count']
    if n != 'UNAVAILABLE' and not (n.isdigit() and int(n) <= 10):
        return result
    c = values['cmdline_console_class']
    if c not in CONSOLE_CLASSES:
        return result
    if n == 'UNAVAILABLE' and c != 'UNAVAILABLE':
        return result
    if n == '0' and c != 'NONE':
        return result
    if n != 'UNAVAILABLE' and n.isdigit() and int(n) > 1 and c != 'MULTIPLE_REDACTED':
        return result
    if n == '1' and c in ('NONE', 'MULTIPLE_REDACTED', 'UNAVAILABLE'):
        return result
    for k in KEYS - {'kernel', 'machine', 'cmdline_console_count', 'cmdline_console_class'}:
        v = values[k]
        if k == 'active_console_other_count':
            if v != 'UNAVAILABLE' and not (v.isdigit() and int(v) <= 100):
                return result
        elif k.startswith('active_console_'):
            if v not in ('0','1','UNAVAILABLE'):
                return result
        elif k.startswith('boot_'):
            if v not in ('0','1','UNAVAILABLE'):
                return result
        elif v not in ('0','1'):
            return result
    result['hold_category'] = 'SERIAL_RECOVERY_HARDWARE_ACCESS_AND_RESTORE_UNVERIFIED'
    result['review'] = dict(
        kernel_console_metadata_parsed=True,
        cmdline_console_count=n,
        cmdline_console_class=c,
        active_console_imx0=values['active_console_imx0'],
        active_console_imx1=values['active_console_imx1'],
        active_console_other_count=values['active_console_other_count'],
        sysfs_ttymxc0_present=values['sysfs_tty_ttymxc0_present'],
        sysfs_ttymxc1_present=values['sysfs_tty_ttymxc1_present'],
        boot_area_write_protection_flags={
            'boot0_force_ro': values['boot_mmcblk0boot0_force_ro'],
            'boot1_force_ro': values['boot_mmcblk0boot1_force_ro'],
            'boot0_ro': values['boot_mmcblk0boot0_ro'],
            'boot1_ro': values['boot_mmcblk0boot1_ro'],
        },
        physical_uart_connection_verified=False,
        uboot_console_access_verified=False,
        independent_restore_verified=False,
    )
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input_file', nargs='?')
    a = p.parse_args(argv)
    report = analyze('')
    if a.input_file:
        try:
            file = Path(a.input_file)
            if file.is_symlink() or file.stat().st_size > 16_384:
                raise ValueError('input not bounded regular file')
            report = analyze(file.read_text(encoding='utf-8'))
        except (OSError, UnicodeError, ValueError):
            pass
    print(json.dumps(report, sort_keys=True, separators=(',', ':')))
    return 2


if __name__ == '__main__':
    sys.exit(main())
