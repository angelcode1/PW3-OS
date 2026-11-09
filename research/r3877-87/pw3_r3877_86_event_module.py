#!/usr/bin/env python3
"""Read-only pinned KOReader Event module preflight and optional one-shot ARM run.

Uses exactly the previously demonstrated R3877.83 six-ELF glibc bundle, plus
one byte-identical pinned 858-byte upstream KOReader frontend/ui/event.lua.
No GUI, framebuffer, input, storage, mounts, chroot, boot or firmware changes.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile

import pw3_r3877_83_glibc_luajit_smoke as r83

PRIOR_RUNNER_SHA256 = 'c06918d8235b78687aa7a896b2a86c0d3371a11ad7b96ae8a0a959bef3faddf4'
# Verified GitHub blob for koreader/koreader tag v2026.07.2,
# frontend/ui/event.lua. The actual file is read ONLY from the user's pinned R13 stage.
PINNED_UPSTREAM_GIT_BLOB_SHA1 = '3e042eb2a017e2a4e6fd27a6e4c1c7d2e388bd14'
MODULE_REL = 'opt/koreader-compat/app/frontend/ui/event.lua'
MODULE_NAME = 'event.lua'
MODULE_BYTES = 858
MARKER = b'R3877_86_KOREADER_EVENT_MODULE_OK\n'

# R83 contains precisely this one non-graphical LuaJIT launch.
ORIGINAL_EXEC = '''  -e 'io.write("R3877_83_GLIBC_LUAJIT_OK\\n")' || exit 53'''
LUA_CODE = (
    'local h=assert(os.getenv("HOME")); '
    'package.path=h.."/?.lua"; package.cpath=""; '
    'assert(package.loaded.event==nil); '
    'if not table.pack then table.pack=function(...) return {n=select("#",...), ...} end end; '
    'local Event=assert(require("event")); '
    'assert(type(Event)=="table" and type(Event.new)=="function"); '
    'local e=Event:new("Pw3Test",42,"ok"); '
    'assert(e.handler=="onPw3Test" and e.args.n==2 and e.args[1]==42 and e.args[2]=="ok"); '
    'io.write("R3877_86_KOREADER_EVENT_MODULE_OK\\n")'
)

class Refused(Exception):
    pass


def source_pin_check():
    p = Path(__file__).resolve().parent / 'pw3_r3877_83_glibc_luajit_smoke.py'
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest() == PRIOR_RUNNER_SHA256
    except OSError:
        return False


def read_pinned_event(stage):
    root = Path(stage).expanduser()
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise Refused('STAGE_ROOT_INVALID')
    path = root
    for comp in MODULE_REL.split('/')[:-1]:
        path = path / comp
        if path.is_symlink() or not path.is_dir():
            raise Refused('MODULE_PARENT_INVALID_OR_SYMLINK')
    name = path / 'event.lua'
    if name.is_symlink() or not name.is_file():
        raise Refused('MODULE_FILE_MISSING_OR_SYMLINK')
    # O_NOFOLLOW and stable stat metadata provided by the unchanged R81 reader.
    try:
        raw = r83.r81.raw_file(name)
    except (OSError, r83.r81.Refused) as exc:
        raise Refused('MODULE_SAFE_READ_FAILED') from exc
    if len(raw) != MODULE_BYTES:
        raise Refused('PINNED_EVENT_MODULE_LENGTH_MISMATCH')
    git_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if git_blob != PINNED_UPSTREAM_GIT_BLOB_SHA1:
        raise Refused('PINNED_EVENT_MODULE_CONTENT_MISMATCH')
    return raw


def make_archive(elf_objects, module):
    data = dict(elf_objects)
    data[MODULE_NAME] = module
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w', format=tarfile.USTAR_FORMAT) as tar:
        for name in ('luajit',) + r83.NAMES + (MODULE_NAME,):
            contents = data[name]
            entry = tarfile.TarInfo(name)
            entry.mode = 0o500
            entry.uid = entry.gid = 0
            entry.size = len(contents)
            entry.mtime = 0
            tar.addfile(entry, io.BytesIO(contents))
    return buffer.getvalue()


def remote_script(elf_objects, module):
    if not source_pin_check():
        raise Refused('R83_RUNNER_SOURCE_PIN_MISMATCH')
    sh = r83.remote_shell(elf_objects)
    old_dir = 'work="$place/pw3-r3877-83-$$"'
    old_cleanup = 'libm.so.6; do rm -f "$work/$f"; done'
    hash_gate = 'chmod 500 "$work/luajit" "$work/ld-linux.so.3" || exit 49'
    if any(sh.count(x) != 1 for x in (ORIGINAL_EXEC, old_dir, old_cleanup, hash_gate)):
        raise Refused('R83_REMOTE_TEMPLATE_CHANGED')
    sh = sh.replace(old_dir, 'work="$place/pw3-r3877-86-$$"', 1)
    sh = sh.replace(old_cleanup, 'libm.so.6 event.lua; do rm -f "$work/$f"; done', 1)
    gate = ('check_one event.lua ' + str(len(module)) + ' ' + hashlib.sha256(module).hexdigest() +
            ' || exit 48\n' + hash_gate)
    sh = sh.replace(hash_gate, gate, 1)
    # package.path is pinned to the one RAM-stage module and C module search disabled.
    sh = sh.replace(ORIGINAL_EXEC, '  -e ' + shlex.quote(LUA_CODE) + ' || exit 53', 1)
    if 'R3877_83_GLIBC_LUAJIT_OK' in sh or 'pw3-r3877-83-' in sh:
        raise Refused('PREVIOUS_TEST_MARKER_REMAINS')
    if sh.count('event.lua') < 2 or sh.count('--inhibit-rpath') < 2:
        raise Refused('R83_MAPPING_GATE_OR_EVENT_HASH_CHECK_MISSING')
    return sh


def base_report():
    r = r83.report_base()
    r.update(milestone='R3877.86', result='HOLD', immutable_hold='NOT_BOOTABLE',
             hold_category='EXPLICIT_OPT_IN_REQUIRED',
             pinned_event_module_sha1_verified=False,
             offline_validation_passed=False,
             koreader_real_module_require_verified=False,
             complete_koreader_runtime_verified=False,
             koreader_gui_started=False)
    return r


def ssh_category(stderr):
    s = stderr.decode('utf-8', 'replace').lower()
    if 'permission denied' in s or 'authentication failed' in s: return 'AUTHENTICATION'
    if 'host key verification failed' in s or 'identification has changed' in s: return 'HOST_KEY'
    if 'connection refused' in s or 'network is unreachable' in s: return 'NETWORK'
    if 'timed out' in s: return 'TIMEOUT'
    return 'UNCLASSIFIED'


def main(argv=None, runner=subprocess.run):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage', required=True)
    ap.add_argument('--review-only', action='store_true')
    ap.add_argument('--acknowledge-one-shot-kindle-event-test', action='store_true')
    ap.add_argument('--target', default='root@192.168.8.102')
    ap.add_argument('--port', type=int, default=2222)
    a = ap.parse_args(argv)
    report = base_report()
    if a.review_only == a.acknowledge_one_shot_kindle_event_test:
        if a.review_only: report['hold_category'] = 'MUTUALLY_EXCLUSIVE_MODES'
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    if not re.fullmatch(r'root@[A-Za-z0-9][A-Za-z0-9.\-]{0,252}', a.target) or not 1 <= a.port <= 65535:
        report['hold_category'] = 'TARGET_OR_PORT_INVALID'
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    try:
        if not source_pin_check():
            raise Refused('R83_RUNNER_SOURCE_PIN_MISMATCH')
        elf_objects, _review = r83.validate_stage(a.stage)
        module = read_pinned_event(a.stage)
        payload = make_archive(elf_objects, module)
        shell = remote_script(elf_objects, module)
        report['pinned_event_module_sha1_verified'] = True
        report['event_module_bytes'] = len(module)
        report['host_bundle_bytes'] = sum(map(len, elf_objects.values())) + len(module)
        report['host_bundle_sha256_verified'] = True
        report['offline_validation_passed'] = True
    except (Refused, r83.Hold, r83.r81.Refused, r83.r82.Refused, OSError,
            ValueError, KeyError, tarfile.TarError) as exc:
        report['hold_category'] = 'HOST_KOREADER_EVENT_PREFLIGHT_REFUSED'
        if isinstance(exc, Refused): report['offline_refusal_code'] = str(exc)
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    if a.review_only:
        report['hold_category'] = 'HOST_PINNED_EVENT_MODULE_PASS_DEVICE_REQUIRE_UNVERIFIED'
        print(json.dumps(report, sort_keys=True, separators=(',', ':')))
        return 2
    cmd = ['ssh', '-T', '-o', 'ConnectTimeout=15', '-o', 'ConnectionAttempts=1',
           '-p', str(a.port), a.target, 'sh -c ' + shlex.quote(shell)]
    report['kindle_access_performed'] = True
    report['device_execution_attempted'] = True
    try:
        result = runner(cmd, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        timeout=75, check=False)
    except (OSError, subprocess.TimeoutExpired):
        report['hold_category'] = 'SSH_OR_TIMEOUT_CLEANUP_UNVERIFIED'
    else:
        report['ssh_exit_code'] = result.returncode
        if result.returncode == 0 and result.stdout == MARKER:
            report.update(result='PASS_KOREADER_EVENT_LUA_MODULE_SINGLE_PROCESS',
                          hold_category='KO_READER_MODULE_DEPENDENCY_GRAPH_GUI_BOOT_RECOVERY_UNVERIFIED',
                          glibc_loader_resolution_verified=True,
                          lua_native_execution_verified=True,
                          koreader_real_module_require_verified=True,
                          tmpfs_cleanup_reported_complete=True)
        else:
            report['hold_category'] = r83.FAILURES.get(result.returncode, 'REMOTE_OUTPUT_OR_EXIT_UNEXPECTED')
            if result.returncode == 255:
                report['ssh_failure_category'] = ssh_category(result.stderr)
            report['tmpfs_cleanup_reported_complete'] = False
    print(json.dumps(report, sort_keys=True, separators=(',', ':')))
    return 0 if report['koreader_real_module_require_verified'] else 2

if __name__ == '__main__':
    sys.exit(main())
