#!/usr/bin/env python3
"""R3877.80: host-only, read-only ELF32 ARM LuaJIT dynamic-link audit.

Never executes an ELF, follows a filesystem symlink, reaches the Kindle,
mounts anything, or produces an installable payload. All results retain HOLD.
"""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys

TARGET = ('opt', 'koreader-compat', 'app', 'luajit')
R26_REGULAR_REPORTED = 1448
MAX_ELF = 32 * 1024 * 1024
MAX_ENTRIES = 50000
PT_LOAD, PT_DYNAMIC, PT_INTERP = 1, 2, 3
DT_NEEDED, DT_STRTAB, DT_STRSZ, DT_RPATH, DT_RUNPATH = 1, 5, 10, 15, 29
SONAME = re.compile(r'^[A-Za-z0-9_.+\-]{1,128}$')
KNOWN_INTERPS = {'/lib/ld-linux.so.3', '/lib/ld-linux-armhf.so.3'}

class Refused(ValueError):
    pass


def _span(blob, off, length):
    if off < 0 or length < 0 or off > len(blob) or length > len(blob)-off:
        raise Refused('ELF_RANGE_INVALID')
    return blob[off:off+length]


def _asciiz(buf, start):
    if start >= len(buf):
        raise Refused('ELF_STRING_OFFSET_INVALID')
    end = buf.find(b'\0', start)
    if end < 0:
        raise Refused('ELF_UNTERMINATED_STRING')
    try:
        return buf[start:end].decode('ascii')
    except UnicodeDecodeError:
        raise Refused('ELF_NONASCII_STRING') from None


