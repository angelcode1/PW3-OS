#!/usr/bin/env python3
"""R3877.15: read-only installed-KOReader ELF dependency audit on existing PW3.

No Kindle binaries are installed or started. Existing remote shell and tar read
only /mnt/us/koreader/{luajit,fbink,libs/*.so*}. ELF parsing runs on macOS.
Research/educational only; NOT_BOOTABLE.
"""
import argparse
import hashlib
import io
import json
import re
import struct
import subprocess
import sys
import tarfile

EXPECTED_TARGET = 'root@192.168.8.102'
MAX_ARCHIVE = 96 * 1024 * 1024
MAX_MEMBER = 24 * 1024 * 1024
MAX_MEMBERS = 400
MAX_STR = 4 * 1024 * 1024
TARGET_SCRIPT = r'''#!/bin/sh
# Deliberately fixed, narrow scope; no personal content directories.
root=/mnt/us/koreader
[ -d "$root/libs" ] && [ -f "$root/luajit" ] && [ -f "$root/fbink" ] || exit 44
cd "$root" || exit 45
set -- luajit fbink
for f in libs/*.so libs/*.so.*; do
    if [ -f "$f" ] || [ -L "$f" ]; then
        set -- "$@" "$f"
    fi
done
# Existing stock tar only; target filesystem is never written.
tar -cf - "$@"
'''

class Hold(Exception):
    pass


def safe_name(name):
    if name in ('luajit', 'fbink'):
        return True
    return bool(re.fullmatch(r'libs/[A-Za-z0-9_+.-]{1,180}\.so(?:\.[A-Za-z0-9_+.-]{1,100})?', name)) and '..' not in name


def parse_archive(data):
    if not data or len(data) > MAX_ARCHIVE:
        raise Hold('ARCHIVE_EMPTY_OR_EXCESSIVE')
    result = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
            members = archive.getmembers()
            if not members or len(members) > MAX_MEMBERS:
                raise Hold('ARCHIVE_MEMBER_COUNT_INVALID')
            for m in members:
                if not safe_name(m.name) or m.name in result:
                    raise Hold('ARCHIVE_UNEXPECTED_OR_DUPLICATE_PATH')
                if m.isfile():
                    if m.size > MAX_MEMBER:
                        raise Hold('ARCHIVE_MEMBER_SIZE_EXCEEDED')
                    handle = archive.extractfile(m)
                    if handle is None:
                        raise Hold('ARCHIVE_FILE_READ_FAILED')
                    content = handle.read(MAX_MEMBER + 1)
                    if len(content) != m.size:
                        raise Hold('ARCHIVE_MEMBER_TRUNCATED')
                    result[m.name] = ('file', content)
                elif m.issym():
                    if not re.fullmatch(r'[A-Za-z0-9_+.-]{1,180}', m.linkname) or '..' in m.linkname:
                        raise Hold('ARCHIVE_SYMLINK_TARGET_UNSAFE')
                    result[m.name] = ('symlink', m.linkname)
                else:
                    raise Hold('ARCHIVE_MEMBER_TYPE_UNEXPECTED')
    except (OSError, tarfile.TarError, EOFError) as exc:
        raise Hold('ARCHIVE_INVALID_' + type(exc).__name__) from exc
    if not all(k in result and result[k][0] == 'file' for k in ('luajit','fbink')):
        raise Hold('REQUIRED_BINARIES_ABSENT')
    return result


def cstring(blob, off):
    if off >= len(blob):
        raise Hold('ELF_STRING_OFFSET_INVALID')
    end = blob.find(b'\x00', off)
    if end < 0:
        raise Hold('ELF_STRING_NOT_TERMINATED')
    return blob[off:end].decode('ascii', errors='replace')


