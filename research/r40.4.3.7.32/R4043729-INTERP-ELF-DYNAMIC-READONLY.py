#!/usr/bin/env python3
"""R4043729: read-only ELF dynamic/header evidence for one alternate PT_INTERP.

No stage writes; no ELF execution; no guest-path strings emitted. NOT_BOOTABLE.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct

PINNED = {
    'R4043726-INTERP-GUEST-RESOLVE-READONLY.py': '7068af571b0c57677793eb5722938b3a4f14abfd5ce33c6b4e4ce41040e117b3',
    'R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py': 'abd04b8af7f66fa0a5fe46ab889c04811eb1c34c984e91857183f87c838ecaaa',
    'R4043728-INTERP-PATH-TOPOLOGY-READONLY.py': '77b74b5d61dd2bbc61901f3b9e36465164abc36ee28cb41e56b7d0532adb9515',
}


class Hold(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def load_pinned(path):
    if path.name not in PINNED or path.is_symlink() or not path.is_file():
        raise Hold('PARENT_FILE_INVALID')
    if hashlib.sha256(path.read_bytes()).hexdigest() != PINNED[path.name]:
        raise Hold('PARENT_HASH_MISMATCH')
    spec = importlib.util.spec_from_file_location('pinned_' + path.stem.replace('-', '_'), path)
    if spec is None or spec.loader is None:
        raise Hold('PARENT_IMPORT_HOLD')
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def arm_flags(flags, cls, machine):
    """Header-level flags only; ARM attributes and actual ABI remain unverified."""
    if machine != 40 or cls != 1:
        return {'arch': 'NOT_ELF32_ARM', 'eabi': 'NOT_APPLICABLE', 'float_flags': 'NOT_APPLICABLE'}
    ver = (flags >> 24) & 255
    if ver == 0:
        eabi = 'VERSION_UNDECLARED'
    elif 1 <= ver <= 5:
        eabi = 'EABI_VERSION_' + str(ver)
    else:
        eabi = 'UNKNOWN_EABI_VERSION'
    soft = bool(flags & 0x200)
    hard = bool(flags & 0x400)
    if soft and hard:
        floating = 'CONFLICTING_FLOAT_FLAGS_HOLD'
    elif hard:
        floating = 'HARD_FLOAT_FLAG'
    elif soft:
        floating = 'SOFT_FLOAT_FLAG'
    else:
        floating = 'FLOAT_FLAGS_UNDECLARED'
    return {'arch': 'ELF32_ARM', 'eabi': eabi, 'float_flags': floating}


def read_segment_metadata(parent26, fileobj):
    h = parent26.elf_header(fileobj)
    if h is None:
        raise Hold('NOT_ELF_HOLD')
    off_flags = 36 if h['cls'] == 1 else 48
    flags, = struct.unpack(h['endian'] + 'I', parent26.read_at(fileobj, off_flags, 4))
    result = {'header': arm_flags(flags, h['cls'], h['machine']),
              'elf_type': 'ET_DYN' if h['type'] == 3 else 'ET_EXEC' if h['type'] == 2 else 'OTHER',
              'pt_load_count': 0, 'pt_dynamic_count': 0, 'pt_gnu_relro_count': 0,
              'pt_gnu_stack_count': 0, 'dynamic_null_terminated': None,
              'dt_needed_count': 0, 'dt_rpath_present': False,
              'dt_runpath_present': False, 'dt_soname_present': False,
              'dt_strtab_present': False, 'dt_strsz_present': False,
              'dt_textrel_present': False, 'dt_flags_1_present': False,
              'dt_strtab_load_mapping_candidate': False}
    segments = []
    dynamics = []
    for i in range(h['phnum']):
        ph = parent26.read_at(fileobj, h['phoff'] + i * h['phsize'], h['phsize'])
        typ, = struct.unpack_from(h['endian'] + 'I', ph, 0)
        if h['cls'] == 1:
            p_offset, p_vaddr = struct.unpack_from(h['endian'] + 'II', ph, 4)
            p_filesz, p_memsz = struct.unpack_from(h['endian'] + 'II', ph, 16)
        else:
            p_offset, = struct.unpack_from(h['endian'] + 'Q', ph, 8)
            p_vaddr, = struct.unpack_from(h['endian'] + 'Q', ph, 16)
            p_filesz, = struct.unpack_from(h['endian'] + 'Q', ph, 32)
            p_memsz, = struct.unpack_from(h['endian'] + 'Q', ph, 40)
        if p_offset > h['length'] or p_filesz > h['length'] - p_offset or p_filesz > p_memsz:
            raise Hold('SEGMENT_BOUNDS_HOLD')
        if typ == 1:
            result['pt_load_count'] += 1
            segments.append((p_vaddr, p_filesz, p_offset))
        elif typ == 2:
            result['pt_dynamic_count'] += 1
            dynamics.append((p_offset, p_filesz))
        elif typ == 0x6474e552:
            result['pt_gnu_relro_count'] += 1
        elif typ == 0x6474e551:
            result['pt_gnu_stack_count'] += 1
    if result['pt_dynamic_count'] > 1:
        raise Hold('MULTIPLE_DYNAMIC_SEGMENTS_HOLD')
    if dynamics:
        start, size = dynamics[0]
        entrysize = 8 if h['cls'] == 1 else 16
        if size == 0 or size > 65536 or size % entrysize:
            raise Hold('DYNAMIC_SIZE_HOLD')
        values = []
        nullfound = False
        for i in range(size // entrysize):
            raw = parent26.read_at(fileobj, start + i * entrysize, entrysize)
            tag, value = struct.unpack(h['endian'] + ('II' if h['cls'] == 1 else 'QQ'), raw)
            if tag == 0:
                nullfound = True
                break
            values.append((tag, value))
        if not nullfound:
            raise Hold('DYNAMIC_NOT_TERMINATED_HOLD')
        result['dynamic_null_terminated'] = True
        counts = Counter(tag for tag, _ in values)
        result['dt_needed_count'] = counts[1]
        for field, tag in [('dt_rpath_present', 15), ('dt_runpath_present', 29),
                           ('dt_soname_present', 14), ('dt_strtab_present', 5),
                           ('dt_strsz_present', 10), ('dt_textrel_present', 22),
                           ('dt_flags_1_present', 0x6ffffffb)]:
            result[field] = bool(counts[tag])
        tables = [value for tag, value in values if tag == 5]
        sizes = [value for tag, value in values if tag == 10]
        if len(tables) == 1 and len(sizes) == 1:
            addr, length = tables[0], sizes[0]
            for vaddr, filesz, offset in segments:
                if addr >= vaddr and addr - vaddr <= filesz and length <= filesz - (addr - vaddr):
                    result['dt_strtab_load_mapping_candidate'] = True
        if result['dt_needed_count'] and not result['dt_strtab_load_mapping_candidate']:
            raise Hold('NEEDED_STRTAB_UNRESOLVED_HOLD')
    if not result['pt_load_count']:
        raise Hold('NO_LOADABLE_SEGMENTS_HOLD')
    return result


def audit(root, parent26, parent27, parent28):
    if root.is_symlink() or not root.is_dir():
        raise Hold('INVALID_ROOT')
    try:
        baseline = parent28.audit(root, parent27, parent26)
    except (parent28.Hold, parent27.Hold, parent26.Hold):
        raise Hold('R3728_BASELINE_REPLAY_HOLD') from None
    if baseline.get('result') != 'INTERP_SINGLE_PATH_TOPOLOGY_CLASSIFIED_ONLY':
        raise Hold('R3728_RESULT_HOLD')
    if baseline.get('candidate_elf_structure') != {
        'elf_type': 'ET_DYN', 'has_loadable_segment': True,
        'pt_interp_segments': 0, 'pt_load_segments': 2}:
        raise Hold('R3728_CANDIDATE_STRUCTURE_HOLD')
    try:
        index, sources, nfiles, _nlinks = parent27.inventory(root, parent26)
    except (parent27.Hold, parent26.Hold):
        raise Hold('R3727_INVENTORY_REPLAY_HOLD') from None
    if nfiles != 1446 or len(sources) != 12 or len({s for s, _ in sources}) != 1:
        raise Hold('R3727_ABSENT_SOURCE_HOLD')
    missing_literal = sources[0][0]
    basename = missing_literal.rsplit('/', 1)[-1]
    candidates = set()
    for source_literal, source_hdr in sources:
        if source_literal != missing_literal:
            raise Hold('R3727_DISTINCT_SOURCE_HOLD')
        matches = []
        for candidate, kind in index.get(basename, []):
            guest_candidate = '/' + candidate.relative_to(root).as_posix()
            status, _ = parent26.classify_guest_target(root, guest_candidate, source_hdr)
            if status == 'GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE' and kind == 'regular':
                matches.append(candidate)
        if len(matches) != 1:
            raise Hold('R3727_ALTERNATIVE_UNIQUENESS_HOLD')
        candidates.add(matches[0])
    if len(candidates) != 1:
        raise Hold('SOURCE_ALTERNATIVES_DIFFER_HOLD')
    candidate = next(iter(candidates))
    try:
        with parent26.open_regular_nofollow(candidate) as stream:
            metadata = read_segment_metadata(parent26, stream)
    except parent26.Hold:
        raise Hold('PARENT_ELF_HOLD') from None
    if metadata['pt_load_count'] != 2 or metadata['elf_type'] != 'ET_DYN':
        raise Hold('ELF_CANDIDATE_CHANGED_HOLD')
    # No path or dynamic string is serialized.
    return {'milestone': 'R40.4.3.7.29',
            'result': 'SINGLE_ALTERNATE_ELF_DYNAMIC_METADATA_CLASSIFIED_ONLY',
            'parent_r3728_replayed': True, 'parent_r3726_r3727_r3728_sha_pins_verified': True,
            'missing_guest_path_resolved': False, 'unique_alternative_elf_count': 1,
            'absent_interp_segment_count': 12, 'alternative_metadata': metadata,
            'private_guest_paths_or_dynamic_strings_exported': False,
            'original_r26_source_provenance_authenticated': False,
            'transitive_dependency_closure_proven': False,
            'runtime_loader_resolved': False, 'boot_authorized': False,
            'stage_modified': False, 'prune_authorized': False,
            'immutable_hold': 'NOT_BOOTABLE'}


def main():
    p = argparse.ArgumentParser(description='PT_INTERP alternative static ELF metadata; NOT_BOOTABLE')
    p.add_argument('--rootfs', type=Path, required=True)
    p.add_argument('--parent-r3726', type=Path, required=True)
    p.add_argument('--parent-r3727', type=Path, required=True)
    p.add_argument('--parent-r3728', type=Path, required=True)
    a = p.parse_args()
    try:
        p26 = load_pinned(a.parent_r3726)
        p27 = load_pinned(a.parent_r3727)
        p28 = load_pinned(a.parent_r3728)
        result = audit(a.rootfs, p26, p27, p28)
    except (Hold, OSError) as ex:
        result = {'milestone': 'R40.4.3.7.29', 'result': 'HOLD',
                  'hold_category': ex.code if isinstance(ex, Hold) else 'HOST_IO_HOLD',
                  'boot_authorized': False, 'prune_authorized': False,
                  'immutable_hold': 'NOT_BOOTABLE'}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['result'] == 'SINGLE_ALTERNATE_ELF_DYNAMIC_METADATA_CLASSIFIED_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