def parse_luajit(blob):
    if len(blob) < 52 or blob[:7] != b'\x7fELF\x01\x01\x01':
        raise Refused('ELF32_LITTLE_ENDIAN_REQUIRED')
    (etype, machine, version, entry, phoff, _shoff, flags, ehsize,
     phentsize, phnum, _shentsize, _shnum, _shindex) = struct.unpack_from('<HHIIIIIHHHHHH', blob, 16)
    if (etype not in (2, 3) or machine != 40 or version != 1 or ehsize != 52 or
            phentsize != 32 or not 1 <= phnum <= 128 or (flags >> 24) != 5 or entry == 0):
        raise Refused('ARM_EABI5_EXECUTABLE_REQUIRED')
    if flags & 0x600 == 0x600:
        raise Refused('CONFLICTING_ARM_FLOAT_ABI_FLAGS')
    _span(blob, phoff, phnum * 32)
    segments = []
    for i in range(phnum):
        p = struct.unpack_from('<8I', blob, phoff + i*32)
        typ, off, vaddr, _paddr, filesz, _memsz, _flags, _align = p
        if typ in (PT_LOAD, PT_DYNAMIC, PT_INTERP):
            _span(blob, off, filesz)
        segments.append(p)
    interps = [p for p in segments if p[0] == PT_INTERP]
    dynamics = [p for p in segments if p[0] == PT_DYNAMIC]
    if len(interps) != 1 or len(dynamics) != 1:
        raise Refused('EXACTLY_ONE_INTERP_AND_DYNAMIC_REQUIRED')
    p = interps[0]
    interp_raw = _span(blob, p[1], p[4])
    if len(interp_raw) > 128 or not interp_raw.endswith(b'\0'):
        raise Refused('ELF_INTERPRETER_INVALID')
    interp = _asciiz(interp_raw, 0)
    if interp not in KNOWN_INTERPS:
        raise Refused('INTERPRETER_NOT_ALLOWLISTED_GLIBC_ARM')
    d = dynamics[0]
    if d[4] > 32768 or d[4] % 8:
        raise Refused('DYNAMIC_SEGMENT_INVALID')
    tags = []
    terminated = False
    for idx in range(d[4] // 8):
        tag, val = struct.unpack_from('<II', blob, d[1] + idx*8)
        if tag == 0:
            terminated = True
            break
        tags.append((tag, val))
    if not terminated:
        raise Refused('DYNAMIC_TABLE_UNTERMINATED')
    singles = {}
    for tag, val in tags:
        if tag in (DT_STRTAB, DT_STRSZ):
            if tag in singles and singles[tag] != val:
                raise Refused('DYNAMIC_STRING_METADATA_CONFLICT')
            singles[tag] = val
    if DT_STRTAB not in singles or DT_STRSZ not in singles or singles[DT_STRSZ] > 1024*1024:
        raise Refused('DYNAMIC_STRING_TABLE_MISSING_OR_LARGE')
    addr, size = singles[DT_STRTAB], singles[DT_STRSZ]
    mappings = []
    for p in segments:
        typ, off, vaddr, _pa, filesz, _ms, _fl, _al = p
        if typ == PT_LOAD and vaddr <= addr and size <= filesz and addr-vaddr <= filesz-size:
            mappings.append(_span(blob, off + addr-vaddr, size))
    if len(mappings) != 1:
        raise Refused('DYNAMIC_STRING_TABLE_MAPPING_INVALID')
    strtab = mappings[0]
    deps = [_asciiz(strtab, val) for tag, val in tags if tag == DT_NEEDED]
    if not deps or len(deps) > 64 or any(not SONAME.fullmatch(n) or '/' in n for n in deps):
        raise Refused('DEPENDENCY_NAMES_INVALID')
    return {
        'entrypoint': 'opt/koreader-compat/app/luajit',
        'elf_class': 'ELF32_ARM_EABI5',
        'elf_kind': 'EXEC' if etype == 2 else 'DYN',
        'arm_float_header_flag': 'hard' if flags & 0x400 else 'soft' if flags & 0x200 else 'unspecified',
        'arm_e_flags_hex': f'0x{flags:08x}',
        'arm_attributes_vfp_calling_convention_decoded': False,
        'interpreter': interp,
        'needed': deps,
        'has_rpath': any(tag == DT_RPATH for tag, _ in tags),
        'has_runpath': any(tag == DT_RUNPATH for tag, _ in tags),
        'full_dependency_closure_verified': False,
    }


def _safe_stage(stage):
    p = Path(stage).expanduser()
    if not p.is_absolute() or not p.is_dir() or p.is_symlink():
        raise Refused('STAGE_MISSING_NOT_ABSOLUTE_OR_SYMLINK')
    cur = p
    for part in TARGET[:-1]:
        cur = cur / part
        if cur.is_symlink() or not cur.is_dir():
            raise Refused('TARGET_PARENT_MISSING_OR_SYMLINK')
    target = cur / TARGET[-1]
    if target.is_symlink() or not target.is_file():
        raise Refused('TARGET_MISSING_OR_SYMLINK')
    fd = os.open(str(target), os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        fst = os.fstat(fd)
        if not stat.S_ISREG(fst.st_mode) or fst.st_size > MAX_ELF:
            raise Refused('TARGET_NOT_BOUNDED_REGULAR_FILE')
        blocks=[]
        remaining=fst.st_size
        while remaining:
            b=os.read(fd, min(1_048_576, remaining))
            if not b:
                raise Refused('TARGET_READ_TRUNCATED')
            blocks.append(b)
            remaining-=len(b)
        aft=os.fstat(fd)
        if (fst.st_dev, fst.st_ino, fst.st_size, fst.st_mtime_ns) != (aft.st_dev,aft.st_ino,aft.st_size,aft.st_mtime_ns):
            raise Refused('TARGET_CHANGED_DURING_READ')
        return p, b''.join(blocks)
    finally:
        os.close(fd)


def provider_counts(stage, needed, interp):
    wanted = sorted(set(needed + [Path(interp).name]))
    regular = {key: 0 for key in wanted}
    symbolic = {key: 0 for key in wanted}
    regular_total = 0
    links_total = 0
    dir_seen = 0
    for base, dirs, names in os.walk(stage, topdown=True, followlinks=False):
        dir_seen += 1
        if dir_seen > MAX_ENTRIES:
            raise Refused('STAGE_TOO_MANY_DIRECTORIES')
        kept = []
        for dn in dirs:
            path = Path(base) / dn
            if path.is_symlink():
                links_total += 1
                if dn in symbolic:
                    symbolic[dn] += 1
            else:
                kept.append(dn)
        dirs[:] = kept
        for name in names:
            file = Path(base) / name
            if file.is_symlink():
                links_total += 1
                if name in symbolic:
                    symbolic[name] += 1
            elif file.is_file():
                regular_total += 1
                if name in regular:
                    regular[name] += 1
            if regular_total + links_total > MAX_ENTRIES:
                raise Refused('STAGE_TOO_MANY_ENTRIES')
    return dict(stage_regular_file_count=regular_total,
                historical_r26_regular_file_count=R26_REGULAR_REPORTED,
                count_difference_from_historical_r26=regular_total-R26_REGULAR_REPORTED,
                same_stage_bytes_reverified_against_r26=False,
                symlinks_skipped=links_total,
                candidates=[{'object_name': k, 'regular_name_matches':regular[k],
                             'symlink_name_matches_not_followed':symbolic[k],
                             'runtime_loader_resolution_verified':False} for k in wanted])


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--stage',required=True)
    ap.add_argument('--acknowledge-host-only-elf-audit',action='store_true')
    args=ap.parse_args(argv)
    report=dict(milestone='R3877.80',result='HOLD',immutable_hold='NOT_BOOTABLE',
                hold_category='HOST_ONLY_ELF_AUDIT_NOT_AUTHORIZED',
                kindle_access_performed=False,device_execution_performed=False,
                local_files_modified=False,boot_hook_modified=False,
                recovery_verified=False,koreader_device_runtime_verified=False)
    if args.acknowledge_host_only_elf_audit:
        try:
            stage, blob = _safe_stage(args.stage)
            app = parse_luajit(blob)
            count = provider_counts(stage, app['needed'], app['interpreter'])
            report['review']={'luajit':app,'provider_name_catalog':count}
            report['hold_category']='GLIBC_LUAJIT_RUNTIME_AND_ABI_NEEDS_SEPARATE_VERIFICATION'
        except (OSError, Refused, UnicodeError, struct.error):
            report['hold_category']='HOST_ELF_OR_STAGE_REVIEW_REFUSED'
    print(json.dumps(report,sort_keys=True,separators=(',',':')))
    return 2

if __name__=='__main__':
    sys.exit(main())
