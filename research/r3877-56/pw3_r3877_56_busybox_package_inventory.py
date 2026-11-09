#!/usr/bin/env python3
"""R3877.56: fail-closed, stopped-only BusyBox APK and applet-list metadata audit.

Research/education only. Default has no Docker, SSH, or ARM code execution.
Authorised mode requires an immutable pinned ARMv7 cached Alpine image,
creates a STOPPED disposable container with no networking/host mounts,
copies only four allowlisted files, then removes and verifies the container.
No Kindle access or firmware writes. Immutable NOT_BOOTABLE.

This audit verifies package metadata and an APK-generated applet-list *file*;
it is not a byte-level BusyBox build reproduction, execution, or full applet
inventory proof. Absent list or inconsistent data means HOLD.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import uuid

import pw3_r3877_48_musl_interp_audit as base
import pw3_r3877_54_busybox_entropy_elf_audit as r54

MILESTONE = 'R3877.56'
PASS = 'PASS_PINNED_BUSYBOX_APK_METADATA_AND_PACKAGE_GENERATED_APPLET_LIST_ONLY'
EXPECTED_R54_SOURCE_SHA256 = '848f8994fa7a8ca9effd392435dc4573f376e9749068509fe1bcaaf6a14d198d'
EXPECTED_BUSYBOX_VERSION = '1.37.0-r31'
EXPECTED_ARCH = 'armv7'
APPLET_PATH = '/etc/busybox-paths.d/busybox'
MAX_INSTALLED = 4 * 1024 * 1024
MAX_LIST = 128 * 1024

class AuditHold(Exception):
    pass


def bounded(path, max_size):
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        raise AuditHold('INPUT_FILE_MISSING_OR_SYMLINK')
    size = p.stat().st_size
    if not 1 <= size <= max_size:
        raise AuditHold('INPUT_FILE_SIZE_OUT_OF_BOUNDS')
    data = p.read_bytes()
    if len(data) != size:
        raise AuditHold('INPUT_FILE_SIZE_CHANGED')
    return data


def require_r54_code():
    code = Path(r54.__file__)
    if code.is_symlink() or not code.is_file() or base.digest(code) != EXPECTED_R54_SOURCE_SHA256:
        raise AuditHold('PINNED_R54_AUDITOR_CHANGED')
    try:
        r54.require_baseline_code()
    except r54.AuditHold as e:
        raise AuditHold('PINNED_R48_HELPER_CHANGED') from e


def parse_apk_db(data):
    if len(data) > MAX_INSTALLED or b'\x00' in data:
        raise AuditHold('APK_DB_INVALID_SIZE_OR_NUL')
    try:
        content = data.decode('utf-8')
    except UnicodeDecodeError as e:
        raise AuditHold('APK_DB_NOT_UTF8') from e
    found=[]
    for record in re.split(r'\r?\n\r?\n', content.strip()):
        fields={}
        for line in record.splitlines():
            if len(line) >= 2 and line[1] == ':' and line[0] in 'PVA':
                if line[0] in fields:
                    raise AuditHold('APK_DB_DUPLICATE_RECORD_FIELD')
                fields[line[0]] = line[2:]
        if fields.get('P') == 'busybox':
            found.append(fields)
    if len(found) != 1:
        raise AuditHold('APK_DB_BUSYBOX_RECORD_MISSING_OR_DUPLICATED')
    record=found[0]
    if record.get('V') != EXPECTED_BUSYBOX_VERSION:
        raise AuditHold('BUSYBOX_INSTALLED_VERSION_DIFFERS_FROM_PINNED_RECIPE')
    if record.get('A') != EXPECTED_ARCH:
        raise AuditHold('BUSYBOX_INSTALLED_ARCH_UNEXPECTED')
    return {'installed_package_name':'busybox',
            'installed_package_version':record['V'],
            'installed_package_arch':record['A'],
            'matches_pinned_recipe_version':True}


def parse_applet_list(data):
    if len(data) > MAX_LIST or b'\x00' in data:
        raise AuditHold('APPLET_LIST_INVALID_SIZE_OR_NUL')
    try:
        text=data.decode('ascii')
    except UnicodeDecodeError as e:
        raise AuditHold('APPLET_LIST_NOT_ASCII') from e
    applets=set()
    paths=set()
    for line in text.splitlines():
        if not line or line != line.strip() or '\\' in line or '\x00' in line:
            raise AuditHold('APPLET_LIST_INVALID_LINE')
        # busybox --list-path may produce absolute or relative standard paths.
        path=line[1:] if line.startswith('/') else line
        if (not re.fullmatch(r'(?:usr/)?(?:s?bin)/[A-Za-z0-9_.+\[\]-]+', path)
            or '..' in path or path in paths):
            raise AuditHold('APPLET_LIST_INVALID_OR_DUPLICATE_PATH')
        paths.add(path)
        applets.add(path.rsplit('/', 1)[-1])
    if not 1 <= len(paths) <= 1000:
        raise AuditHold('APPLET_LIST_ENTRY_COUNT_UNEXPECTED')
    if 'ash' not in applets:
        raise AuditHold('APPLET_LIST_ASH_MISSING')
    if 'seedrng' in applets:
        raise AuditHold('APPLET_LIST_SEEDRNG_CONFLICTS_WITH_PINNED_RECIPE')
    return {
        'source':'PACKAGE_GENERATED_ETC_BUSYBOX_PATHS_D_BUSYBOX',
        'sha256':hashlib.sha256(data).hexdigest(),
        'listed_paths_count':len(paths),
        'unique_applet_basenames_count':len(applets),
        'ash_listed':True,'seedrng_listed':False,
        'list_is_not_actual_binary_applet_execution':True,
        'absence_does_not_prove_all_binary_code_paths':True,
    }


def analyze(installed, listing, busybox, loader):
    require_r54_code()
    # Revalidate exact parent-image ELF pins; never trust only package metadata.
    link=r54.inspect_binary_pair(busybox,loader)
    pkg=parse_apk_db(bounded(installed,MAX_INSTALLED))
    applets=parse_applet_list(bounded(listing,MAX_LIST))
    return {
       'installed_package':pkg,
       'package_generated_applet_list':applets,
       'binary_revalidated':{
          'busybox_sha256':link['linkage']['busybox_sha256'],
          'loader_sha256':link['linkage']['loader_sha256'],
          'musl_interp_matches_pinned_loader':link['linkage']['interpreter_path_matches_pinned_loader'],
          'direct_getrandom_dynamic_import_present':link['direct_getrandom_dynamic_import_present'],
          'direct_getentropy_dynamic_import_present':link['direct_getentropy_dynamic_import_present'],
          'generic_syscall_import_present':link['interesting_undefined_imports']['syscall'],
          'urandom_marker_present':link['embedded_byte_marker_present']['/dev/urandom'],
       },
       'installed_recipe_binary_reproducibility_verified':False,
       'actual_compiled_applet_table_verified':False,
       'runtime_entropy_fallback_verified':False,
       'vendor_kernel_syscalls_verified':False,
    }


def preflight():
    return dict(milestone=MILESTONE,result='HOLD',hold_category='INPUTS_OR_AUTHORIZATION_REQUIRED',
        immutable_hold='NOT_BOOTABLE',docker_used=False,arm_executable_launched=False,
        physical_device_access_performed=False,kindle_ssh_sessions=0,boot_performed=False,
        firmware_write_performed=False,recovery_verified=False,
        installed_recipe_binary_reproducibility_verified=False,
        application_entropy_fallback_verified=False,
        target_musl_linux_3_0_35_compatibility_verified=False)


def run_local(installed,listing,busybox,loader):
    r=preflight()
    try:
        r['audit']=analyze(installed,listing,busybox,loader)
        r.update(result=PASS,hold_category='NOT_BOOTABLE')
    except (AuditHold,r54.AuditHold,base.Hold,OSError,ValueError,TypeError,KeyError) as e:
        r['hold_category']=str(e).splitlines()[0][:180]
    return r


def check_stopped_isolation(cid):
    base.inspect_stopped(cid)
    try:
        info=json.loads(base.docker(['container','inspect',cid]).stdout)
        if len(info)!=1: raise ValueError()
        cfg=info[0]['HostConfig']
        if (cfg.get('ReadonlyRootfs') is not True
            or not isinstance(cfg.get('CapDrop'),list) or 'ALL' not in cfg['CapDrop']
            or not isinstance(cfg.get('SecurityOpt'),list)
            or not any(x.startswith('no-new-privileges') for x in cfg['SecurityOpt'])
            or cfg.get('PidsLimit')!=32):
            raise ValueError()
    except (ValueError,KeyError,TypeError) as e:
        raise AuditHold('STOPPED_CONTAINER_HARDENING_UNVERIFIED') from e


def run_stopped():
    r=preflight()
    r.update(docker_used=True,docker_stopped_container_only=True,
             original_image_unchanged=False,stopped_container_removed=False)
    cid=None; parent_seen=False
    try:
        require_r54_code()
        base.inspect_image();parent_seen=True
        with tempfile.TemporaryDirectory(prefix='pw3-r56-') as folder:
            cp=base.docker(['create','--platform','linux/arm/v7','--pull','never',
               '--network','none','--read-only','--cap-drop','ALL',
               '--security-opt','no-new-privileges','--pids-limit','32',
               '--name','pw3-r56-static-'+uuid.uuid4().hex[:12],
               '--entrypoint','/bin/true',base.PARENT])
            cid=cp.stdout.strip()
            if not base.CID_RE.fullmatch(cid):
                raise AuditHold('STOPPED_CONTAINER_ID_INVALID')
            check_stopped_isolation(cid)
            files={
                'installed':('/lib/apk/db/installed',False),
                'listing':(APPLET_PATH,False),
                'busybox':('/bin/busybox',True),
                'loader':(base.INTERP,True),
            }
            dest={}
            for name,(source,follow) in files.items():
                dest[name]=str(Path(folder)/name)
                argv=['cp'] + (['-L'] if follow else []) + [cid+':'+source,dest[name]]
                base.docker(argv)
                check_stopped_isolation(cid)
            r['audit']=analyze(**dest)
            r.update(result=PASS,hold_category='NOT_BOOTABLE')
    except (AuditHold,base.Hold,r54.AuditHold,OSError,ValueError,TypeError,KeyError) as e:
        r['hold_category']=str(e).splitlines()[0][:180]
    finally:
        if cid:
            try:
                rm=base.docker(['rm','-f',cid],allow_nonzero=True)
                ch=base.docker(['container','inspect',cid],allow_nonzero=True)
                r['stopped_container_removed']=(rm.returncode==0 and ch.returncode!=0 and
                  bool(re.search('No such (?:container|object)',ch.stderr,re.I)))
            except base.Hold:r['stopped_container_removed']=False
        if parent_seen:
            try:base.inspect_image();r['original_image_unchanged']=True
            except base.Hold:r['original_image_unchanged']=False
        if r['result']==PASS and (not r['stopped_container_removed'] or not r['original_image_unchanged']):
            r.update(result='HOLD',hold_category='CONTAINER_CLEANUP_OR_PARENT_UNVERIFIED')
    return r


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--authorize-stopped-image-audit',action='store_true')
    ap.add_argument('--installed-db')
    ap.add_argument('--applet-list')
    ap.add_argument('--busybox')
    ap.add_argument('--loader')
    a=ap.parse_args(argv)
    f=(a.installed_db,a.applet_list,a.busybox,a.loader)
    if a.authorize_stopped_image_audit:
        if any(f):ap.error('Docker mode does not accept local file paths')
        r=run_stopped()
    elif all(f):r=run_local(*f)
    else:r=preflight()
    print(json.dumps(r,sort_keys=True,separators=(',',':')))
    return 0 if r['result']==PASS else 2

if __name__=='__main__':sys.exit(main())
