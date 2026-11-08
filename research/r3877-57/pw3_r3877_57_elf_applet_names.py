#!/usr/bin/env python3
"""R3877.57: compare a package-generated applet list to a pinned BusyBox ELF
NUL-separated name array in FILE-BACKED PT_LOAD segments. Host-only and fail-closed.

This cannot verify the callable applet dispatch, actual execution, kernel
compatibility, entropy fallbacks, source-to-binary reproducibility or recovery.
No Kindle access or ARM executable launched. NOT_BOOTABLE immutable.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import uuid

import pw3_r3877_56_busybox_package_inventory as r56

BASE = r56.base
MILESTONE='R3877.57'
PASS='PASS_PINNED_BUSYBOX_ELF_APPLET_NAME_ARRAY_MATCH_ONLY'
R56_SHA256='30940a63087905f277b7a4dde535914b933c1054e0c7ab363dd1e7725a08ad7e'
GENERATOR_GIT_BLOB_SHA1='66ef7e4ac349d0006015d1b39c8021b6e5a3ce86'
GENERATOR_TAG='vda-linux/busybox_mirror:1_37_0'
APPLET_EXPECTED_SHA256='ad43f2888aa6679930812faef33672c45e98021d3be0d0ed08d257c1d957a968'
EXPECTED_COUNT=304
MAX_ELF=24*1024*1024

class AuditHold(Exception): pass

def require_helpers():
    p=Path(r56.__file__)
    if p.is_symlink() or not p.is_file() or BASE.digest(p)!=R56_SHA256:
        raise AuditHold('PINNED_R56_HELPER_CHANGED')
    try:r56.require_r54_code()
    except r56.AuditHold as e:raise AuditHold('PINNED_R54_OR_R48_HELPER_CHANGED') from e

def canonical_names(list_data):
    try:
        v=r56.parse_applet_list(list_data)  # validates paths and disabled seedrng
    except r56.AuditHold as e:
        raise AuditHold('PINNED_APPLET_LIST_INVALID:'+str(e)) from e
    if v['sha256']!=APPLET_EXPECTED_SHA256 or v['unique_applet_basenames_count']!=EXPECTED_COUNT or v['listed_paths_count']!=EXPECTED_COUNT:
        raise AuditHold('PACKAGE_GENERATED_LIST_NOT_THE_REPORTED_R56_BYTES')
    names=sorted({line.rsplit(b'/',1)[-1] for line in list_data.splitlines()})
    if len(names)!=EXPECTED_COUNT or b'ash' not in names or b'seedrng' in names:
        raise AuditHold('APPLET_NAME_SET_INCONSISTENT')
    # BusyBox 1.37.0 generator prints: const char applet_names[]="" "name" "\\0"...
    # C string concatenation also adds an implicit trailing NUL byte.
    pattern=b''.join(name+b'\0' for name in names)+b'\0'
    return names,pattern

def elf_load_segments(data):
    if not 52<=len(data)<=MAX_ELF or data[:7]!=b'\x7fELF\x01\x01\x01':
        raise AuditHold('ELF32_LE_ARM_HEADER_INVALID')
    etype,machine,version=struct.unpack_from('<HHI',data,16)
    eflags=struct.unpack_from('<I',data,36)[0]
    if etype not in (2,3) or machine!=40 or version!=1 or eflags!=0x05000400:
        raise AuditHold('ELF_ARM_EABI_HARDFLOAT_IDENTITY_INVALID')
    phoff=struct.unpack_from('<I',data,28)[0]
    phentsize,phnum=struct.unpack_from('<HH',data,42)
    if phentsize!=32 or not 1<=phnum<=128 or phoff<52 or phoff+phentsize*phnum>len(data):
        raise AuditHold('ELF_PROGRAM_HEADERS_INVALID')
    loads=[]
    for i in range(phnum):
        p_type,p_off,_,_,p_filesz,p_memsz,_,_=struct.unpack_from('<IIIIIIII',data,phoff+i*32)
        if p_type!=1:continue
        if p_filesz==0 or p_filesz>p_memsz or p_off>len(data) or p_filesz>len(data)-p_off:
            raise AuditHold('ELF_PT_LOAD_OUT_OF_BOUNDS')
        loads.append(data[p_off:p_off+p_filesz])
    if not loads:raise AuditHold('ELF_FILE_BACKED_PT_LOAD_ABSENT')
    return loads

def applet_name_array_evidence(elf_bytes,list_data):
    names,pattern=canonical_names(list_data)
    total=0
    for load in elf_load_segments(elf_bytes):
        # Allow duplicate search at each subsequent position, but don't trust bytes
        # in ELF overlays, non-PT_LOAD data or section headers.
        at=0
        while True:
            ix=load.find(pattern,at)
            if ix<0:break
            total+=1
            if total>1:raise AuditHold('APPLET_NAMES_ARRAY_NOT_UNIQUE')
            at=ix+1
    if total!=1:raise AuditHold('EXACT_APPLET_NAMES_ARRAY_NOT_FOUND_IN_FILE_BACKED_PT_LOAD')
    return {'exact_sorted_nul_separated_applet_name_array_in_elf_pt_load':True,
        'matched_name_count':len(names),
        'applet_names_array_byte_length':len(pattern),
        'applet_names_array_sha256':hashlib.sha256(pattern).hexdigest(),
        'package_generated_list_sha256':APPLET_EXPECTED_SHA256,
        'ash_name_present_in_matched_array':True,
        'seedrng_name_absent_from_matched_array':True,
        'source_generator_git_blob_sha1':GENERATOR_GIT_BLOB_SHA1,
        'source_generator_revision':GENERATOR_TAG,
        'actual_function_pointer_dispatch_table_verified':False,
        'applet_execution_verified':False,
        'binary_reproducibility_verified':False,
        'application_entropy_fallback_verified':False,
        'binary_string_array_is_not_runtime_evidence':True}

def preflight():
    return {'milestone':MILESTONE,'result':'HOLD','hold_category':'INPUTS_OR_AUTHORIZATION_REQUIRED',
      'immutable_hold':'NOT_BOOTABLE','docker_used':False,'docker_stopped_container_only':False,
      'arm_executable_launched':False,'physical_device_access_performed':False,
      'kindle_ssh_sessions':0,'boot_performed':False,'firmware_write_performed':False,
      'actual_vendor_syscall_dispatch_verified':False,'recovery_verified':False,
      'application_entropy_fallback_verified':False,'target_musl_linux_3_0_35_compatibility_verified':False}

def analyze(installed,listing,busybox,loader):
    require_helpers()
    existing=r56.analyze(installed,listing,busybox,loader)  # reverify ALL original pins
    raw=r56.bounded(busybox,MAX_ELF)
    alist=r56.bounded(listing,r56.MAX_LIST)
    table=applet_name_array_evidence(raw,alist)
    return {'prior_pinned_package_and_binary_revalidation':existing,
            'compiled_file_backed_applet_name_array':table,
            'compiled_applets_callable_verified':False,
            'legacy_kernel_compatibility_verified':False}

def run_local(installed,listing,busybox,loader):
    r=preflight()
    try:
        r['audit']=analyze(installed,listing,busybox,loader)
        r.update(result=PASS,hold_category='NOT_BOOTABLE')
    except (AuditHold,r56.AuditHold,r56.r54.AuditHold,BASE.Hold,OSError,ValueError,TypeError,KeyError) as e:
        r['hold_category']=str(e).splitlines()[0][:160]
    return r

def run_stopped():
    r=preflight()
    r.update(docker_used=True,docker_stopped_container_only=True,
      original_image_unchanged=False,stopped_container_removed=False)
    cid=None;parent_seen=False
    try:
        require_helpers()
        BASE.inspect_image();parent_seen=True
        with tempfile.TemporaryDirectory(prefix='pw3-r57-') as folder:
            cp=BASE.docker(['create','--platform','linux/arm/v7','--pull','never',
              '--network','none','--read-only','--cap-drop','ALL',
              '--security-opt','no-new-privileges','--pids-limit','32',
              '--name','pw3-r57-static-'+uuid.uuid4().hex[:12],
              '--entrypoint','/bin/true',BASE.PARENT])
            cid=cp.stdout.strip()
            if not BASE.CID_RE.fullmatch(cid):raise AuditHold('STOPPED_CONTAINER_ID_INVALID')
            r56.check_stopped_isolation(cid)
            files={'installed':('/lib/apk/db/installed',False),
              'listing':(r56.APPLET_PATH,False),
              'busybox':('/bin/busybox',True),
              'loader':(BASE.INTERP,True)}
            dest={}
            for name,(source,follow) in files.items():
                dest[name]=str(Path(folder)/name)
                BASE.docker(['cp']+(['-L'] if follow else [])+[cid+':'+source,dest[name]])
                r56.check_stopped_isolation(cid)
            r['audit']=analyze(**dest)
            r.update(result=PASS,hold_category='NOT_BOOTABLE')
    except (AuditHold,r56.AuditHold,r56.r54.AuditHold,BASE.Hold,OSError,ValueError,TypeError,KeyError) as e:
        r['hold_category']=str(e).splitlines()[0][:160]
    finally:
        if cid:
            try:
                rm=BASE.docker(['rm','-f',cid],allow_nonzero=True)
                ch=BASE.docker(['container','inspect',cid],allow_nonzero=True)
                r['stopped_container_removed']=(rm.returncode==0 and ch.returncode!=0 and
                    bool(re.search('No such (?:container|object)',ch.stderr,re.I)))
            except BASE.Hold:r['stopped_container_removed']=False
        if parent_seen:
            try:BASE.inspect_image();r['original_image_unchanged']=True
            except BASE.Hold:r['original_image_unchanged']=False
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
        if any(f):ap.error('Docker mode cannot mix local files')
        result=run_stopped()
    elif all(f):result=run_local(*f)
    else:result=preflight()
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
    return 0 if result['result']==PASS else 2

if __name__=='__main__':sys.exit(main())
