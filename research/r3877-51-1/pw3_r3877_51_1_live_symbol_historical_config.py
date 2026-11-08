#!/usr/bin/env python3
"""R3877.51.1: offline, fail-closed cross-check of the user's R51 stock-kernel
receipt with historical R21 config metadata. This DOES NOT visit Kindle, run
ARM code, prove actual kernel syscall dispatch, or promote R51's config HOLD.
Research and educational purposes only. NOT_BOOTABLE immutable.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

MILESTONE = 'R3877.51.1'
HOLD = 'NOT_BOOTABLE'
LIVE_SHA256 = '3a6f6c4e4f12284f7f340740c36605bfb012a6631c81468c9901aa76e04a665d'
PRIOR_BLOB_SHA1 = 'b06ec168b5190d9b625d79449cbe09f960b037af'
EXPECTED_RELEASE = '3.0.35-lab126'
EXPECTED_MACHINE = 'armv7l'
SYMS = ('sys_brk','sys_exit_group','sys_getgid','sys_getuid','sys_ioctl',
        'sys_mmap2','sys_mprotect','sys_rt_sigprocmask','sys_set_tid_address',
        'sys_setgid','sys_setuid','sys_newuname','sys_write','sys_writev')
CONFIGS = ('CONFIG_AEABI','CONFIG_BINFMT_ELF','CONFIG_CPU_V7','CONFIG_FUTEX',
           'CONFIG_EPOLL','CONFIG_EVENTFD','CONFIG_SIGNALFD','CONFIG_TIMERFD',
           'CONFIG_INOTIFY_USER','CONFIG_HIGH_RES_TIMERS','CONFIG_UNIX',
           'CONFIG_VFP','CONFIG_NEON','CONFIG_SECCOMP','CONFIG_KALLSYMS',
           'CONFIG_IKCONFIG','CONFIG_IKCONFIG_PROC','CONFIG_SMP')
PRIOR_CONFIGS = ('CONFIG_AEABI','CONFIG_BINFMT_ELF','CONFIG_CPU_V7','CONFIG_FUTEX',
                 'CONFIG_EPOLL','CONFIG_EVENTFD','CONFIG_SIGNALFD','CONFIG_TIMERFD',
                 'CONFIG_INOTIFY_USER','CONFIG_HIGH_RES_TIMERS','CONFIG_UNIX',
                 'CONFIG_VFP','CONFIG_NEON','CONFIG_SECCOMP')

class EvidenceHold(Exception):
    pass


def git_blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()


def safe_bytes(path, limit):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or not (32 <= p.stat().st_size <= limit):
        raise EvidenceHold('INPUT_MISSING_SYMLINK_OR_SIZE')
    return p.read_bytes()


def read_receipt(raw):
    if not isinstance(raw,bytes) or not (700 <= len(raw) <= 8192):
        raise EvidenceHold('RECEIPT_BYTES_INVALID')
    try:
        s=raw.decode('utf-8','strict')
    except UnicodeDecodeError as exc:
        raise EvidenceHold('RECEIPT_ENCODING_INVALID') from exc
    if '\r' in s or '\0' in s or not s.endswith('\n'):
        raise EvidenceHold('RECEIPT_CONTROL_OR_NEWLINE_INVALID')
    lines=s.splitlines()
    if lines[0]!='PW3_R51_BEGIN' or lines[-1]!='PW3_R51_END':
        raise EvidenceHold('RECEIPT_SENTINEL_INVALID')
    scalars={}; cfg={}; sym={}
    for line in lines[1:-1]:
        fields=line.split('|')
        if len(fields)==2 and fields[0] in ('RELEASE','MACHINE','CONFIG_SOURCE','KALLSYMS_SOURCE'):
            if fields[0] in scalars:raise EvidenceHold('DUPLICATE_SCALAR')
            scalars[fields[0]]=fields[1]
        elif len(fields)==3 and fields[0]=='CFG' and fields[1] in CONFIGS and fields[2] in ('y','m','n','UNKNOWN'):
            if fields[1] in cfg: raise EvidenceHold('DUPLICATE_CONFIG')
            cfg[fields[1]]=fields[2]
        elif len(fields)==3 and fields[0]=='SYM' and fields[1] in SYMS and fields[2] in ('PRESENT','ABSENT','UNKNOWN'):
            if fields[1] in sym: raise EvidenceHold('DUPLICATE_SYMBOL')
            sym[fields[1]]=fields[2]
        else:
            raise EvidenceHold('RECEIPT_LINE_NOT_ALLOWLISTED')
    if set(scalars)!= {'RELEASE','MACHINE','CONFIG_SOURCE','KALLSYMS_SOURCE'} or set(cfg)!=set(CONFIGS) or set(sym)!=set(SYMS):
        raise EvidenceHold('RECEIPT_FIELDS_INCOMPLETE')
    if scalars['RELEASE']!=EXPECTED_RELEASE or scalars['MACHINE']!=EXPECTED_MACHINE:
        raise EvidenceHold('RUNNING_KERNEL_BASELINE_CHANGED')
    if scalars['CONFIG_SOURCE']!='UNAVAILABLE' or set(cfg.values())!={'UNKNOWN'}:
        raise EvidenceHold('RECEIPT_CONFIG_EXPECTATION_MISMATCH')
    if scalars['KALLSYMS_SOURCE']!='AVAILABLE' or set(sym.values())!={'PRESENT'}:
        raise EvidenceHold('RECEIPT_SYMBOLS_NOT_ALL_PRESENT')
    return scalars,cfg,sym


def read_prior(raw):
    if not isinstance(raw,bytes) or len(raw)>8192:
        raise EvidenceHold('PRIOR_BYTES_INVALID')
    try:
        r=json.loads(raw.decode('utf-8','strict'))
    except (UnicodeDecodeError, ValueError) as exc:
        raise EvidenceHold('PRIOR_JSON_INVALID') from exc
    if not isinstance(r,dict) or r.get('kernel_release')!=EXPECTED_RELEASE or r.get('machine')!=EXPECTED_MACHINE or r.get('immutable_hold')!=HOLD:
        raise EvidenceHold('PRIOR_BASELINE_INCONSISTENT')
    if r.get('kconfig_status')!='AVAILABLE' or r.get('binary_runtime_on_target_verified') is not False or r.get('recovery_verified') is not False:
        raise EvidenceHold('PRIOR_SCOPE_INCONSISTENT')
    cfg=r.get('kconfig')
    if not isinstance(cfg,dict) or set(cfg)!=set(PRIOR_CONFIGS) or any(v not in ('BUILTIN','MODULE','DISABLED','NOT_LISTED') for v in cfg.values()):
        raise EvidenceHold('PRIOR_CONFIG_INVALID')
    if not isinstance(r.get('source'),str) or not r['source'].startswith('User-reported R3877.13'):
        raise EvidenceHold('PRIOR_ORIGIN_INVALID')
    return r


def preflight():
    return {'milestone':MILESTONE, 'result':'HOLD','hold_category':'NO_OFFLINE_RECEIPT_VALIDATED',
            'immutable_hold':HOLD,'physical_device_access_performed':False,
            'ssh_sessions_in_this_audit':0,'arm_execution_in_this_audit':False,
            'boot_performed':False,'firmware_write_performed':False,
            'live_kernel_config_verified':False,'actual_vendor_syscall_dispatch_verified':False,
            'target_musl_linux_3_0_35_compatibility_verified':False,'recovery_verified':False}


def assess(receipt,prior,*,require_pins=True):
    if require_pins:
        if hashlib.sha256(receipt).hexdigest()!=LIVE_SHA256:
            raise EvidenceHold('LIVE_RECEIPT_SHA256_MISMATCH')
        if git_blob(prior)!=PRIOR_BLOB_SHA1:
            raise EvidenceHold('PRIOR_GIT_BLOB_SHA1_MISMATCH')
    scalars,cfg,sym=read_receipt(receipt)
    r=read_prior(prior)
    out=preflight()
    out.update(result='PASS_SELECTED_LIVE_SYMBOL_NAMES_HISTORICAL_CONFIG_CONTEXT_ONLY',
               hold_category='NOT_BOOTABLE',
               live_receipt_sha256=hashlib.sha256(receipt).hexdigest(),
               historical_config_git_blob_sha1=git_blob(prior),
               live_kernel_release=scalars['RELEASE'],live_machine=scalars['MACHINE'],
               live_kallsyms_source_available=True,
               selected_live_kernel_symbols_present=len(sym),selected_live_kernel_symbols_expected=len(SYMS),
               live_config_source='UNAVAILABLE',live_config_known_count=0,
               historical_reported_config_known_count=len(r['kconfig']),
               historical_config_only_not_live_attestation=True,
               historical_config_values={k:r['kconfig'][k] for k in sorted(r['kconfig'])},
               historical_config_origin=r['source'],
               historical_kernel_equals_live_release_and_arch=True,
               binary_provenance_to_public_source_verified=False,
               actual_vendor_syscall_dispatch_verified=False,
               live_kernel_config_verified=False,
               source_table_to_running_kernel_binary_verified=False,
               running_kernel_source_exact_build_verified=False,
               historical_report_does_not_fill_live_config_gap=True,
               trace_stream_output_attribution_verified=False)
    return out


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--live-receipt')
    ap.add_argument('--historical-r21-json')
    args=ap.parse_args(argv)
    out=preflight()
    try:
        if args.live_receipt and args.historical_r21_json:
            out=assess(safe_bytes(args.live_receipt,8192),safe_bytes(args.historical_r21_json,8192))
        elif args.live_receipt or args.historical_r21_json:
            raise EvidenceHold('BOTH_INPUTS_REQUIRED')
    except (EvidenceHold,OSError,ValueError) as exc:
        out['hold_category']=str(exc).splitlines()[0][:100] if isinstance(exc,EvidenceHold) else 'INPUT_IO_OR_VALUE_ERROR'
    print(json.dumps(out,sort_keys=True,separators=(',',':')))
    return 0 if out['result'].startswith('PASS_') else 2

if __name__=='__main__':
    sys.exit(main())
