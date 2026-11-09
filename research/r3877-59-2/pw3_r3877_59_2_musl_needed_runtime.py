#!/usr/bin/env python3
"""R3877.59.2: repair one missing DT_NEEDED on a pinned Mac-only ARM ELF.

Strictly host/Colima QEMU research. The unchanged R49/R59/R59.1 runners
provide guest isolation, read-only copy gate, exact parent pins, cleanup and
bounded failure output. Only the copied disposable ARM ELF differs; it has an
explicit DT_NEEDED libc.so. No target Kindle access. NOT_BOOTABLE immutable.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import struct
import sys
from unittest.mock import patch

import pw3_r3877_59_qemu_pthread_tls as r59
import pw3_r3877_59_1_failure_diagnostic as r591

MILESTONE = 'R3877.59.2'
PASS = 'PASS_PINNED_QEMU_ARMV7_MUSL_PTHREAD_TLS_WITH_LIBC_NEEDED_ONLY'
NEW_PROBE = Path(__file__).resolve().parent / 'pw3_r3877_59_2_armv7_probe.elf'
NEW_SHA = 'b0b89626cd48482e99ea8515b4c808c378e1ff65b4ea4de05b16a4c373df18f4'
ORIGINAL_SHA = '5ce343387f982330965aa1d101daf15d1d53fd38de329d8e7c14a30d6cd37085'
R59_SCRIPT_SHA = 'c6151873a881f68fa13dd88910cfe712780d2db139c2e94596fca4381602d234'
R591_SCRIPT_SHA = '726f82b8e9c6fbcb4567d45aea22ba44853d4924c09868fdb106c0a727f510fa'
EXPECTED_GUEST_PATH = '/usr/bin/pw3-r3877-59-armv7-probe'
EXPECTED_LOADER = b'/lib/ld-musl-armhf.so.1\0'
KNOWN_RELOCATION_SYMBOLS = (
 '__aeabi_read_tp', 'pthread_create', 'puts', 'pthread_join',
 'getrandom', 'getentropy', '__errno_location', '__libc_start_main', 'exit'
)
OBSERVED_ERROR_SHA = 'c5a0eb0c4ac06bc5154e324411a4df0dbce3fd56402ec3b023367633d2971332'
OBSERVED_ERROR_BYTES = 740

class Hold(Exception): pass


def file_sha(path):
    p = Path(path)
    if p.is_symlink() or not p.is_file() or not 1 <= p.stat().st_size <= 256000:
        raise Hold('LOCAL_FILE_MISSING_SYMLINK_OR_OVERSIZE')
    return hashlib.sha256(p.read_bytes()).hexdigest()


def reconstructed_relocation_error():
    # Reconstruct *only* the error format of our own known disposable probe.
    # Never capture or publish arbitrary guest output.
    return ''.join('Error relocating '+EXPECTED_GUEST_PATH+': '+s+': symbol not found\n'
                   for s in KNOWN_RELOCATION_SYMBOLS).encode('utf-8')


def check_prior_error_fingerprint():
    b = reconstructed_relocation_error()
    if len(b) != OBSERVED_ERROR_BYTES or hashlib.sha256(b).hexdigest() != OBSERVED_ERROR_SHA:
        raise Hold('PRIOR_KNOWN_RELOCATION_ERROR_FINGERPRINT_CHANGED')
    return {'matched_prior_output_sha256':OBSERVED_ERROR_SHA,
            'matched_prior_output_bytes':OBSERVED_ERROR_BYTES,
            'unresolved_symbol_count':len(KNOWN_RELOCATION_SYMBOLS),
            'classification':'EXACT_KNOWN_MUSL_RELOCATION_ERROR_FINGERPRINT',
            'raw_guest_output_published':False}


def validate_elf_dependency(path):
    b=Path(path).read_bytes()
    if file_sha(path) != NEW_SHA: raise Hold('NEW_ELF_SHA256_MISMATCH')
    if len(b)<52 or b[:7]!=b'\x7fELF\x01\x01\x01':
        raise Hold('ELF32_HEADER_INVALID')
    typ,machine,version=struct.unpack_from('<HHI',b,16)
    flags=struct.unpack_from('<I',b,36)[0]
    phoff=struct.unpack_from('<I',b,28)[0]
    phstride,phnum=struct.unpack_from('<HH',b,42)
    if (typ,machine,version,flags)!=(3,40,1,0x05000400):
        raise Hold('ELF_ARMV7_EABI_HARDFLOAT_MISMATCH')
    if phnum<4 or phnum>32 or phstride!=32 or phoff<52 or phoff+phstride*phnum>len(b):
        raise Hold('ELF_PROGRAM_HEADERS_INVALID')
    loads=[]; interps=[]; dyn=[]; tls=0
    for i in range(phnum):
        off=phoff+i*phstride
        kind,fileoff,vaddr,_,filesz,memsz=struct.unpack_from('<IIIIII',b,off)
        if fileoff+filesz>len(b):raise Hold('ELF_SEGMENT_OUT_OF_FILE')
        if kind==1: loads.append((fileoff,vaddr,filesz,memsz))
        if kind==3:interps.append(b[fileoff:fileoff+filesz])
        if kind==7:tls+=1
        if kind==2:dyn.append((fileoff,filesz))
    if interps != [EXPECTED_LOADER] or tls != 1 or len(dyn)!=1 or not loads:
        raise Hold('ELF_LOADER_TLS_OR_DYNAMIC_INVALID')
    doff,dsize=dyn[0]
    if dsize%8 or dsize>2048 or dsize<40:raise Hold('ELF_DYNAMIC_SIZE_INVALID')
    tags=[]
    for j in range(doff,doff+dsize,8):
        tag,val=struct.unpack_from('<II',b,j)
        tags.append((tag,val))
        if tag==0:break
    if not tags or tags[-1][0]!=0:raise Hold('ELF_DYNAMIC_NOT_TERMINATED')
    if [x for x,_ in tags].count(1)!=1 or any(x in (15,29) for x,_ in tags):
        raise Hold('ELF_NEEDED_COUNT_OR_SEARCH_PATH_INVALID')
    def tag_one(t):
        vals=[v for k,v in tags if k==t]
        if len(vals)!=1:raise Hold('ELF_DYNAMIC_TAG_MISSING_OR_DUPLICATE')
        return vals[0]
    strva=tag_one(5);strsz=tag_one(10)
    if not 0<strsz<=4096:raise Hold('ELF_STRTAB_SIZE_INVALID')
    maps=[f+(strva-v) for f,v,fs,ms in loads if v<=strva and strva+strsz<=v+fs]
    if len(maps)!=1:raise Hold('ELF_STRTAB_NOT_IN_UNIQUE_LOAD')
    needed_offset=tag_one(1)
    start=maps[0]+needed_offset
    if not 0<=needed_offset<strsz:raise Hold('ELF_NEEDED_STRING_OUT_OF_BOUNDS')
    end=b.find(b'\0',start,maps[0]+strsz)
    if end<0 or b[start:end]!=b'libc.so':
        raise Hold('ELF_NEEDED_NOT_MUSL_LIBC')
    if file_sha(r59.__file__)!=R59_SCRIPT_SHA or file_sha(r591.__file__)!=R591_SCRIPT_SHA:
        raise Hold('PINNED_R59_OR_R591_RUNNER_CHANGED')
    if r59.GUEST_PROBE != EXPECTED_GUEST_PATH or file_sha(r59.PROBE)!=ORIGINAL_SHA:
        raise Hold('ORIGINAL_R59_PROBE_BYTES_OR_PATH_CHANGED')
    r59.require_pinned()
    return {'elf_sha256':NEW_SHA,'original_probe_sha256':ORIGINAL_SHA,
        'elf_armv7_hard_float_verified':True,
        'pt_interp':'/lib/ld-musl-armhf.so.1','pt_tls_present':True,
        'dt_needed':['libc.so'], 'rpath_or_runpath_absent':True,
        'link_time_placeholder_not_shipped_to_guest':True}


def preflight():
    return dict(milestone=MILESTONE,result='HOLD',hold_category='QEMU_OPT_IN_REQUIRED',
      immutable_hold='NOT_BOOTABLE',docker_used=False,arm_guest_execution_performed=False,
      original_r59_elf_unchanged=True,kindle_ssh_sessions=0,
      physical_device_access_performed=False,boot_performed=False,
      firmware_write_performed=False,host_binfmt_registration_changed=False,
      guest_network_enabled=False,host_mounts_enabled=False,
      actual_vendor_kernel_compatibility_verified=False,recovery_verified=False,
      runtime_getrandom_enosys_fallback_verified=False,
      original_patched_musl_binary_reproducibility_verified=False)


def run(allow_writable=False):
    report=preflight()
    report.update(docker_used=True,offline_qemu_authorized=True,
        disposable_writable_layer_additional_opt_in=bool(allow_writable))
    try:
        report['exact_prior_error']=check_prior_error_fingerprint()
        report['new_probe_linkage']=validate_elf_dependency(NEW_PROBE)
        # The QEMU isolation and cleanup runner remains byte-identical to R59.
        # Substitute ONLY the preverified probe bytes into the disposable guest.
        with ExitStack() as patches:
            patches.enter_context(patch.object(r59,'PROBE',NEW_PROBE))
            patches.enter_context(patch.object(r59,'PROBE_SHA256',NEW_SHA))
            base = r591.execute(allow_writable)
        report.update(result='HOLD',
            arm_guest_execution_performed=base.get('arm_guest_execution_performed') is True,
            all_created_containers_removed=base.get('all_created_containers_removed') is True,
            original_image_unchanged=base.get('original_image_unchanged') is True,
            writable_fallback_used=base.get('writable_fallback_used') is True,
            diagnostic_control_output=base.get('diagnostic_control_output'),
            diagnostics=base.get('diagnostics'),
            r59_wrapper_result=base.get('r59_result'))
        if base.get('result') == r591.PASS and all(report.get(k) is True for k in
                ('arm_guest_execution_performed','all_created_containers_removed','original_image_unchanged')):
            report.update(result=PASS,hold_category='NOT_BOOTABLE',
                pthread_and_tls_runtime_under_qemu_verified=True,
                getrandom_and_getentropy_host_kernel_only_verified=True)
        else:
            report['hold_category']='ARM_QEMU_OR_GUEST_PROBE_HOLD'
    except (Hold,r59.Hold,ValueError,TypeError,OSError,KeyError) as exc:
        report.update(result='HOLD',hold_category=str(exc).splitlines()[0][:145])
    return report


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--authorize-offline-qemu',action='store_true')
    ap.add_argument('--allow-disposable-writable-layer',action='store_true')
    a=ap.parse_args(argv)
    if a.allow_disposable_writable_layer and not a.authorize_offline_qemu:
        r=preflight();r['hold_category']='WRITABLE_OPT_IN_REQUIRES_QEMU_AUTHORIZATION'
    elif a.authorize_offline_qemu:r=run(a.allow_disposable_writable_layer)
    else:r=preflight()
    print(json.dumps(r,sort_keys=True,separators=(',',':')))
    return 0 if r['result']==PASS else 2

if __name__=='__main__':sys.exit(main())