def inspect_elf(data):
    if len(data) < 52 or data[:4] != b'\x7fELF':
        return {'kind': 'NON_ELF'}
    if data[4:7] != b'\x01\x01\x01':
        return {'kind': 'ELF_UNSUPPORTED_FORMAT', 'elf_ident': data[4:7].hex()}
    machine = struct.unpack_from('<H', data, 18)[0]
    eflags = struct.unpack_from('<I', data, 36)[0]
    phoff = struct.unpack_from('<I', data, 28)[0]
    entsize, count = struct.unpack_from('<HH', data, 42)
    if count > 128 or entsize < 32 or entsize > 256 or phoff < 52 or phoff + count * entsize > len(data):
        raise Hold('ELF_PROGRAM_HEADERS_INVALID')
    headers = []
    for i in range(count):
        typ, off, va, _pa, fsz, msz, _flags, _align = struct.unpack_from('<IIIIIIII', data, phoff+i*entsize)
        if off > len(data) or fsz > len(data)-off or msz < fsz:
            raise Hold('ELF_SEGMENT_BOUNDS_INVALID')
        headers.append((typ,off,va,fsz))
    interp = []
    for typ,off,_va,fsz in headers:
        if typ == 3:
            if not (1 <= fsz < 1024) or data[off+fsz-1] != 0:
                raise Hold('ELF_INTERP_INVALID')
            interp.append(data[off:off+fsz-1].decode('ascii','replace'))
    if len(interp) > 1:
        raise Hold('ELF_MULTIPLE_INTERPRETERS')
    def virt_to_off(va, n):
        for typ,off,start,fsz in headers:
            if typ == 1 and va >= start and va-start <= fsz and n <= fsz-(va-start):
                return off + va-start
        raise Hold('ELF_DYNAMIC_STRTAB_NOT_MAPPED')
    needed,soname,rpath,runpath = [],[],[],[]
    dyn = [p for p in headers if p[0] == 2]
    if len(dyn) > 1:
        raise Hold('ELF_MULTIPLE_DYNAMIC_SEGMENTS')
    if dyn:
        typ,off,va,fsz = dyn[0]
        if fsz % 8:
            raise Hold('ELF_DYNAMIC_SIZE_INVALID')
        tags = []
        for pos in range(off,off+fsz,8):
            tag,val = struct.unpack_from('<II',data,pos)
            if tag == 0:
                break
            tags.append((tag,val))
        else:
            raise Hold('ELF_DYNAMIC_NOT_TERMINATED')
        dt = dict(tags)
        if 5 in dt and 10 in dt:
            strsize = dt[10]
            if not 0 < strsize <= MAX_STR:
                raise Hold('ELF_DYNSTR_SIZE_INVALID')
            string_off = virt_to_off(dt[5], strsize)
            strings = data[string_off:string_off+strsize]
            for tag,val in tags:
                if tag in (1,14,15,29):
                    target = {1:needed,14:soname,15:rpath,29:runpath}[tag]
                    target.append(cstring(strings,val))
        elif any(tag in (1,14,15,29) for tag,_ in tags):
            raise Hold('ELF_DYNAMIC_STRTAB_MISSING')
    is_hard = bool(eflags & 0x400)
    is_soft = bool(eflags & 0x200)
    return {
        'kind':'ELF32_ARM' if machine==40 else f'ELF32_OTHER_MACHINE_{machine}',
        'eabi_version':eflags>>24,
        'float_abi':'CONFLICT' if is_hard and is_soft else 'HARD' if is_hard else 'SOFT' if is_soft else 'UNSPECIFIED',
        'pt_interp':interp[0] if interp else None,
        'needed':needed,'soname':soname,'rpath':rpath,'runpath':runpath,
    }


