#!/usr/bin/env python3
"""R3877.17.2: one SSH connection, two sequential read-only tar streams.

Nothing is uploaded or executed on the Kindle beyond its existing sh/tar.
No file content is persisted by this program. NOT_BOOTABLE always.
"""
import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import tarfile
import pw3_r3877_15_koreader_elf_audit as app
import pw3_r3877_16_system_elf_audit as syslib
import pw3_r3877_17_symbol_version_audit as r17

EXPECTED_TARGET = app.EXPECTED_TARGET
assert EXPECTED_TARGET == syslib.EXPECTED_TARGET == r17.EXPECTED_TARGET
MAX_COMBINED_ARCHIVE = app.MAX_ARCHIVE + syslib.MAX_ARCHIVE

# Reuse *unchanged* fixed-scope collection commands from R3877.15 and R3877.16.
# Both print tar data to the same binary stdout; no delimiters are inserted.
# Python's tarfile(ignore_zeros=True) supports concatenated tar streams.
TARGET_SCRIPT = (app.TARGET_SCRIPT.rstrip() + '\n'
                 'first_tar_status=$?\n'
                 '[ "$first_tar_status" -eq 0 ] || exit 51\n'
                 + syslib.TARGET_SCRIPT.rstrip() + '\n'
                 'second_tar_status=$?\n'
                 '[ "$second_tar_status" -eq 0 ] || exit 52\n')

class Hold(Exception):
    def __init__(self, category, **evidence):
        super().__init__(category)
        self.category = category
        self.evidence = evidence


def classify_ssh_error(raw, rc):
    """Classify stderr, but never disclose remote stderr (which may contain sensitive material)."""
    low = raw.decode('utf-8', 'replace').lower()[:16384]
    patterns = (
        ('too many authentication failures', 'SSH_TOO_MANY_AUTH_FAILURES'),
        ('permission denied', 'SSH_AUTHENTICATION_FAILURE'),
        ('host key verification failed', 'SSH_HOST_KEY_FAILURE'),
        ('remote host identification has changed', 'SSH_HOST_KEY_FAILURE'),
        ('connection refused', 'SSH_CONNECTION_REFUSED'),
        ('connection timed out', 'SSH_CONNECTION_TIMED_OUT'),
        ('operation timed out', 'SSH_CONNECTION_TIMED_OUT'),
        ('connection reset', 'SSH_CONNECTION_RESET'),
        ('connection closed', 'SSH_CONNECTION_CLOSED'),
        ('no route to host', 'SSH_NETWORK_UNREACHABLE'),
        ('no such host', 'SSH_DNS_FAILURE'),
        ('could not resolve hostname', 'SSH_DNS_FAILURE'),
        ('kex_exchange_identification', 'SSH_NEGOTIATION_FAILURE'),
        ('broken pipe', 'SSH_BROKEN_PIPE'),
        ('tar:', 'SSH_REMOTE_TAR_ERROR'),
    )
    for indicator, code in patterns:
        if indicator in low:
            return code
    return 'SSH_EXIT_255_UNCLASSIFIED' if rc == 255 else 'REMOTE_COMMAND_EXIT_'+str(rc)


def one_session_collect(target, port):
    try:
        cp = subprocess.run(
            ['ssh', '-T', '-p', str(port), '-o', 'ConnectTimeout=12',
             '-o', 'ConnectionAttempts=1', '--', target, 'sh -s'],
            input=TARGET_SCRIPT.encode('ascii'), capture_output=True, timeout=180)
    except subprocess.TimeoutExpired as e:
        raise Hold('SSH_COMMAND_TIMEOUT') from e
    except OSError as e:
        raise Hold('SSH_COMMAND_LAUNCH_FAILED', error_type=type(e).__name__) from e
    if cp.returncode != 0:
        raise Hold('SSH_COLLECTION_FAILED',
                   ssh_exit_code=cp.returncode,
                   ssh_error_class=classify_ssh_error(cp.stderr, cp.returncode),
                   ssh_stderr_sha256=hashlib.sha256(cp.stderr).hexdigest(),
                   ssh_stderr_bytes=len(cp.stderr))
    if len(cp.stdout) == 0 or len(cp.stdout) > MAX_COMBINED_ARCHIVE:
        raise Hold('COMBINED_ARCHIVE_EMPTY_OR_TOO_LARGE', total_bytes=len(cp.stdout))
    return cp.stdout


