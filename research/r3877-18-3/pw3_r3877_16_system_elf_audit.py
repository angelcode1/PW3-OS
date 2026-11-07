#!/usr/bin/env python3
"""R3877.16: limited stock-library ELF metadata audit. Research only; NOT_BOOTABLE."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
from r3877_elf_parser import inspect_elf, Hold

EXPECTED_TARGET = 'root@192.168.8.102'
NAMES = ('ld-linux.so.3','libc.so.6','libdl.so.2','libgcc_s.so.1',
         'libm.so.6','libpthread.so.0','librt.so.1')
PREFIXES = ('lib/','usr/lib/','usr/local/lib/')
MAX_ARCHIVE = 36 * 1024 * 1024
MAX_MEMBER = 16 * 1024 * 1024
TARGET_SCRIPT = r'''#!/bin/sh
# Fixed system library names only, no user files; no files created on device.
cd / || exit 43
set --
for name in ld-linux.so.3 libc.so.6 libdl.so.2 libgcc_s.so.1 libm.so.6 libpthread.so.0 librt.so.1; do
    for dir in lib usr/lib usr/local/lib; do
        if [ -f "$dir/$name" ]; then
            set -- "$@" "$dir/$name"
            break
        fi
    done
done
[ "$#" -gt 0 ] || exit 44
# Dereference library symlinks; streamed archive, not stored on the Kindle.
tar -chf - "$@"
'''

def allowed_member(name):
    return any(name == pre + lib for pre in PREFIXES for lib in NAMES)

def parse_archive(buf):
    if not buf or len(buf) > MAX_ARCHIVE: raise Hold('ARCHIVE_EMPTY_OR_TOO_LARGE')
    result = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(buf),mode='r:') as tar:
            members = tar.getmembers()
            if not members or len(members) > len(NAMES): raise Hold('ARCHIVE_COUNT_INVALID')
            for m in members:
                if not allowed_member(m.name) or m.name in result:
                    raise Hold('ARCHIVE_UNEXPECTED_OR_DUPLICATE_NAME')
                if not m.isfile() or m.size < 52 or m.size > MAX_MEMBER:
                    raise Hold('ARCHIVE_NOT_REGULAR_ELF_OR_TOO_LARGE')
                f = tar.extractfile(m)
                if f is None: raise Hold('ARCHIVE_FILE_UNREADABLE')
                data = f.read(MAX_MEMBER + 1)
                if len(data) != m.size: raise Hold('ARCHIVE_TRUNCATED')
                result[m.name] = data
    except (OSError,tarfile.TarError,EOFError) as e:
        raise Hold('ARCHIVE_INVALID_'+type(e).__name__) from e
    return result

def load_koreader_evidence(path):
    if not path: return None
    try: raw=json.loads(Path(path).read_text())
    except (OSError,ValueError,UnicodeError) as e: raise Hold('KOREADER_EVIDENCE_UNREADABLE') from e
    if raw.get('milestone') != 'R3877.15' or raw.get('result') != 'PASS_KOREADER_APP_ELF_METADATA_ONLY':
        raise Hold('KOREADER_EVIDENCE_MILESTONE_INVALID')
    inv=raw.get('inventory',{})
    if inv.get('arm_elf_file_count') != 38 or inv.get('float_abi_declarations') != ['SOFT']:
        raise Hold('KOREADER_EVIDENCE_NOT_EXPECTED_SOFT_FLOAT')
    ext=inv.get('external_or_unverified_library_names')
    if not isinstance(ext,list) or set(ext) != set(NAMES):
        raise Hold('KOREADER_EVIDENCE_PROVIDER_SET_DIFFERENT')
    return {'r3877_15_evidence_checked':True,'r3877_15_elf_file_count':38,
            'r3877_15_float_abi':'SOFT','needed_names':sorted(ext)}

def summarize(files, koreader):
    names={}
    for path,blob in files.items():
        name=path.rsplit('/',1)[1]
        if name in names: raise Hold('MULTIPLE_PATHS_FOR_SAME_PROVIDER')
        elf=inspect_elf(blob)
        names[name]={'source_path':path,'sha256':hashlib.sha256(blob).hexdigest(),
            'bytes':len(blob),'kind':elf['kind'],'eabi_version':elf.get('eabi_version'),
            'float_abi':elf.get('float_abi'),'pt_interp':elf.get('pt_interp'),
            'needed':elf.get('needed',[]),'soname':elf.get('soname',[]),
            'rpath':elf.get('rpath',[]),'runpath':elf.get('runpath',[])}
    missing=sorted(set(NAMES)-set(names))
    mismatched=sorted(n for n,v in names.items() if
            v['kind']!='ELF32_ARM' or v['eabi_version']!=5 or v['float_abi']!='SOFT')
    other_needed=sorted({n for v in names.values() for n in v['needed'] if n not in NAMES})
    result={'provider_names_expected':sorted(NAMES),'provider_names_found':sorted(names),
        'provider_names_absent':missing,'provider_abi_mismatch':mismatched,
        'provider_indirect_dependencies_not_audited':other_needed,'providers':names,
        'all_seven_providers_found':not missing,
        'all_provider_elf_headers_match_koreader_soft_float':not missing and not mismatched,
        'glibc_symbol_versions_verified':False,'library_resolution_at_runtime_verified':False,
        'koreader_dependency_closure_verified':False}
    if koreader is not None: result['comparison_to_r3877_15']=koreader
    return result

def remote_tar(target,port):
    try:
        cp=subprocess.run(['ssh','-T','-p',str(port),'-o','ConnectTimeout=12',
            '-o','ConnectionAttempts=1','--',target,'sh -s'],
            input=TARGET_SCRIPT.encode('ascii'),capture_output=True,timeout=140)
    except (OSError,subprocess.TimeoutExpired) as e:
        raise Hold('SSH_CONNECT_OR_TIMEOUT_'+type(e).__name__) from e
    if cp.returncode: raise Hold('REMOTE_TAR_FAILED_EXIT_'+str(cp.returncode))
    if len(cp.stdout)>MAX_ARCHIVE: raise Hold('REMOTE_ARCHIVE_TOO_LARGE')
    return cp.stdout

def main(argv=None):
    ap=argparse.ArgumentParser(description='PW3 R3877.16 stock-library audit, NOT_BOOTABLE')
    ap.add_argument('--target',help='existing authorized SSH target')
    ap.add_argument('-p','--port',type=int,default=2222)
    ap.add_argument('--koreader-evidence',help='optional local r3877_15_result.json')
    ap.add_argument('--authorize-live-readonly-ssh',action='store_true')
    a=ap.parse_args(argv)
    out={'milestone':'R3877.16','result':'HOLD',
        'hold_category':'EXPLICIT_READONLY_SSH_AUTHORIZATION_REQUIRED',
        'immutable_hold':'NOT_BOOTABLE','boot_performed':False,
        'authorized_live_readonly_ssh':bool(a.authorize_live_readonly_ssh),
        'device_files_written':False,'new_device_binary_installed_or_executed':False,
        'firmware_write_performed':False,'original_r13_stage_accessed':False,
        'guest_network_enabled':False,'host_binfmt_changed':False,
        'personal_files_transferred':False,'system_library_contents_transferred':False,
        'target_musl_runtime_verified':False,'kernel_syscall_compatibility_verified':False,
        'koreader_dependency_closure_verified':False,'recovery_verified':False}
    if a.authorize_live_readonly_ssh:
        try:
            if a.target!=EXPECTED_TARGET: raise Hold('UNEXPECTED_SSH_TARGET')
            if not 1<=a.port<=65535: raise Hold('SSH_PORT_INVALID')
            evidence=load_koreader_evidence(a.koreader_evidence)
            files=parse_archive(remote_tar(a.target,a.port))
            out['system_library_contents_transferred']=True
            out['inventory']=summarize(files,evidence)
            if out['inventory']['all_provider_elf_headers_match_koreader_soft_float']:
                out['result']='PASS_SYSTEM_ELF_METADATA_ONLY'
                out['hold_category']='NOT_BOOTABLE'
            else:
                out['hold_category']='SYSTEM_PROVIDER_ABSENT_OR_ABI_MISMATCH'
        except Hold as e: out['hold_category']=str(e)
        except Exception as e: out['hold_category']='UNEXPECTED_'+type(e).__name__
    print(json.dumps(out,sort_keys=True,indent=2))
    return 0 if out['result']=='PASS_SYSTEM_ELF_METADATA_ONLY' else 2

if __name__=='__main__': sys.exit(main())
