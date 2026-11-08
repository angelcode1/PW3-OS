#!/usr/bin/env python3
"""R3877.54: bounded, offline inspection of pinned BusyBox ELF entropy indicators.

No Kindle, ARM execution, boot, or firmware writes. By default no Docker calls.
An independently opted-in stopped-only Docker inspection copies pinned public
candidate ELF files to transient host space, audits then verifies cleanup.

A dynamic symbol import or an embedded string is NOT a call trace, a tested
entropy fallback, or proof that direct syscalls cannot be present.
"""
import argparse
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import uuid

import pw3_r3877_48_musl_interp_audit as baseline

MILESTONE = 'R3877.54'
EXPECTED_R48_SHA256 = '61b42893aa1707e74ddafba5907c380ab65aa286bf233328f19128b16e9d835a'
INTERESTING_IMPORTS = ('getrandom','getentropy','syscall','open','open64',
                       'openat','read','fopen','arc4random','RAND_bytes')
ENTROPY_MARKERS = (b'/dev/urandom',b'/dev/random',b'getrandom',b'getentropy')
PASS = 'PASS_PINNED_BUSYBOX_DIRECT_ELF_ENTROPY_INDICATORS_ONLY'

class AuditHold(Exception):
    pass


def require_baseline_code():
    p = Path(baseline.__file__)
    if not p.is_file() or p.is_symlink() or baseline.digest(p) != EXPECTED_R48_SHA256:
        raise AuditHold('R48_BASELINE_CODE_SHA256_MISMATCH')
    if baseline.PARENT_ID != 'sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a':
        raise AuditHold('R48_BASELINE_IMAGE_ID_CHANGED')


def elf32_dyn_undefined(data):
    """Read ELF32 little-endian section-linked DYNSYM; no code execution.

    The complete executable must already have passed R48 byte/ELF checks.
    Missing/truncated section metadata is HOLD, not an inference of no imports.
    """
    if not isinstance(data,bytes) or len(data) < 52 or len(data) > 24*1024*1024:
        raise AuditHold('ELF_INPUT_SIZE_INVALID')
    if data[:7] != b'\x7fELF\x01\x01\x01':
        raise AuditHold('ELF32_LE_HEADER_INVALID')
    if struct.unpack_from('<H',data,18)[0] != 40:
        raise AuditHold('ELF_NOT_ARM')
    shoff=struct.unpack_from('<I',data,32)[0]
    shentsize,shnum=struct.unpack_from('<HH',data,46)
    if shoff<52 or not (40<=shentsize<=128) or not (1<=shnum<=4096):
        raise AuditHold('ELF_SECTION_HEADERS_MISSING_OR_INVALID')
    if shoff+shentsize*shnum>len(data):
        raise AuditHold('ELF_SECTION_HEADERS_OUT_OF_BOUNDS')
    sections=[]
    for i in range(shnum):
        o=shoff+i*shentsize
        sh_type=struct.unpack_from('<I',data,o+4)[0]
        # ELF32_Shdr: name(0), type(4), flags(8), addr(12), off(16), size(20), link(24), info(28), align(32), entsize(36)
        off,size,link,entsize=(struct.unpack_from('<I',data,o+k)[0] for k in (16,20,24,36))
        if sh_type != 8 and (off>len(data) or size>len(data)-off):
            raise AuditHold('ELF_SECTION_OUT_OF_BOUNDS')
        sections.append((sh_type,off,size,link,entsize))
    dyn=[s for s in sections if s[0]==11]
    if len(dyn)!=1:
        raise AuditHold('DYNAMIC_SYMBOL_TABLE_MISSING_OR_MULTIPLE')
    _,off,size,link,entsize=dyn[0]
    if link>=shnum or sections[link][0]!=3:
        raise AuditHold('DYNAMIC_STRING_TABLE_LINK_INVALID')
    if entsize !=16 or size%entsize or size>16*65536:
        raise AuditHold('DYNAMIC_SYMBOL_TABLE_SIZE_OR_STRIDE_INVALID')
    _,str_off,str_size,_,_=sections[link]
    strings=data[str_off:str_off+str_size]
    if not strings or strings[0:1]!=b'\x00':
        raise AuditHold('DYNAMIC_STRING_TABLE_INVALID')
    imports=set()
    for k in range(0,size,16):
        name=struct.unpack_from('<I',data,off+k)[0]
        shndx=struct.unpack_from('<H',data,off+k+14)[0]
        if shndx!=0 or name==0:continue
        if name>=len(strings):
            raise AuditHold('DYNAMIC_SYMBOL_NAME_OUT_OF_BOUNDS')
        end=strings.find(b'\x00',name,min(len(strings),name+256))
        if end<0:
            raise AuditHold('DYNAMIC_SYMBOL_NAME_UNTERMINATED')
        try:
            token=strings[name:end].decode('ascii')
        except UnicodeDecodeError as e:
            raise AuditHold('DYNAMIC_SYMBOL_NAME_NOT_ASCII') from e
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.@]*',token):
            raise AuditHold('DYNAMIC_SYMBOL_NAME_UNEXPECTED')
        imports.add(token.split('@',1)[0])
    return imports


