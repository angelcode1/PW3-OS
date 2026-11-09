#!/usr/bin/env python3
"""R3877.87 guarded KOReader event -> EventListener -> Widget dispatch test.

Uses exact upstream KOReader v2026.07.2 Lua modules from the existing local
R13 stage, and the pinned previously tested R83 glibc loader + LuaJIT bundle.
No device/GUI access before explicit live opt-in; preserves NOT_BOOTABLE.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile

import pw3_r3877_83_glibc_luajit_smoke as r83
import pw3_r3877_86_event_module as r86

R86_SOURCE_SHA256 = '0c0d3bdface0d5d29739bddaece2769801efb011ec9d5a6f03e9747296271e8d'
MODULES = {
    'ui/event.lua': ('opt/koreader-compat/app/frontend/ui/event.lua', 858, '3e042eb2a017e2a4e6fd27a6e4c1c7d2e388bd14'),
    'ui/widget/eventlistener.lua': ('opt/koreader-compat/app/frontend/ui/widget/eventlistener.lua', 1104, '545e6424b55cebf8c36e4ae58c79da6ebb002a69'),
    'ui/widget/widget.lua': ('opt/koreader-compat/app/frontend/ui/widget/widget.lua', 2011, '8dd4082b1a7ee533997ebfa8f963fb08487c1acb'),
}
MARKER = b'R3877_87_KOREADER_WIDGET_DISPATCH_OK\n'
BASE_EXEC = '''  -e 'io.write("R3877_83_GLIBC_LUAJIT_OK\\n")' || exit 53'''
LUA_CODE = (
    'local home=assert(os.getenv("HOME")); '
    'package.path=home.."/?.lua";package.cpath=""; '
    'if not table.pack then table.pack=function(...) return {n=select("#",...),...} end end; '
    'local Event=assert(require("ui/event")); '
    'assert(package.loaded["ui/widget/eventlistener"]==nil); '
    'local Widget=assert(require("ui/widget/widget")); '
    'assert(type(package.loaded["ui/widget/eventlistener"])=="table"); '
    'local w=Widget:new{onPw3Smoke=function(self,n,s) '
    'assert(n==42 and s=="ok");self.seen=(self.seen or 0)+1;return true end}; '
    'local ev=Event:new("Pw3Smoke",42,"ok"); '
    'assert(w:handleEvent(ev)==true and w.seen==1); '
    'assert(w:handleEvent(Event:new("NoSuchHandler"))==nil); '
    'assert(package.loaded["ui/event"] and package.loaded["ui/widget/widget"]); '
    'io.write("R3877_87_KOREADER_WIDGET_DISPATCH_OK\\n")'
)

class Refused(ValueError):
    pass


def pinned_source_ok():
    try:
        src=Path(__file__).resolve().parent/'pw3_r3877_86_event_module.py'
        return hashlib.sha256(src.read_bytes()).hexdigest()==R86_SOURCE_SHA256 and r86.source_pin_check()
    except OSError:
        return False


def git_blob_sha1(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def read_stage_module(stage, relative, size, git_sha1):
    root=Path(stage).expanduser()
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise Refused('STAGE_ROOT_INVALID')
    path=root
    for part in Path(relative).parts[:-1]:
        path=path/part
        if path.is_symlink() or not path.is_dir():
            raise Refused('MODULE_PARENT_NOT_REGULAR_DIRECTORY')
    path=path/Path(relative).name
    if path.is_symlink() or not path.is_file():
        raise Refused('MODULE_MISSING_OR_SYMLINK')
    try:
        raw=r83.r81.raw_file(path)
    except (OSError,r83.r81.Refused) as e:
        raise Refused('STAGE_MODULE_READ_REFUSED') from e
    if len(raw)!=size:
        raise Refused('STAGED_MODULE_BYTE_COUNT_MISMATCH')
    if git_blob_sha1(raw)!=git_sha1:
        raise Refused('STAGED_MODULE_UPSTREAM_GIT_BLOB_MISMATCH')
    return raw


def load_modules(stage):
    if not pinned_source_ok():
        raise Refused('PREVIOUS_R86_SOURCE_CHANGED')
    return {key:read_stage_module(stage,*value) for key,value in MODULES.items()}


def tar_bundle(objects, modules):
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w',format=tarfile.USTAR_FORMAT) as tf:
        for dirname in ('ui/','ui/widget/'):
            info=tarfile.TarInfo(dirname);info.type=tarfile.DIRTYPE
            info.mode=0o700;info.uid=info.gid=0;info.mtime=0
            tf.addfile(info)
        for name in ('luajit',)+r83.NAMES:
            content=objects[name];info=tarfile.TarInfo(name)
            info.mode=0o500;info.uid=info.gid=0;info.mtime=0
            info.size=len(content);tf.addfile(info,io.BytesIO(content))
        for name in MODULES:
            content=modules[name];info=tarfile.TarInfo(name)
            info.mode=0o400;info.uid=info.gid=0;info.mtime=0
            info.size=len(content);tf.addfile(info,io.BytesIO(content))
    return buffer.getvalue()


def remote_script(objects, modules):
    if not pinned_source_ok():
        raise Refused('PREVIOUS_R86_SOURCE_CHANGED')
    sh=r83.remote_shell(objects)
    fixed={
        'work="$place/pw3-r3877-83-$$"': 'work="$place/pw3-r3877-87-$$"',
        '  rmdir "$work"\n}': (
            '  if [ -d "$work/ui/widget" ]; then rmdir "$work/ui/widget" || return 1; fi\n'
            '  if [ -d "$work/ui" ]; then rmdir "$work/ui" || return 1; fi\n'
            '  rmdir "$work"\n}'),
        'chmod 500 "$work/luajit" "$work/ld-linux.so.3" || exit 49': (
            'MODULE_CHECKS\n'
            'chmod 500 "$work/luajit" "$work/ld-linux.so.3" || exit 49'),
        BASE_EXEC: '  -e '+shlex.quote(LUA_CODE)+' || exit 53',
        'for f in luajit ld-linux.so.3 libc.so.6 libdl.so.2 libgcc_s.so.1 libm.so.6; do rm -f "$work/$f"; done': (
            'for f in luajit ld-linux.so.3 libc.so.6 libdl.so.2 libgcc_s.so.1 libm.so.6; do rm -f "$work/$f"; done\n'
            '  for f in ui/event.lua ui/widget/eventlistener.lua ui/widget/widget.lua; do rm -f "$work/$f"; done'),
    }
    for old,new in fixed.items():
        if sh.count(old)!=1:
            raise Refused('PREVIOUS_R83_REMOTE_TEMPLATE_CHANGED')
        sh=sh.replace(old,new,1)
    checks='\n'.join('check_one '+shlex.quote(name)+' '+str(len(data))+' '+hashlib.sha256(data).hexdigest()+' || exit 48'
                     for name,data in modules.items())
    if sh.count('MODULE_CHECKS')!=1:raise Refused('MODULE_VERIFICATION_GATE_MISSING')
    sh=sh.replace('MODULE_CHECKS',checks,1)
    if 'pw3-r3877-83-$$' in sh or 'R3877_83_GLIBC_LUAJIT_OK' in sh:
        raise Refused('OLD_EXECUTION_MARKER_REMAINS')
    if sh.count('check_one ui/')!=3 or sh.count('--inhibit-rpath')!=2 or '--list "$work/luajit"' not in sh:
        raise Refused('LOADER_OR_MODULE_CHECK_MISSING')
    return sh


def report_base():
    result=r83.report_base()
    result.update(milestone='R3877.87',result='HOLD',immutable_hold='NOT_BOOTABLE',
                  hold_category='EXPLICIT_OPT_IN_REQUIRED',
                  offline_validation_passed=False,upstream_modules_exactly_pinned=False,
                  genuine_widget_dependency_require_verified=False,
                  synthetic_event_dispatch_verified=False,complete_koreader_runtime_verified=False)
    return result


def ssh_category(raw):
    val=raw.decode('utf-8','replace').lower()
    if 'permission denied' in val:return 'AUTHENTICATION'
    if 'host key verification failed' in val or 'identification has changed' in val:return 'HOST_KEY'
    if 'connection refused' in val or 'network is unreachable' in val:return 'NETWORK'
    if 'timed out' in val:return 'TIMEOUT'
    return 'UNCLASSIFIED'


def main(argv=None,runner=subprocess.run):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',required=True)
    ap.add_argument('--review-only',action='store_true')
    ap.add_argument('--acknowledge-one-shot-kindle-widget-dispatch',action='store_true')
    ap.add_argument('--target',default='root@192.168.8.102')
    ap.add_argument('--port',type=int,default=2222)
    a=ap.parse_args(argv)
    report=report_base()
    if a.review_only==a.acknowledge_one_shot_kindle_widget_dispatch:
        if a.review_only:report['hold_category']='MUTUALLY_EXCLUSIVE_MODES'
        print(json.dumps(report,sort_keys=True,separators=(',',':')));return 2
    if not re.fullmatch(r'root@[A-Za-z0-9][A-Za-z0-9.\-]{0,252}',a.target) or not 1<=a.port<=65535:
        report['hold_category']='TARGET_OR_PORT_INVALID'
        print(json.dumps(report,sort_keys=True,separators=(',',':')));return 2
    try:
        objects,review=r83.validate_stage(a.stage)
        modules=load_modules(a.stage)
        payload=tar_bundle(objects,modules)
        sh=remote_script(objects,modules)
        report['upstream_modules_exactly_pinned']=True
        report['host_bundle_sha256_verified']=True
        report['offline_validation_passed']=True
        report['host_bundle_bytes']=sum(map(len,objects.values()))+sum(map(len,modules.values()))
        report['module_files']=len(modules)
        report['module_bytes']=sum(map(len,modules.values()))
        report['rpath_entries_reviewed_but_inhibited']=len(review['objects']['luajit']['rpath_resolution_categories'])
    except (Refused,r83.Hold,r83.r81.Refused,r83.r82.Refused,OSError,ValueError,KeyError,tarfile.TarError) as exc:
        report['hold_category']='HOST_STAGE_OR_MODULE_PREFLIGHT_REFUSED'
        if isinstance(exc,Refused):report['offline_refusal_code']=str(exc)
        print(json.dumps(report,sort_keys=True,separators=(',',':')));return 2
    if a.review_only:
        report['hold_category']='HOST_WIDGET_DISPATCH_READY_DEVICE_UNVERIFIED'
        print(json.dumps(report,sort_keys=True,separators=(',',':')));return 2
    command=['ssh','-T','-o','ConnectTimeout=15','-o','ConnectionAttempts=1',
             '-p',str(a.port),a.target,'sh -c '+shlex.quote(sh)]
    report['kindle_access_performed']=True
    report['device_execution_attempted']=True
    try:
        result=runner(command,input=payload,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=75,check=False)
    except (OSError,subprocess.TimeoutExpired):
        report['hold_category']='SSH_OR_TIMEOUT_CLEANUP_UNVERIFIED'
    else:
        report['ssh_exit_code']=result.returncode
        if result.returncode==0 and result.stdout==MARKER:
            report.update(result='PASS_KOREADER_WIDGET_EVENT_DISPATCH_SINGLE_PROCESS',
                          hold_category='KOREADER_GUI_DEVICE_AND_RECOVERY_UNVERIFIED',
                          glibc_loader_resolution_verified=True,
                          lua_native_execution_verified=True,
                          genuine_widget_dependency_require_verified=True,
                          synthetic_event_dispatch_verified=True,
                          tmpfs_cleanup_reported_complete=True)
        else:
            report['hold_category']=r83.FAILURES.get(result.returncode,'REMOTE_OUTPUT_OR_EXIT_UNEXPECTED')
            if result.returncode==255:report['ssh_failure_category']=ssh_category(result.stderr)
            report['tmpfs_cleanup_reported_complete']=False
    print(json.dumps(report,sort_keys=True,separators=(',',':')))
    return 0 if report['synthetic_event_dispatch_verified'] else 2

if __name__=='__main__':sys.exit(main())
