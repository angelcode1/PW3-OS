#!/usr/bin/env python3
"""R3877.79: read-only local staged KOReader native-entrypoint preflight.

No network, device execution, mounts, guest execution, symlink traversal or writes
except to explicitly redirected stdout. Never infers recovery/boot approval.
"""
import argparse
import json
import os
from pathlib import Path
import stat
import struct
import sys

CANDIDATE_NAMES = frozenset(('luajit','lua','lua5.1','lua5.2','koreader','koreader.bin','launcher'))

class Refused(Exception):
    pass


def candidate_name(name):
    lo = name.lower()
    return lo in CANDIDATE_NAMES or lo.startswith(('luajit-', 'libluajit-'))


def inspect_elf(path):
    with path.open('rb') as f:
        h = f.read(52)
        if len(h) < 4 or h[:4] != b'\x7fELF':
            return None
        if len(h) < 52 or h[4:7] != b'\x01\x01\x01':
            raise Refused('ELF_NOT_32BIT_LITTLE_ENDIAN')
        e_type, machine, version = struct.unpack_from('<HHI', h, 16)
        entry, phoff = struct.unpack_from('<II', h, 24)
        flags = struct.unpack_from('<I', h, 36)[0]
        phentsize, phnum = struct.unpack_from('<HH', h, 42)
        if version != 1 or e_type not in (2,3) or phentsize != 32 or phnum > 256:
            raise Refused('ELF_HEADER_UNEXPECTED')
        size = f.seek(0, 2)
        if phoff + phentsize * phnum > size:
            raise Refused('ELF_PROGRAM_HEADERS_OUT_OF_BOUNDS')
        f.seek(phoff)
        ph = f.read(phentsize * phnum)
        interp = None
        dynamic = False
        for i in range(phnum):
            typ, offset, vaddr, paddr, filesz, memsz, pflags, align = struct.unpack_from('<8I', ph, i*32)
            if typ == 2:
                dynamic = True
            if typ == 3:
                if interp is not None or filesz < 2 or filesz > 256 or offset + filesz > size:
                    raise Refused('ELF_INTERPRETER_INVALID')
                f.seek(offset)
                v = f.read(filesz)
                if not v.endswith(b'\x00'):
                    raise Refused('ELF_INTERPRETER_INVALID')
                interp = v[:-1].decode('ascii', errors='replace')
        if interp is None:
            group = 'NO_PT_INTERP'
        elif interp in ('/lib/ld-linux-armhf.so.3', '/lib/ld-linux.so.3'):
            group = 'GLIBC_ARM_LOADER'
        elif interp.startswith('/lib/ld-musl-') and interp.endswith('.so.1'):
            group = 'MUSL_LOADER'
        else:
            group = 'OTHER_REDACTED'
        return dict(machine='ARM' if machine == 40 else 'OTHER',
                    elf_type='EXEC' if e_type == 2 else 'DYN',
                    arm_eabi5=(flags >> 24) == 5,
                    arm_hard_float=bool(flags & 0x400),
                    dynamic_segment=dynamic,
                    interpreter_class=group,
                    executable_entrypoint=(entry != 0))


def inventory(root):
    root = Path(root).expanduser()
    if root.is_symlink() or not root.is_dir():
        raise Refused('STAGE_ROOT_MISSING_OR_SYMLINK')
    counts = dict(regular_files_seen=0, elf_files_seen=0, arm_elf_seen=0,
                  symlinks_skipped=0, candidate_symlink_names=0,
                  elf_errors=0, candidate_elf_count=0)
    candidates = []
    # All names and candidate paths here are relative to the rootfs stage, never
    # absolute private Mac paths. Symlink targets are intentionally not read.
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        keep = []
        for dirname in dirs:
            p = Path(base) / dirname
            if p.is_symlink():
                counts['symlinks_skipped'] += 1
                if candidate_name(dirname):
                    counts['candidate_symlink_names'] += 1
            else:
                keep.append(dirname)
        dirs[:] = keep
        for name in files:
            p = Path(base) / name
            if p.is_symlink():
                counts['symlinks_skipped'] += 1
                if candidate_name(name):
                    counts['candidate_symlink_names'] += 1
                continue
            mode = p.lstat().st_mode
            if not stat.S_ISREG(mode):
                continue
            counts['regular_files_seen'] += 1
            if counts['regular_files_seen'] > 100_000:
                raise Refused('STAGE_FILE_COUNT_LIMIT')
            if p.stat().st_size > 256 * 1024 * 1024:
                continue
            try:
                info = inspect_elf(p)
            except (Refused, OSError, UnicodeError, struct.error):
                counts['elf_errors'] += 1
                continue
            if info is None:
                continue
            counts['elf_files_seen'] += 1
            if info['machine'] == 'ARM':
                counts['arm_elf_seen'] += 1
            if candidate_name(name):
                counts['candidate_elf_count'] += 1
                if len(candidates) < 20:
                    # Limited, relative, controlled application filename only.
                    candidates.append({'relative_path':p.relative_to(root).as_posix(), **info})
    counts['candidates_truncated'] = counts['candidate_elf_count'] > len(candidates)
    return {'counts':counts, 'candidate_elfs':sorted(candidates,key=lambda x:x['relative_path'])}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage',required=True)
    p.add_argument('--acknowledge-local-readonly-stage-inspection', action='store_true')
    a=p.parse_args(argv)
    out={'milestone':'R3877.79','result':'HOLD',
         'immutable_hold':'NOT_BOOTABLE','device_execution_performed':False,
         'device_connected':False,'stage_files_modified':False,
         'koreader_device_runtime_verified':False,'recovery_verified':False,
         'hold_category':'EXPLICIT_LOCAL_STAGE_INSPECTION_OPT_IN_REQUIRED'}
    if not a.acknowledge_local_readonly_stage_inspection:
        print(json.dumps(out,sort_keys=True))
        return 2
    try:
        review=inventory(a.stage)
        out['review']=review
        out['hold_category']='KO_READER_NATIVE_ENTRYPOINT_SELECTED_FOR_FUTURE_REVIEW' if any(
            x['machine']=='ARM' and x['executable_entrypoint'] for x in review['candidate_elfs']) else 'NO_ARM_ENTRYPOINT_CANDIDATE_IDENTIFIED'
    except (OSError, Refused) as exc:
        out['hold_category']='STAGE_READ_REFUSED'
        if isinstance(exc,Refused): out['offline_refusal_code']=str(exc)
    print(json.dumps(out,sort_keys=True))
    return 2


if __name__=='__main__':
    sys.exit(main())