def parse_concatenated_archives(raw):
    """Strictly distinguish app files and fixed system libraries in two tar streams."""
    if not raw or len(raw) > MAX_COMBINED_ARCHIVE:
        raise Hold('COMBINED_ARCHIVE_EMPTY_OR_TOO_LARGE')
    app_files, system_files = {}, {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:', ignore_zeros=True) as tar:
            members = tar.getmembers()
            if len(members) < 2 or len(members) > app.MAX_MEMBERS + len(syslib.NAMES):
                raise Hold('COMBINED_MEMBER_COUNT_INVALID')
            app_members = 0
            for mem in members:
                name = mem.name
                if app.safe_name(name):
                    app_members += 1
                    if name in app_files: raise Hold('DUPLICATE_APP_ARCHIVE_MEMBER')
                    if mem.isfile():
                        if mem.size > app.MAX_MEMBER: raise Hold('APP_ARCHIVE_MEMBER_TOO_LARGE')
                        f = tar.extractfile(mem)
                        if f is None: raise Hold('APP_ARCHIVE_MEMBER_UNREADABLE')
                        value = f.read(app.MAX_MEMBER + 1)
                        if len(value) != mem.size: raise Hold('APP_ARCHIVE_MEMBER_TRUNCATED')
                        app_files[name] = ('file',value)
                    elif mem.issym():
                        if not re.fullmatch(r'[A-Za-z0-9_+.-]{1,180}',mem.linkname) or '..' in mem.linkname:
                            raise Hold('APP_SYMLINK_TARGET_UNSAFE')
                        app_files[name] = ('symlink',mem.linkname)
                    else:
                        raise Hold('UNEXPECTED_APP_ARCHIVE_MEMBER_TYPE')
                elif syslib.allowed_member(name):
                    if name in system_files: raise Hold('DUPLICATE_SYSTEM_ARCHIVE_MEMBER')
                    if not mem.isfile() or not 52 <= mem.size <= syslib.MAX_MEMBER:
                        raise Hold('INVALID_SYSTEM_ELF_MEMBER')
                    f = tar.extractfile(mem)
                    if f is None: raise Hold('SYSTEM_ARCHIVE_MEMBER_UNREADABLE')
                    value = f.read(syslib.MAX_MEMBER+1)
                    if len(value)!=mem.size: raise Hold('SYSTEM_ARCHIVE_MEMBER_TRUNCATED')
                    system_files[name] = value
                else:
                    raise Hold('UNEXPECTED_ARCHIVE_PATH')
            if app_members > app.MAX_MEMBERS: raise Hold('APP_ARCHIVE_MEMBER_COUNT_EXCEEDED')
    except (OSError,EOFError,tarfile.TarError) as e:
        raise Hold('INVALID_COMBINED_ARCHIVE_'+type(e).__name__) from e
    if not all(name in app_files and app_files[name][0]=='file' for name in ('fbink','luajit')):
        raise Hold('APP_REQUIRED_BINARIES_ABSENT')
    found_names = [path.rsplit('/',1)[-1] for path in system_files]
    if len(system_files)!=len(syslib.NAMES) or set(found_names)!=set(syslib.NAMES):
        raise Hold('SYSTEM_PROVIDER_SET_INCOMPLETE')
    if len(found_names)!=len(set(found_names)):
        raise Hold('DUPLICATE_SYSTEM_PROVIDER_NAME')
    return app_files, system_files


def main(argv=None):
    ap = argparse.ArgumentParser(description='R3877.17.2 single-SSH read-only ELF GNU version audit')
    ap.add_argument('--target')
    ap.add_argument('-p','--port',type=int,default=2222)
    ap.add_argument('--authorize-live-readonly-ssh',action='store_true')
    args=ap.parse_args(argv)
    out={'milestone':'R3877.17.2', 'result':'HOLD',
         'hold_category':'EXPLICIT_READONLY_SSH_AUTHORIZATION_REQUIRED',
         'immutable_hold':'NOT_BOOTABLE','authorized_live_readonly_ssh':bool(args.authorize_live_readonly_ssh),
         'ssh_sessions_requested':0,'boot_performed':False,'firmware_write_performed':False,
         'device_files_written':False,'new_target_binaries_installed_or_executed':False,
         'original_r13_stage_accessed':False,'personal_files_transferred':False,
         'app_and_stock_binary_contents_transferred':False,
         'target_musl_runtime_verified':False,'target_kernel_syscall_compatibility_verified':False,
         'recovery_verified':False,'koreader_dependency_closure_verified':False}
    if args.authorize_live_readonly_ssh:
        try:
            if args.target!=EXPECTED_TARGET: raise Hold('UNEXPECTED_SSH_TARGET')
            if not 1<=args.port<=65535: raise Hold('SSH_PORT_INVALID')
            out['ssh_sessions_requested']=1
            archive=one_session_collect(args.target,args.port)
            af,sf=parse_concatenated_archives(archive)
            out['app_and_stock_binary_contents_transferred']=True
            out['inventory']=r17.analyze(af,sf)
            if out['inventory']['version_requirements_statically_satisfied']:
                out['result']='PASS_VERSION_NAMES_METADATA_ONLY'
                out['hold_category']='NOT_BOOTABLE'
            else:
                out['hold_category']='MISSING_PROVIDER_OR_REQUIRED_SYMBOL_VERSION_NAME'
        except (Hold,app.Hold,syslib.Hold,r17.Hold) as e:
            out['hold_category']=e.category if isinstance(e,Hold) else str(e)
            if isinstance(e,Hold): out.update(e.evidence)
        except Exception as e:
            out['hold_category']='UNEXPECTED_'+type(e).__name__
    print(json.dumps(out,sort_keys=True,indent=2))
    return 0 if out['result']=='PASS_VERSION_NAMES_METADATA_ONLY' else 2

if __name__=='__main__': sys.exit(main())
