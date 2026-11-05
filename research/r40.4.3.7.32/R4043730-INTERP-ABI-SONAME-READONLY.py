#!/usr/bin/env python3
"""R4043730: read-only interpreter source-vs-alternative ABI/Soname checks.

Original staged ELF files are read, never executed or written. This standalone
classifier does NOT resolve the absent guest interpreter pathname or prove
runtime loader functionality, boot readiness or deletion safety. NOT_BOOTABLE.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct

R29_NAME = 'R4043729-INTERP-ELF-DYNAMIC-READONLY.py'
R29_PIN = '7ba1cb8d595ab7d50f717eff379b849732d55e507021a15cb7930a1cbc7e80ba'
REQUIRED_29 = {'arch': 'ELF32_ARM', 'eabi': 'EABI_VERSION_5', 'float_flags': 'SOFT_FLOAT_FLAG'}


class Hold(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def load_r29(path):
    if path.name != R29_NAME or path.is_symlink() or not path.is_file():
        raise Hold('R3729_FILE_INVALID')
    if hashlib.sha256(path.read_bytes()).hexdigest() != R29_PIN:
        raise Hold('R3729_SHA_MISMATCH')
    spec = importlib.util.spec_from_file_location('pw3_r3729_pinned', path)
    if spec is None or spec.loader is None:
        raise Hold('R3729_IMPORT_HOLD')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def arm_abi_flags(parent29, parent26, path):
    with parent26.open_regular_nofollow(path) as f:
        h = parent26.elf_header(f)
        if h is None:
            raise Hold('SOURCE_NOT_ELF_HOLD')
        if h['cls'] != 1 or h['machine'] != 40:
            return ('NOT_ELF32_ARM_HOLD', 'NOT_ELF32_ARM_HOLD', h['type'])
        flags, = struct.unpack(h['endian'] + 'I', parent26.read_at(f, 36, 4))
        vals = parent29.arm_flags(flags, h['cls'], h['machine'])
        return vals['eabi'], vals['float_flags'], h['type']


def ph_records(parent26, f, h):
    for i in range(h['phnum']):
        raw = parent26.read_at(f, h['phoff'] + i * h['phsize'], h['phsize'])
        kind, = struct.unpack_from(h['endian'] + 'I', raw, 0)
        if h['cls'] == 1:
            off, addr = struct.unpack_from(h['endian'] + 'II', raw, 4)
            filesz, memsz, flags = struct.unpack_from(h['endian'] + 'III', raw, 16)
        else:
            flags, = struct.unpack_from(h['endian'] + 'I', raw, 4)
            off, addr = struct.unpack_from(h['endian'] + 'QQ', raw, 8)
            filesz, memsz = struct.unpack_from(h['endian'] + 'QQ', raw, 32)
        if off > h['length'] or filesz > h['length'] - off or filesz > memsz:
            raise Hold('PH_BOUNDS_HOLD')
        yield kind, off, addr, filesz, memsz, flags


def inspect_soname(parent26, candidate, expected_basename):
    """Compare DT_SONAME to expected basename, never emit raw SONAME."""
    if not expected_basename or '/' in expected_basename or '\x00' in expected_basename:
        raise Hold('EXPECTED_BASENAME_INVALID')
    with parent26.open_regular_nofollow(candidate) as f:
        h = parent26.elf_header(f)
        if h is None or h['cls'] != 1 or h['machine'] != 40:
            raise Hold('CANDIDATE_ARCH_HOLD')
        segs = list(ph_records(parent26, f, h))
        dyns = [(o, z) for kind, o, _v, z, _m, _flags in segs if kind == 2]
        if len(dyns) != 1:
            raise Hold('DYNAMIC_COUNT_HOLD')
        dynoff, dynsize = dyns[0]
        if not 8 <= dynsize <= 65536 or dynsize % 8:
            raise Hold('DYNAMIC_SIZE_HOLD')
        values = {}
        terminated = False
        for i in range(dynsize // 8):
            tag, val = struct.unpack(h['endian'] + 'II', parent26.read_at(f, dynoff + i*8, 8))
            if tag == 0:
                terminated = True
                break
            values.setdefault(tag, []).append(val)
        if not terminated:
            raise Hold('DYNAMIC_TERMINATION_HOLD')
        if any(len(values.get(x, [])) != 1 for x in (14, 5, 10)):
            raise Hold('DT_SONAME_STRING_TRIPLE_HOLD')
        strv = values[5][0]
        strsz = values[10][0]
        soname_off = values[14][0]
        if not 1 <= strsz <= 65536 or soname_off >= strsz:
            raise Hold('DT_STRTAB_BOUNDS_HOLD')
        matches = []
        for kind, off, vaddr, filesz, _memsz, _flags in segs:
            if kind != 1 or strv < vaddr or strv - vaddr > filesz:
                continue
            delta = strv-vaddr
            if strsz <= filesz-delta:
                matches.append(off+delta)
        if len(set(matches)) != 1:
            raise Hold('DT_STRTAB_MAPPING_HOLD')
        raw = parent26.read_at(f, matches[0]+soname_off, strsz-soname_off)
        nul = raw.find(b'\x00')
        if nul <= 0 or nul > 255:
            raise Hold('DT_SONAME_TERMINATOR_HOLD')
        name = raw[:nul]
        if any(c < 33 or c > 126 for c in name) or b'/' in name or b'\\' in name:
            raise Hold('DT_SONAME_LITERAL_HOLD')
        entrypoint, = struct.unpack(h['endian']+'I', parent26.read_at(f, 24, 4))
        loads = [flags for kind, _off, _v, _z, _m, flags in segs if kind == 1]
        stacks = [flags for kind, _off, _v, _z, _m, flags in segs if kind == 0x6474e551]
        if len(stacks) > 1:
            raise Hold('GNU_STACK_MULTIPLE_HOLD')
        return {
            'soname_basename_match': 'MATCH' if name == expected_basename.encode('ascii') else 'DIFFERENT',
            'elf_entrypoint_nonzero': entrypoint != 0,
            'load_segments_executable_count': sum(bool(x & 1) for x in loads),
            'load_segments_writable_count': sum(bool(x & 2) for x in loads),
            'gnu_stack_exec': 'EXECUTABLE' if stacks and stacks[0] & 1 else 'NONEXECUTABLE' if stacks else 'NOT_DECLARED',
        }


def audit(root, parent26, parent27, parent28, parent29):
    if root.is_symlink() or not root.is_dir():
        raise Hold('ROOTFS_INVALID')
    try:
        inherited = parent29.audit(root, parent26, parent27, parent28)
    except (parent29.Hold, parent28.Hold, parent27.Hold, parent26.Hold):
        raise Hold('R3729_REPLAY_HOLD') from None
    if inherited.get('result') != 'SINGLE_ALTERNATE_ELF_DYNAMIC_METADATA_CLASSIFIED_ONLY':
        raise Hold('R3729_RESULT_HOLD')
    metadata = inherited.get('alternative_metadata', {})
    if metadata.get('header') != REQUIRED_29 or metadata.get('dt_needed_count') != 0 or metadata.get('pt_load_count') != 2 or not metadata.get('dt_soname_present'):
        raise Hold('R3729_EXPECTED_METADATA_HOLD')
    try:
        index, sources, nfiles, nlinks = parent27.inventory(root, parent26)
    except (parent27.Hold, parent26.Hold):
        raise Hold('R3727_INVENTORY_HOLD') from None
    if nfiles != 1446 or nlinks != 335 or len(sources) != 12 or len({lit for lit, _ in sources}) != 1:
        raise Hold('R3727_COUNTS_HOLD')
    missing = sources[0][0]
    basename = missing.rsplit('/', 1)[-1]
    candidates = set()
    per_source = Counter()
    # Source headers may be ELF-header-compatible yet disagree on e_flags; count that independently.
    for literal, source_hdr in sources:
        matches = []
        for candidate, kind in index.get(basename, ()):
            if kind != 'regular':
                continue
            guest = '/' + candidate.relative_to(root).as_posix()
            state, _hops = parent26.classify_guest_target(root, guest, source_hdr)
            if state == 'GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE':
                matches.append(candidate)
        if len(matches) != 1 or literal != missing:
            raise Hold('UNIQUE_CANDIDATE_HOLD')
        candidates.add(matches[0])
    if len(candidates) != 1:
        raise Hold('ALTERNATIVE_IDENTITY_HOLD')
    candidate = next(iter(candidates))
    # Independently enumerate the requesting ELF files without revealing paths.
    source_seen = 0
    def walkerror(_exc):
        raise Hold('SOURCE_WALK_IO_HOLD')
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False, onerror=walkerror):
        dirs[:] = sorted(d for d in dirs if not (Path(base)/d).is_symlink())
        for filename in sorted(files):
            p = Path(base)/filename
            if p.is_symlink() or not p.is_file():
                continue
            try:
                with parent26.open_regular_nofollow(p) as f:
                    parsed = parent26.inspect_elf(f)
            except parent26.Hold:
                raise Hold('SOURCE_PARSE_HOLD') from None
            if parsed is None:
                continue
            _h, segments = parsed
            if any(lit == missing for lit, _padded in segments):
                eabi, floating, elf_type = arm_abi_flags(parent29, parent26, p)
                per_source['EABI_MATCH' if eabi == REQUIRED_29['eabi'] else 'EABI_MISMATCH_OR_UNDECLARED'] += 1
                per_source['FLOAT_FLAGS_MATCH' if floating == REQUIRED_29['float_flags'] else 'FLOAT_FLAGS_DIFFER_OR_UNDECLARED'] += 1
                per_source['SOURCE_ET_DYN' if elf_type == 3 else 'SOURCE_ET_EXEC' if elf_type == 2 else 'SOURCE_ELF_TYPE_OTHER'] += 1
                source_seen += 1
    if source_seen != 12:
        raise Hold('SOURCE_REFERENCES_MISMATCH')
    soname = inspect_soname(parent26, candidate, basename)
    return {
        'milestone': 'R40.4.3.7.30',
        'result': 'INTERP_ABI_AND_SONAME_STATIC_CLASSIFICATION_ONLY',
        'requesting_elf_count': source_seen,
        'source_arm_eabi_float_flag_categories': dict(sorted(per_source.items())),
        'candidate_soname_and_flags': soname,
        'parent_r3729_sha_pinned': True,
        'parent_r3726_r3727_r3728_pinned_and_replayed': True,
        'missing_guest_path_resolved': False,
        'runtime_loader_resolved': False,
        'kernel_abi_and_ARM_attributes_verified': False,
        'historical_inventory_membership_reverified': False,
        'original_r26_source_provenance_authenticated': False,
        'transitive_dependency_closure_proven': False,
        'stage_modified': False, 'paths_or_dynamic_strings_exported': False,
        'boot_authorized': False, 'prune_authorized': False,
        'immutable_hold': 'NOT_BOOTABLE',
    }


def main():
    ap = argparse.ArgumentParser(description='Host-only PT_INTERP ABI/Soname classifier; NOT_BOOTABLE')
    ap.add_argument('--rootfs', type=Path, required=True)
    ap.add_argument('--parent-dir', type=Path, required=True,
                    help='folder containing the pinned R3726, R3727, R3728, R3729 scripts')
    args = ap.parse_args()
    try:
        p29 = load_r29(args.parent_dir / R29_NAME)
        parents = [p29.load_pinned(args.parent_dir / name) for name in p29.PINNED]
        parents_by_name = {name: module for name, module in zip(p29.PINNED, parents)}
        p26 = parents_by_name['R4043726-INTERP-GUEST-RESOLVE-READONLY.py']
        p27 = parents_by_name['R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py']
        p28 = parents_by_name['R4043728-INTERP-PATH-TOPOLOGY-READONLY.py']
        result = audit(args.rootfs, p26, p27, p28, p29)
    except Exception as err:
        category = err.code if isinstance(err, Hold) else 'PARENT_OR_HOST_IO_HOLD'
        result = {'milestone': 'R40.4.3.7.30', 'result': 'HOLD', 'hold_category': category,
                  'boot_authorized': False, 'prune_authorized': False, 'immutable_hold': 'NOT_BOOTABLE'}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['result'] == 'INTERP_ABI_AND_SONAME_STATIC_CLASSIFICATION_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
