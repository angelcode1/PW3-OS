#!/usr/bin/env python3
"""R3877.51 selected stock-kernel metadata triage. Research/educational only.

By default never contacts Kindle. Explicitly authorised SSH invokes only the
stock remote shell's read-only uname, config and /proc/kallsyms readers.
No kernel addresses, raw config text, IDs, mount tables or secrets are exported.
No firmware/boot/partition writes, new ARM executables, remote file creation,
privileged Docker, or physical boot changes. Immutable NOT_BOOTABLE hold.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

MILESTONE = 'R3877.51'
HOLD = 'NOT_BOOTABLE'
EXPECTED_KERNEL = '3.0.35-lab126'
EXPECTED_ARCH = 'armv7l'
CONFIG_KEYS = (
    'CONFIG_AEABI', 'CONFIG_BINFMT_ELF', 'CONFIG_CPU_V7',
    'CONFIG_FUTEX', 'CONFIG_EPOLL', 'CONFIG_EVENTFD',
    'CONFIG_SIGNALFD', 'CONFIG_TIMERFD', 'CONFIG_INOTIFY_USER',
    'CONFIG_HIGH_RES_TIMERS', 'CONFIG_UNIX', 'CONFIG_VFP',
    'CONFIG_NEON', 'CONFIG_SECCOMP', 'CONFIG_KALLSYMS',
    'CONFIG_IKCONFIG', 'CONFIG_IKCONFIG_PROC', 'CONFIG_SMP',
)
# This allowlist comes from the R3877.50 public source crosswalk.
SOURCE_ENTRY_SYMBOLS = (
    'sys_brk', 'sys_exit_group', 'sys_getgid', 'sys_getuid',
    'sys_ioctl', 'sys_mmap2', 'sys_mprotect', 'sys_rt_sigprocmask',
    'sys_set_tid_address', 'sys_setgid', 'sys_setuid', 'sys_newuname',
    'sys_write', 'sys_writev',
)
EXPECTED_NAME_TO_ENTRY = {
    'brk': 'sys_brk', 'exit_group': 'sys_exit_group',
    'getgid32': 'sys_getgid', 'getuid32': 'sys_getuid',
    'ioctl': 'sys_ioctl', 'mmap2': 'sys_mmap2',
    'mprotect': 'sys_mprotect', 'rt_sigprocmask': 'sys_rt_sigprocmask',
    'set_tid_address': 'sys_set_tid_address',
    'setgid32': 'sys_setgid', 'setuid32': 'sys_setuid',
    'uname': 'sys_newuname', 'write': 'sys_write', 'writev': 'sys_writev',
}
SOURCE_REVISION = '7ac2585f384573da8cbdcc987a3503e2e6ff1fb4'
SOURCE_HEADER_GIT_BLOB = '2c04ed5efeb50707ac3353958434d37691841839'
SOURCE_CALLS_GIT_BLOB = '80f7896cc0164ad6f74469f1e777b90c1f306443'

# Everything below is sent over stdin to a single stock /bin/sh process.
# Never print kernel symbol addresses or the full (possibly private) config.
# BusyBox awk, uname and zcat/gzip/cat are the only external utilities used.
REMOTE_SCRIPT = r'''#!/bin/sh
printf 'PW3_R51_BEGIN\n'
printf 'RELEASE|%s\n' "$(uname -r 2>/dev/null)"
printf 'MACHINE|%s\n' "$(uname -m 2>/dev/null)"
config_state=UNAVAILABLE
config_text=
if [ -r /proc/config.gz ]; then
  if command -v zcat >/dev/null 2>&1; then
    config_text=$(zcat /proc/config.gz 2>/dev/null) && [ -n "$config_text" ] && config_state=PROC_CONFIG_GZ
  elif command -v gzip >/dev/null 2>&1; then
    config_text=$(gzip -dc /proc/config.gz 2>/dev/null) && [ -n "$config_text" ] && config_state=PROC_CONFIG_GZ
  fi
fi
if [ "$config_state" = UNAVAILABLE ] && [ -r /proc/config ]; then
  config_text=$(cat /proc/config 2>/dev/null) && [ -n "$config_text" ] && config_state=PROC_CONFIG
fi
printf 'CONFIG_SOURCE|%s\n' "$config_state"
printf '%s\n' "$config_text" | awk -v keys='CONFIG_AEABI CONFIG_BINFMT_ELF CONFIG_CPU_V7 CONFIG_FUTEX CONFIG_EPOLL CONFIG_EVENTFD CONFIG_SIGNALFD CONFIG_TIMERFD CONFIG_INOTIFY_USER CONFIG_HIGH_RES_TIMERS CONFIG_UNIX CONFIG_VFP CONFIG_NEON CONFIG_SECCOMP CONFIG_KALLSYMS CONFIG_IKCONFIG CONFIG_IKCONFIG_PROC CONFIG_SMP' '
BEGIN { n=split(keys, names, " "); for(i=1;i<=n;i++) wanted[names[i]]=1 }
/^[A-Z_0-9]+=[ym]$/ { split($0,p,"="); if(p[1] in wanted) got[p[1]]=p[2] }
/^# CONFIG_[A-Z_0-9]+ is not set$/ { k=$2; if(k in wanted) got[k]="n" }
END { for(i=1;i<=n;i++){ k=names[i]; print "CFG|" k "|" (k in got ? got[k] : "UNKNOWN") } }'
if [ -r /proc/kallsyms ]; then
  symbols=$(awk -v keys='sys_brk sys_exit_group sys_getgid sys_getuid sys_ioctl sys_mmap2 sys_mprotect sys_rt_sigprocmask sys_set_tid_address sys_setgid sys_setuid sys_newuname sys_write sys_writev' '
BEGIN {n=split(keys,names," ");for(i=1;i<=n;i++) wanted[names[i]]=1}
NF>=3 { if($3 in wanted) found[$3]=1 }
END {for(i=1;i<=n;i++){k=names[i];print "SYM|" k "|" (k in found ? "PRESENT" : "ABSENT")}}' /proc/kallsyms 2>/dev/null)
  if [ "$?" -eq 0 ] && [ -n "$symbols" ]; then
    printf 'KALLSYMS_SOURCE|AVAILABLE\n'
    printf '%s\n' "$symbols"
  else
    printf 'KALLSYMS_SOURCE|UNAVAILABLE\n'
    for name in sys_brk sys_exit_group sys_getgid sys_getuid sys_ioctl sys_mmap2 sys_mprotect sys_rt_sigprocmask sys_set_tid_address sys_setgid sys_setuid sys_newuname sys_write sys_writev; do printf 'SYM|%s|UNKNOWN\n' "$name"; done
  fi
else
  printf 'KALLSYMS_SOURCE|UNAVAILABLE\n'
  for name in sys_brk sys_exit_group sys_getgid sys_getuid sys_ioctl sys_mmap2 sys_mprotect sys_rt_sigprocmask sys_set_tid_address sys_setgid sys_setuid sys_newuname sys_write sys_writev; do printf 'SYM|%s|UNKNOWN\n' "$name"; done
fi
printf 'PW3_R51_END\n'
'''

class AuditHold(Exception):
    pass


def selected_runtime_evidence():
    return {
        'milestone': MILESTONE, 'result': 'HOLD',
        'hold_category': 'NO_LIVE_READ_ONLY_EVIDENCE_YET',
        'immutable_hold': HOLD, 'physical_device_access_performed': False,
        'kindle_ssh_sessions': 0, 'new_kindle_binary_installed_or_executed': False,
        'boot_performed': False, 'firmware_write_performed': False,
        'running_kernel_matches_public_source_verified': False,
        'actual_vendor_syscall_dispatch_verified': False,
        'target_musl_linux_3_0_35_compatibility_verified': False,
        'recovery_verified': False,
    }


def parse_selected_lines(raw: str):
    if not isinstance(raw, str) or not (100 <= len(raw.encode('utf-8')) <= 8192):
        raise AuditHold('INPUT_SIZE_OR_TYPE_INVALID')
    if '\r' in raw or '\x00' in raw:
        raise AuditHold('INPUT_CONTROL_CHARACTER')
    lines = raw.splitlines()
    if not lines or lines[0] != 'PW3_R51_BEGIN' or lines[-1] != 'PW3_R51_END':
        raise AuditHold('RECEIPT_SENTINELS_INVALID')
    scalar = {}
    configs = {}
    symbols = {}
    for line in lines[1:-1]:
        parts = line.split('|')
        if len(parts) == 2 and parts[0] in ('RELEASE', 'MACHINE', 'CONFIG_SOURCE', 'KALLSYMS_SOURCE'):
            if parts[0] in scalar:
                raise AuditHold('DUPLICATE_SCALAR')
            scalar[parts[0]] = parts[1]
        elif len(parts) == 3 and parts[0] == 'CFG' and parts[1] in CONFIG_KEYS:
            if parts[1] in configs or parts[2] not in ('y','m','n','UNKNOWN'):
                raise AuditHold('CONFIG_VALUE_OR_DUPLICATE_INVALID')
            configs[parts[1]] = parts[2]
        elif len(parts) == 3 and parts[0] == 'SYM' and parts[1] in SOURCE_ENTRY_SYMBOLS:
            if parts[1] in symbols or parts[2] not in ('PRESENT','ABSENT','UNKNOWN'):
                raise AuditHold('SYMBOL_VALUE_OR_DUPLICATE_INVALID')
            symbols[parts[1]] = parts[2]
        else:
            raise AuditHold('UNEXPECTED_RECEIPT_LINE')
    if set(scalar) != {'RELEASE','MACHINE','CONFIG_SOURCE','KALLSYMS_SOURCE'}:
        raise AuditHold('REQUIRED_SCALAR_MISSING')
    if set(configs) != set(CONFIG_KEYS) or set(symbols) != set(SOURCE_ENTRY_SYMBOLS):
        raise AuditHold('REQUIRED_ALLOWLIST_ENTRIES_MISSING')
    if scalar['CONFIG_SOURCE'] not in ('PROC_CONFIG_GZ','PROC_CONFIG','UNAVAILABLE'):
        raise AuditHold('CONFIG_SOURCE_INVALID')
    if scalar['KALLSYMS_SOURCE'] not in ('AVAILABLE','UNAVAILABLE'):
        raise AuditHold('KALLSYMS_SOURCE_INVALID')
    if scalar['CONFIG_SOURCE'] == 'UNAVAILABLE' and any(x != 'UNKNOWN' for x in configs.values()):
        raise AuditHold('CONFIG_UNAVAILABLE_CONTRADICTS_VALUES')
    if scalar['KALLSYMS_SOURCE'] == 'UNAVAILABLE' and any(x != 'UNKNOWN' for x in symbols.values()):
        raise AuditHold('KALLSYMS_UNAVAILABLE_CONTRADICTS_VALUES')
    if not re.fullmatch('[A-Za-z0-9_.+-]{1,64}', scalar['RELEASE']):
        raise AuditHold('RELEASE_NOT_ALLOWLISTED')
    if not re.fullmatch('[A-Za-z0-9_-]{1,32}', scalar['MACHINE']):
        raise AuditHold('MACHINE_NOT_ALLOWLISTED')
    return scalar, configs, symbols


def assess(raw, *, from_ssh=False):
    scalar, configs, symbols = parse_selected_lines(raw)
    d = selected_runtime_evidence()
    d.update(physical_device_access_performed=bool(from_ssh), kindle_ssh_sessions=1 if from_ssh else 0,
             source_revision=SOURCE_REVISION, public_calls_git_blob_sha1=SOURCE_CALLS_GIT_BLOB,
             public_header_git_blob_sha1=SOURCE_HEADER_GIT_BLOB,
             kernel_release=scalar['RELEASE'], machine=scalar['MACHINE'],
             config_source=scalar['CONFIG_SOURCE'], kallsyms_source=scalar['KALLSYMS_SOURCE'],
             kconfig_allowlist_status=configs,
             kallsyms_source_entry_name_status=symbols,
             config_known_count=sum(v!='UNKNOWN' for v in configs.values()),
             kallsyms_entry_present_count=sum(v=='PRESENT' for v in symbols.values()),
             kallsyms_entry_absent_count=sum(v=='ABSENT' for v in symbols.values()),
             kallsyms_entry_unknown_count=sum(v=='UNKNOWN' for v in symbols.values()),
             missing_kallsyms_symbols_does_not_prove_missing_syscalls=True,
             source_table_to_running_kernel_binary_verified=False,
             running_kernel_matches_public_source_verified=False,
             actual_vendor_syscall_dispatch_verified=False,
             exact_source_to_binary_attestation_verified=False,
             target_musl_linux_3_0_35_compatibility_verified=False,
             new_kindle_binary_installed_or_executed=False,
             stock_userland_read_commands_requested=bool(from_ssh),
             raw_kernel_symbol_addresses_published=False,
             raw_kernel_config_published=False,
             device_identifiers_published=False)
    if scalar['RELEASE'] != EXPECTED_KERNEL or scalar['MACHINE'] != EXPECTED_ARCH:
        d['hold_category']='RUNNING_KERNEL_RELEASE_OR_ARCH_CHANGED'
    elif scalar['CONFIG_SOURCE'] == 'UNAVAILABLE' or d['config_known_count']==0:
        d['hold_category']='LIVE_KERNEL_CONFIG_UNAVAILABLE'
    else:
        d['result']='PASS_SELECTED_LIVE_KERNEL_CONFIG_AND_SYMBOL_NAMES_METADATA_ONLY'
        d['hold_category']='NOT_BOOTABLE'
    return d


def collect(target):
    # Never interpolate target into a shell command; reject strange SSH options.
    if not isinstance(target,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,31}@[A-Za-z0-9][A-Za-z0-9.:-]{0,127}',target):
        raise AuditHold('SSH_TARGET_FORMAT_INVALID')
    argv = ['ssh','-T','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
            '-o','UpdateHostKeys=no','-o','ConnectTimeout=8',
            '-o','NumberOfPasswordPrompts=0',target,'sh','-s']
    try:
        cp = subprocess.run(argv, input=REMOTE_SCRIPT, text=True, capture_output=True,
                            timeout=45, check=False, errors='replace')
    except (OSError,subprocess.TimeoutExpired) as ex:
        raise AuditHold('SSH_LAUNCH_OR_TIMEOUT') from ex
    if cp.returncode != 0:
        raise AuditHold('SSH_NONZERO_EXIT')
    if len(cp.stdout.encode('utf-8')) > 8192:
        raise AuditHold('SSH_OUTPUT_OVERSIZED')
    return cp.stdout


def read_input(path):
    p=Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size < 100 or p.stat().st_size > 8192:
        raise AuditHold('INPUT_FILE_MISSING_OR_OUT_OF_BOUNDS')
    return p.read_text('utf-8')


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    modes=ap.add_mutually_exclusive_group()
    modes.add_argument('--input-receipt',help='Parse a previously captured, sanitized R3877.51 receipt on Mac only')
    modes.add_argument('--authorize-readonly-kindle-ssh',action='store_true',help='One explicit stock-kernel read-only SSH session')
    ap.add_argument('--target',help='SSH target, for example root@your-kindle; not displayed in result')
    args=ap.parse_args(argv)
    result=selected_runtime_evidence()
    try:
        if args.authorize_readonly_kindle_ssh:
            if not args.target:
                raise AuditHold('SSH_TARGET_REQUIRED')
            result=assess(collect(args.target),from_ssh=True)
        elif args.input_receipt:
            if args.target:
                raise AuditHold('TARGET_WITH_OFFLINE_RECEIPT_INVALID')
            result=assess(read_input(args.input_receipt),from_ssh=False)
        elif args.target:
            raise AuditHold('SSH_AUTHORIZATION_REQUIRED')
    except (AuditHold, UnicodeError, OSError, ValueError) as exc:
        result['hold_category']=str(exc) if isinstance(exc,AuditHold) else 'INPUT_DECODE_OR_IO_ERROR'
        result['ssh_authorized_requested']=args.authorize_readonly_kindle_ssh
        if args.authorize_readonly_kindle_ssh:
            # We cannot prove whether an SSH connection was established on failure.
            result['kindle_ssh_sessions']='UNKNOWN_ON_FAILURE'
            result['physical_device_access_performed']='UNKNOWN_ON_FAILURE'
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
    return 0 if result['result'].startswith('PASS_') else 2

if __name__=='__main__':
    sys.exit(main())