def summarize(files):
    output = []
    for name, (kind, value) in sorted(files.items()):
        if kind == 'symlink':
            output.append({'path':name,'kind':'SYMLINK','target_basename':value})
            continue
        header = inspect_elf(value)
        record = {'path':name,'size_bytes':len(value),'sha256':hashlib.sha256(value).hexdigest(),**header}
        output.append(record)
    provided = set()
    for record in output:
        if record.get('kind') == 'ELF32_ARM':
            if record['path'].startswith('libs/'):
                provided.add(record['path'].split('/')[-1])
        if record.get('kind') == 'SYMLINK' and record['path'].startswith('libs/'):
            provided.add(record['path'].split('/')[-1])
    for record in output:
        if record.get('kind') == 'ELF32_ARM':
            record['matching_names_in_collected_app_libs'] = sorted(set(record['needed']) & provided)
            record['external_or_unverified_needed'] = sorted(set(record['needed']) - provided)
    total_elf = sum(rec.get('kind') == 'ELF32_ARM' for rec in output)
    non_arm = [rec['path'] for rec in output if rec['kind'].startswith('ELF32_OTHER')]
    abi_classes = sorted({rec['float_abi'] for rec in output if rec['kind']=='ELF32_ARM'})
    external = sorted({dep for rec in output for dep in rec.get('external_or_unverified_needed',[])})
    return {'file_count':len(files),'arm_elf_file_count':total_elf,
        'unexpected_machine_files':non_arm,'float_abi_declarations':abi_classes,
        'external_or_unverified_library_names':external,
        'files':output}


def remote_tar(target,port):
    try:
        cp = subprocess.run(['ssh','-T','-p',str(port),'-o','ConnectTimeout=12',
               '-o','ConnectionAttempts=1','--',target,'sh -s'],
               input=TARGET_SCRIPT.encode('ascii'), capture_output=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Hold('SSH_CONNECT_OR_TIMEOUT_'+type(e).__name__) from e
    if cp.returncode:
        raise Hold('SSH_ARCHIVE_COMMAND_FAILED_EXIT_'+str(cp.returncode))
    if len(cp.stdout) > MAX_ARCHIVE:
        raise Hold('SSH_ARCHIVE_TOO_LARGE')
    return cp.stdout


def main(argv=None):
    ap=argparse.ArgumentParser(description='R3877.15 KOReader read-only ELF dependencies, NOT_BOOTABLE')
    ap.add_argument('--target',help='existing Kindle SSH user@host')
    ap.add_argument('-p','--port',type=int,default=2222)
    ap.add_argument('--authorize-live-readonly-ssh',action='store_true')
    a=ap.parse_args(argv)
    out={'milestone':'R3877.15','result':'HOLD','hold_category':'EXPLICIT_READONLY_SSH_AUTHORIZATION_REQUIRED',
         'immutable_hold':'NOT_BOOTABLE','authorized_live_readonly_ssh':bool(a.authorize_live_readonly_ssh),
         'new_device_binary_installed_or_executed':False,'firmware_write_performed':False,
         'boot_performed':False,'original_r13_stage_accessed':False,
         'koreader_dependency_closure_verified':False,'pw3_alpine_runtime_verified':False,
         'kernel_syscall_compatibility_verified':False,'recovery_verified':False,
         'device_files_written':False,'system_library_contents_transferred':False,
         'personal_files_transferred':False}
    if a.authorize_live_readonly_ssh:
        try:
            if a.target != EXPECTED_TARGET:
                raise Hold('UNEXPECTED_SSH_TARGET')
            if not (1 <= a.port <= 65535):
                raise Hold('SSH_PORT_INVALID')
            files=parse_archive(remote_tar(a.target,a.port))
            out['inventory']=summarize(files)
            out['result']='PASS_KOREADER_APP_ELF_METADATA_ONLY'
            out['hold_category']='NOT_BOOTABLE'
        except Hold as e:
            out['hold_category']=str(e)
        except Exception as e:
            out['hold_category']='UNEXPECTED_'+type(e).__name__
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if out['result']=='PASS_KOREADER_APP_ELF_METADATA_ONLY' else 2

if __name__=='__main__':
    sys.exit(main())
