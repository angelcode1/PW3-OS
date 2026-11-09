#!/usr/bin/env python3
"""R3877.85: guarded LuaJIT FFI libc/libm single-process ABI check.

Based exclusively on the checksum-pinned R3877.83 six-ELF bundle and remote
loader-mapping gate. Never touches GUI, boot, firmware, mounts, or userstore.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

import pw3_r3877_83_glibc_luajit_smoke as r83

R83_SHA256='c06918d8235b78687aa7a896b2a86c0d3371a11ad7b96ae8a0a959bef3faddf4'
MARKER=b'R3877_85_LUAJIT_FFI_LIBC_LIBM_OK\n'
OLD="""  -e 'io.write("R3877_83_GLIBC_LUAJIT_OK\\n")' || exit 53"""
# No imported KOReader modules; only LuaJIT's native FFI, glibc getpid, and
# explicit RAM-directory libm cos(0). Exact marker is the sole stdout allowed.
NEW="""  -e 'local ffi=require("ffi"); ffi.cdef("int getpid(void); double cos(double);"); local pid=tonumber(ffi.C.getpid()); assert(pid and pid>0); local lm=ffi.load(assert(os.getenv("HOME")).."/libm.so.6"); local v=tonumber(lm.cos(0.0)); assert(v and math.abs(v-1.0)<1e-12); io.write("R3877_85_LUAJIT_FFI_LIBC_LIBM_OK\\n")' || exit 53"""


def validate_original_source():
    p=Path(__file__).resolve().parent/'pw3_r3877_83_glibc_luajit_smoke.py'
    return hashlib.sha256(p.read_bytes()).hexdigest()==R83_SHA256


def remote_shell(objects):
    if not validate_original_source():
        raise ValueError('ORIGINAL_R83_SOURCE_CHANGED')
    shell=r83.remote_shell(objects)
    if shell.count(OLD)!=1 or shell.count('  --library-path "$work" --list "$work/luajit"')!=1:
        raise ValueError('ORIGINAL_EXEC_OR_MAPPING_GATE_CHANGED')
    shell=shell.replace(OLD,NEW,1)
    if 'R3877_83_GLIBC_LUAJIT_OK' in shell:
        raise ValueError('OLD_MARKER_REMAINS')
    return shell


def ssh_category(raw):
    s=raw.decode('utf-8','replace').lower()
    if 'permission denied' in s or 'authentication failed' in s: return 'AUTHENTICATION'
    if 'host key verification failed' in s or 'remote host identification has changed' in s: return 'HOST_KEY'
    if 'connection refused' in s or 'network is unreachable' in s: return 'NETWORK_CONNECTION'
    if 'timed out' in s or 'operation timed out' in s: return 'TIMEOUT'
    return 'UNCLASSIFIED'


def main(argv=None,runner=subprocess.run):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',required=True)
    p.add_argument('--review-only',action='store_true')
    p.add_argument('--acknowledge-one-shot-kindle-ffi-test',action='store_true')
    p.add_argument('--target',default='root@192.168.8.102')
    p.add_argument('--port',type=int,default=2222)
    a=p.parse_args(argv)
    report=r83.report_base()
    report.update(milestone='R3877.85',result='HOLD',hold_category='EXPLICIT_OPT_IN_REQUIRED',
                  ffi_libc_libm_calls_verified=False,complete_koreader_runtime_verified=False,
                  koreader_gui_started=False,immutable_hold='NOT_BOOTABLE',
                  prior_r83_device_pass='USER_REPORTED_NOT_INDEPENDENTLY_REPEATED')
    if a.review_only==a.acknowledge_one_shot_kindle_ffi_test:
        if a.review_only: report['hold_category']='MUTUALLY_EXCLUSIVE_MODES'
        print(json.dumps(report,sort_keys=True,separators=(',',':')))
        return 2
    if not re.fullmatch(r'root@[A-Za-z0-9][A-Za-z0-9.\-]{0,252}',a.target) or not 1<=a.port<=65535:
        report['hold_category']='TARGET_OR_PORT_INVALID'
        print(json.dumps(report,sort_keys=True,separators=(',',':')))
        return 2
    try:
        if not validate_original_source():raise ValueError('R83_SHA_MISMATCH')
        objects,review=r83.validate_stage(a.stage)
        payload=r83.bundle_tar(objects)
        shell=remote_shell(objects)
        report['host_bundle_sha256_verified']=True
        report['host_glibc_version_names_matched']=True
        report['host_bundle_bytes']=sum(map(len,objects.values()))
        report['rpath_entries_reviewed_but_inhibited']=len(review['objects']['luajit']['rpath_resolution_categories'])
        report['offline_validation_passed']=True
    except (OSError,ValueError,KeyError,r83.Hold,r83.r81.Refused,r83.r82.Refused) as exc:
        report['hold_category']='HOST_ELF_OR_PINNED_SOURCE_REVIEW_REFUSED'
        print(json.dumps(report,sort_keys=True,separators=(',',':')))
        return 2
    if a.review_only:
        report['hold_category']='HOST_FFI_TEST_READY_DEVICE_UNVERIFIED'
        print(json.dumps(report,sort_keys=True,separators=(',',':')))
        return 2
    cmd=['ssh','-T','-o','ConnectTimeout=15','-o','ConnectionAttempts=1',
         '-p',str(a.port),a.target,'sh -c '+shlex.quote(shell)]
    report['kindle_access_performed']=True
    report['device_execution_attempted']=True
    try:
        out=runner(cmd,input=payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                   timeout=75,check=False)
    except (OSError,subprocess.TimeoutExpired):
        report['hold_category']='SSH_OR_TIMEOUT_CLEANUP_UNVERIFIED'
    else:
        report['ssh_exit_code']=out.returncode
        if out.returncode==0 and out.stdout==MARKER:
            report.update(result='PASS_GLIBC_LUAJIT_FFI_LIBC_LIBM_SINGLE_PROCESS',
                          hold_category='KOREADER_APP_MODULES_GUI_BOOT_RECOVERY_UNVERIFIED',
                          glibc_loader_resolution_verified=True,
                          lua_native_execution_verified=True,
                          ffi_libc_libm_calls_verified=True,
                          tmpfs_cleanup_reported_complete=True)
        else:
            report['hold_category']=r83.FAILURES.get(out.returncode,'REMOTE_OUTPUT_OR_EXIT_UNEXPECTED')
            if out.returncode==255:report['ssh_failure_category']=ssh_category(out.stderr)
            report['tmpfs_cleanup_reported_complete']=False
    print(json.dumps(report,sort_keys=True,separators=(',',':')))
    return 0 if report['ffi_libc_libm_calls_verified'] else 2


if __name__=='__main__':sys.exit(main())