def inspect_binary_pair(busybox,loader):
    require_baseline_code()
    # Re-use the actual, unchanged R48 byte pins and PT_INTERP ELF32 validation.
    try:linkage=baseline.validate_linkage(busybox,loader)
    except baseline.Hold as e:raise AuditHold('R48_LINKAGE_HOLD:'+str(e)) from e
    content=Path(busybox).read_bytes()
    imports=elf32_dyn_undefined(content)
    has={s:s in imports for s in INTERESTING_IMPORTS}
    markers={s.decode('ascii'):s in content for s in ENTROPY_MARKERS}
    return dict(linkage=linkage, dynamic_import_table_readable=True,
      undefined_dynamic_symbol_count=len(imports),interesting_undefined_imports=has,
      embedded_byte_marker_present=markers,
      direct_getrandom_dynamic_import_present=has['getrandom'],
      direct_getentropy_dynamic_import_present=has['getentropy'],
      no_dynamic_import_does_not_prove_no_syscall=True,
      embedded_string_does_not_prove_executed_path=True,
      application_entropy_fallback_verified=False,
      dynamic_symbol_audit_is_not_syscall_trace=True)


def preflight():
    return dict(milestone=MILESTONE,result='HOLD',hold_category='NOT_AUTHORIZED_OR_INPUT_ABSENT',
      immutable_hold='NOT_BOOTABLE',docker_used=False,docker_stopped_container_only=False,
      arm_executable_launched=False,kindle_ssh_sessions=0,physical_device_access_performed=False,
      boot_performed=False,firmware_write_performed=False,recovery_verified=False,
      target_musl_linux_3_0_35_compatibility_verified=False,
      actual_vendor_syscall_dispatch_verified=False,application_entropy_fallback_verified=False)


def run_files(bb,ld):
    result=preflight()
    try:
        result['binary_audit']=inspect_binary_pair(bb,ld)
        result['result']=PASS
        result['hold_category']='NOT_BOOTABLE'
    except (AuditHold,OSError,ValueError,struct.error) as e:
        result['hold_category']=str(e).splitlines()[0][:150]
    return result


def run_stopped_image():
    r=preflight()
    r.update(docker_used=True,docker_stopped_container_only=True,
             original_image_unchanged=False,stopped_container_removed=False)
    cid=None
    parent_seen=False
    try:
        require_baseline_code()
        baseline.inspect_image()
        parent_seen=True
        with tempfile.TemporaryDirectory(prefix='pw3-r54-') as tmp:
            cp=baseline.docker(['create','--platform','linux/arm/v7','--pull','never',
                 '--network','none','--read-only','--cap-drop','ALL',
                 '--security-opt','no-new-privileges','--pids-limit','32','--name','pw3-r54-static-'+uuid.uuid4().hex[:12],
                 '--entrypoint','/bin/true',baseline.PARENT])
            cid=cp.stdout.strip()
            if not baseline.CID_RE.fullmatch(cid):
                raise AuditHold('STOPPED_CONTAINER_ID_INVALID')
            baseline.inspect_stopped(cid)
            bb=Path(tmp)/'busybox'
            ld=Path(tmp)/'loader'
            baseline.docker(['cp','-L',cid+':/bin/busybox',str(bb)])
            baseline.docker(['cp','-L',cid+':'+baseline.INTERP,str(ld)])
            baseline.inspect_stopped(cid)
            r['binary_audit']=inspect_binary_pair(bb,ld)
            r['result']=PASS
            r['hold_category']='NOT_BOOTABLE'
    except (AuditHold,baseline.Hold,OSError,ValueError,TypeError,KeyError,struct.error) as e:
        r['hold_category']=str(e).splitlines()[0][:150]
    finally:
        if cid:
            try:
                rm=baseline.docker(['rm','-f',cid],allow_nonzero=True)
                check=baseline.docker(['container','inspect',cid],allow_nonzero=True)
                r['stopped_container_removed']=(rm.returncode==0 and check.returncode!=0 and
                     bool(re.search('No such (?:container|object)',check.stderr,re.I)))
            except baseline.Hold:
                r['stopped_container_removed']=False
        if parent_seen:
            try:
                baseline.inspect_image()
                r['original_image_unchanged']=True
            except baseline.Hold:
                r['original_image_unchanged']=False
        if r['result']==PASS and (not r['stopped_container_removed'] or not r['original_image_unchanged']):
            r['result']='HOLD';r['hold_category']='CLEANUP_OR_IMAGE_UNVERIFIED'
    return r


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    modes=p.add_mutually_exclusive_group()
    modes.add_argument('--authorize-stopped-image-audit',action='store_true')
    modes.add_argument('--busybox',help='Local already-copied BusyBox ELF (requires --loader)')
    p.add_argument('--loader',help='Local already-copied musl loader ELF')
    a=p.parse_args(argv)
    if a.authorize_stopped_image_audit:
        if a.loader:p.error('--loader cannot be supplied in Docker mode')
        r=run_stopped_image()
    elif a.busybox and a.loader:
        r=run_files(a.busybox,a.loader)
    elif a.busybox or a.loader:
        r=preflight();r['hold_category']='LOCAL_BUSYBOX_AND_LOADER_BOTH_REQUIRED'
    else:r=preflight()
    print(json.dumps(r,sort_keys=True,separators=(',',':')))
    return 0 if r['result']==PASS else 2

if __name__=='__main__':sys.exit(main())
