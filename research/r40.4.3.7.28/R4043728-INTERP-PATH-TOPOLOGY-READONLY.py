#!/usr/bin/env python3
"""R4043728 source-only modeled PT_INTERP missing-path topology audit.

Preserves R3727/R3726 exact source SHA pins. Does not write to rootfs, reveal
private paths, run staged ELF files, boot, or authorize firmware/pruning.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct

PARENT27_NAME = 'R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py'
PARENT27_SHA = 'abd04b8af7f66fa0a5fe46ab889c04811eb1c34c984e91857183f87c838ecaaa'
EXPECTED_CATEGORY = {'ONE_REGULAR_SAME_BASENAME_ABI_HEADER_CANDIDATE': 12}
EXPECTED_EDGES = {
    'absent_segments_with_any_same_basename_entries': 12,
    'same_basename_regular_abi_header_candidate_entries': 12,
    'same_basename_symlink_abi_header_candidate_entries': 0,
}

class Hold(Exception):
    def __init__(self, category):
        super().__init__(category)
        self.category = category


def load_pinned_r3727(path):
    """Checks exact source before import, then delegates parent R3726 pin."""
    if path.is_symlink() or not path.is_file() or path.name != PARENT27_NAME:
        raise Hold('R3727_INVALID_FILE')
    if hashlib.sha256(path.read_bytes()).hexdigest() != PARENT27_SHA:
        raise Hold('R3727_SHA_MISMATCH')
    spec = importlib.util.spec_from_file_location('pw3_r3727_verified', path)
    if not spec or not spec.loader:
        raise Hold('R3727_IMPORT_HOLD')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def guest_parent_status(root, guest, max_symlinks=40):
    """Classify the parent directory of an absent guest pathname (no host link following).

    Absolute symlinks are interpreted in the *guest root* rather than the host
    filesystem. A missing component, dangling symlink, non-directory component,
    root escape, or symlink cycle remains a hold.
    """
    if not guest.startswith('/') or guest == '/' or '\x00' in guest or '\\' in guest:
        return 'PARENT_INVALID_PATH_HOLD', 0
    parts = guest.split('/')[1:]
    if any(p in ('', '.', '..') for p in parts):
        return 'PARENT_INVALID_PATH_HOLD', 0
    pending = parts[:-1]
    settled = []
    hops = 0
    while pending:
        part = pending.pop(0)
        if part in ('', '.'):
            continue
        if part == '..':
            if not settled:
                return 'PARENT_GUEST_ESCAPE_HOLD', hops
            settled.pop()
            continue
        current = root.joinpath(*settled, part)
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return 'PARENT_DIRECTORY_COMPONENT_ABSENT', hops
        except OSError:
            return 'PARENT_IO_HOLD', hops
        if stat.S_ISLNK(mode):
            hops += 1
            if hops > max_symlinks:
                return 'PARENT_SYMLINK_LIMIT_HOLD', hops
            try:
                target = os.readlink(current)
            except OSError:
                return 'PARENT_IO_HOLD', hops
            if not target:
                return 'PARENT_EMPTY_SYMLINK_HOLD', hops
            if target.startswith('/'):
                settled.clear()
                pending = target.split('/')[1:] + pending
            else:
                pending = target.split('/') + pending
            continue
        if not stat.S_ISDIR(mode):
            return 'PARENT_NON_DIRECTORY_COMPONENT_HOLD', hops
        settled.append(part)
    return 'PARENT_DIRECTORY_PRESENT', hops


def candidate_elf_structure(parent26, path):
    """Count loadable ELF program headers for a static candidate, no execution."""
    with parent26.open_regular_nofollow(path) as f:
        h = parent26.elf_header(f)
        if h is None:
            raise Hold('CANDIDATE_NOT_ELF_HOLD')
        # Tighten basic program-header structural checks; keep runtime unresolved.
        pt_loads = 0
        interp = 0
        for i in range(h['phnum']):
            p = parent26.read_at(f, h['phoff'] + i * h['phsize'], h['phsize'])
            typ, = struct.unpack_from(h['endian'] + 'I', p, 0)
            if typ == 1:
                pt_loads += 1
                if h['cls'] == 1:
                    offset, = struct.unpack_from(h['endian'] + 'I', p, 4)
                    filesz, = struct.unpack_from(h['endian'] + 'I', p, 16)
                    memsz, = struct.unpack_from(h['endian'] + 'I', p, 20)
                else:
                    offset, = struct.unpack_from(h['endian'] + 'Q', p, 8)
                    filesz, = struct.unpack_from(h['endian'] + 'Q', p, 32)
                    memsz, = struct.unpack_from(h['endian'] + 'Q', p, 40)
                if offset > h['length'] or filesz > h['length'] - offset or filesz > memsz:
                    raise Hold('CANDIDATE_PT_LOAD_BOUNDS_HOLD')
            if typ == 3:
                interp += 1
        return {'elf_type': 'ET_DYN' if h['type'] == 3 else 'ET_EXEC' if h['type'] == 2 else 'OTHER',
                'pt_load_segments': pt_loads, 'pt_interp_segments': interp,
                'has_loadable_segment': pt_loads > 0}


def audit(root, parent27, parent26):
    if root.is_symlink() or not root.is_dir():
        raise Hold('ROOTFS_INVALID')
    try:
        earlier = parent27.audit(root, parent26)
    except parent27.Hold:
        raise Hold('R3727_REPLAY_HOLD') from None
    if earlier.get('result') != 'ABSENT_INTERP_SAME_BASENAME_ALTERNATIVES_CLASSIFIED_ONLY':
        raise Hold('R3727_RESULT_HOLD')
    if earlier.get('absent_interp_segments') != 12 or earlier.get('distinct_absent_guest_path_literals') != 1:
        raise Hold('R3727_ABSENT_UNIQUENESS_HOLD')
    if earlier.get('distinct_absent_basename_literals') != 1:
        raise Hold('R3727_ABSENT_BASENAME_HOLD')
    if earlier.get('same_basename_alternative_categories') != EXPECTED_CATEGORY:
        raise Hold('R3727_ALTERNATIVE_CATEGORY_HOLD')
    if earlier.get('same_basename_candidate_entry_counts') != EXPECTED_EDGES:
        raise Hold('R3727_ALTERNATIVE_COUNT_HOLD')
    if earlier.get('rootfs_regular_files') != 1446 or earlier.get('rootfs_symlink_entries_seen') != 335:
        raise Hold('R3727_INVENTORY_HOLD')
    # Parent R3727 already checks R3726 source + counts and path classifications.
    try:
        index, sources, nfiles, nlinks = parent27.inventory(root, parent26)
    except parent27.Hold:
        raise Hold('R3727_INVENTORY_REPLAY_HOLD') from None
    literals = {guest for guest, _hdr in sources}
    if len(literals) != 1 or len(sources) != 12 or nfiles != 1446 or nlinks != 335:
        raise Hold('R3727_INDEPENDENT_REPLAY_HOLD')
    missing = next(iter(literals))
    basename = missing.rsplit('/', 1)[-1]
    candidate_set = set()
    nonmatching = 0
    for source_guest, header in sources:
        if source_guest != missing:
            raise Hold('SOURCES_DIFFERENT_MISSING_PATH_HOLD')
        matched_this_source = []
        for candidate, typ in index.get(basename, []):
            # R3727 reported exactly one matching regular candidate per source.
            guest_candidate = '/' + candidate.relative_to(root).as_posix()
            try:
                category, _hops = parent26.classify_guest_target(root, guest_candidate, header)
            except parent26.Hold:
                raise Hold('R3726_CANDIDATE_PARSE_HOLD') from None
            if category == 'GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE' and typ == 'regular':
                matched_this_source.append(candidate)
            elif category != 'GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE':
                nonmatching += 1
        if len(matched_this_source) != 1:
            raise Hold('REPLAY_CANDIDATE_UNIQUE_HOLD')
        candidate_set.add(matched_this_source[0])
    if len(candidate_set) != 1:
        raise Hold('CANDIDATE_DIFFERS_BY_SOURCE_HOLD')
    # The expected literal stays absent. No alias is created and no file is moved.
    try:
        status, _ = parent26.classify_guest_target(root, missing, sources[0][1])
    except parent26.Hold:
        raise Hold('R3726_MISSING_PATH_REPLAY_HOLD') from None
    if status != 'GUEST_ABSENT_HOLD':
        raise Hold('MISSING_PATH_NO_LONGER_ABSENT_HOLD')
    parent_cat, parent_hops = guest_parent_status(root, missing)
    candidate = next(iter(candidate_set))
    try:
        structure = candidate_elf_structure(parent26, candidate)
    except parent26.Hold:
        raise Hold('R3726_CANDIDATE_ELF_STRUCTURE_HOLD') from None
    if structure['elf_type'] not in ('ET_DYN', 'ET_EXEC'):
        raise Hold('CANDIDATE_ELF_TYPE_HOLD')
    return {
        'milestone': 'R40.4.3.7.28',
        'result': 'INTERP_SINGLE_PATH_TOPOLOGY_CLASSIFIED_ONLY',
        'distinct_absent_guest_path_literals': 1,
        'absent_interp_segments': 12,
        'unique_compatible_alternative_regular_files': 1,
        'missing_parent_directory_categories': {parent_cat: 1},
        'missing_parent_guest_symlink_hops': parent_hops,
        'same_basename_other_candidate_entries_across_sources': nonmatching,
        'candidate_elf_structure': structure,
        'r3727_source_pin_verified': True,
        'r3726_source_pin_verified': True,
        'r3727_counts_and_categories_replayed': True,
        'interpreter_guest_path_resolved': False,
        'candidate_is_not_at_requested_guest_path': True,
        'runtime_loader_resolved': False,
        'transitive_dependency_closure_proven': False,
        'original_r26_source_provenance_authenticated': False,
        'historical_inventory_membership_reverified': False,
        'guest_path_or_symlink_strings_exported': False,
        'stage_modified': False,
        'boot_authorized': False,
        'prune_authorized': False,
        'immutable_hold': 'NOT_BOOTABLE',
    }


def main():
    ap = argparse.ArgumentParser(description='Read-only static PT_INTERP directory-topology audit. NOT_BOOTABLE')
    ap.add_argument('--rootfs', type=Path, required=True)
    ap.add_argument('--parent-r3727', type=Path, required=True)
    ap.add_argument('--parent-r3726', type=Path, required=True)
    args = ap.parse_args()
    try:
        r3727 = load_pinned_r3727(args.parent_r3727)
        try:
            r3726 = r3727.verify_parent(args.parent_r3726)
        except r3727.Hold as exc:
            raise Hold('R3726_' + exc.category) from None
        result = audit(args.rootfs, r3727, r3726)
    except (Hold, OSError) as exc:
        result = {
            'milestone': 'R40.4.3.7.28',
            'result': 'HOLD',
            'hold_category': exc.category if isinstance(exc, Hold) else 'HOST_IO_HOLD',
            'boot_authorized': False,
            'prune_authorized': False,
            'immutable_hold': 'NOT_BOOTABLE',
        }
    print(json.dumps(result, sort_keys=True))
    return 0 if result['result'] == 'INTERP_SINGLE_PATH_TOPOLOGY_CLASSIFIED_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
