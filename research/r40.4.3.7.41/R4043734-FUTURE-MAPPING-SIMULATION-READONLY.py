#!/usr/bin/env python3
"""R4043734: simulate a FUTURE independently built guest interpreter mapping.

NO stage mutation, symlink creation, execution, device I/O, or boot authorization.
No private path names or symlink target strings in default output. All stage
reads are bounded to the R13 rootfs and the SHA-pinned parent audit lineage.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import posixpath
import stat

R33 = 'R4043733-INTERP-LAYOUT-READONLY.py'
PIN33 = 'c16d029944344943fef2274582b93c00fad115bc4a4564e5f4298cc614c0d3bc'


class Hold(Exception):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def import_r33(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_HOLD')
    path = folder / R33
    if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != PIN33:
        raise Hold('R3733_SHA_OR_FILE_HOLD')
    spec = importlib.util.spec_from_file_location('pw3_r3733_pinned_for_r3734', path)
    if not spec or not spec.loader:
        raise Hold('R3733_IMPORT_HOLD')
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def components(guest):
    if (not isinstance(guest, str) or not guest.startswith('/') or guest == '/'
            or '\x00' in guest or '\\' in guest):
        raise Hold('INVALID_GUEST_PATH_HOLD')
    parts = guest[1:].split('/')
    if any(part in ('', '.', '..') for part in parts):
        raise Hold('INVALID_COMPONENT_HOLD')
    return parts


def simulation(missing, candidate):
    """Derive a purely lexical future-image *proposal*; never create a link."""
    a, b = components(missing), components(candidate)
    if a[-1] != b[-1] or missing == candidate:
        raise Hold('NAME_OR_IDENTITY_MISMATCH_HOLD')
    parent = '/' + '/'.join(a[:-1]) if len(a) > 1 else '/'
    relative = posixpath.relpath(candidate, parent)
    if relative.startswith('/'):
        raise Hold('RELATIVE_TARGET_HOLD')
    settled = a[:-1].copy()
    ascents = 0
    for part in relative.split('/'):
        if part in ('', '.'):
            continue
        if part == '..':
            if not settled:
                raise Hold('GUEST_ROOT_ESCAPE_HOLD')
            settled.pop()
            ascents += 1
        else:
            settled.append(part)
    if '/' + '/'.join(settled) != candidate:
        raise Hold('SIMULATION_DID_NOT_REACH_CANDIDATE_HOLD')
    return {
        'purely_lexical_simulation_reaches_candidate': True,
        'relative_target_parent_ascents': ascents,
        'relative_target_total_components': len(relative.split('/')),
        'future_image_mapping_kind': 'RELATIVE_SYMLINK_PROPOSAL_ONLY',
        'mapping_runtime_validated': False,
        'mapping_applied': False,
    }


def no_symlink_parent(root, guest):
    parts = components(guest)[:-1]
    cur = root
    for part in parts:
        cur = cur / part
        try:
            kind = cur.lstat().st_mode
        except FileNotFoundError:
            raise Hold('GUEST_PARENT_MISSING_HOLD') from None
        except OSError:
            raise Hold('GUEST_PARENT_IO_HOLD') from None
        if not stat.S_ISDIR(kind):
            raise Hold('GUEST_PARENT_LINK_OR_NONDIR_HOLD')


def absent_leaf(root, guest):
    parts = components(guest)
    no_symlink_parent(root, guest)
    try:
        (root.joinpath(*parts)).lstat()
    except FileNotFoundError:
        return True
    except OSError:
        raise Hold('GUEST_LEAF_IO_HOLD') from None
    raise Hold('GUEST_LEAF_ALREADY_PRESENT_HOLD')


def audit(root, folder, p33):
    if root.is_symlink() or not root.is_dir():
        raise Hold('ROOTFS_DIRECTORY_HOLD')
    try:
        baseline = p33.audit(root, folder, False)
        p26 = p33.import_parent(folder / p33.R3726, p33.R3726)
        p27 = p33.import_parent(folder / p33.R3727, p33.R3727)
        index, sources, nregular, nsymlinks = p27.inventory(root, p26)
    except p33.Hold:
        raise Hold('R3733_PARENT_REPLAY_HOLD') from None
    except p27.Hold:
        raise Hold('R3727_PARENT_REPLAY_HOLD') from None
    required = ('INTERP_SINGLE_MISSING_PATH_LAYOUT_REVIEW_ONLY', 12, 1, 1, 4, 0)
    got = (baseline.get('result'), baseline.get('absent_interpreter_references'),
           baseline.get('distinct_missing_guest_paths'),
           baseline.get('missing_parent_component_count'),
           baseline.get('candidate_parent_component_count'),
           baseline.get('common_parent_components'))
    if got != required or nregular != 1446 or nsymlinks != 335 or len(sources) != 12:
        raise Hold('R3733_BASELINE_OR_LAYOUT_HOLD')
    missing_set = {literal for literal, _hdr in sources}
    if len(missing_set) != 1:
        raise Hold('MISSING_PATH_UNIQUENESS_HOLD')
    missing = next(iter(missing_set))
    names = index.get(missing.rsplit('/', 1)[-1], [])
    candidates = set()
    for source_guest, header in sources:
        if source_guest != missing:
            raise Hold('SOURCE_MISSING_PATH_DIFFERENCE_HOLD')
        hits = []
        for candidate, kind in names:
            if kind != 'regular':
                continue
            g = p33.relative_guest_path(root, candidate)
            cat, hops = p26.classify_guest_target(root, g, header)
            if cat == 'GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE' and hops == 0:
                hits.append(g)
        if len(hits) != 1:
            raise Hold('ONE_CANDIDATE_PER_SOURCE_HOLD')
        candidates.add(hits[0])
    if len(candidates) != 1:
        raise Hold('CANDIDATE_IDENTITY_HOLD')
    candidate = next(iter(candidates))
    no_symlink_parent(root, candidate)
    if not absent_leaf(root, missing):
        raise Hold('MISSING_LEAF_STATUS_HOLD')
    physical = root.joinpath(*components(candidate))
    try:
        if not stat.S_ISREG(physical.lstat().st_mode):
            raise Hold('CANDIDATE_NOT_REGULAR_HOLD')
    except OSError:
        raise Hold('CANDIDATE_FILE_IO_HOLD') from None
    geometry = simulation(missing, candidate)
    return {
        'milestone': 'R40.4.3.7.34',
        'result': 'FUTURE_IMAGE_GUEST_ALIAS_SIMULATION_ONLY',
        'parent_r3733_r3727_r3726_pins_and_counts_replayed': True,
        'source_interpreter_references': 12,
        'distinct_missing_guest_paths': 1,
        'unique_alternate_regular_candidates': 1,
        'missing_leaf_still_absent': True,
        'missing_and_candidate_parent_directories_have_no_symlink_components': True,
        **geometry,
        'stage_file_writes': 0,
        'source_path_strings_exported': False,
        'future_image_mapping_approved': False,
        'runtime_loader_resolved': False,
        'transitive_dependency_closure_proven': False,
        'r26_source_provenance_authenticated': False,
        'historical_hash_membership_reverified': False,
        'boot_authorized': False,
        'prune_authorized': False,
        'immutable_hold': 'NOT_BOOTABLE',
    }


def main():
    parser = argparse.ArgumentParser(description='In-memory guest loader alias simulation; NOT_BOOTABLE')
    parser.add_argument('--rootfs', required=True, type=Path)
    parser.add_argument('--parent-dir', required=True, type=Path)
    args = parser.parse_args()
    try:
        p33 = import_r33(args.parent_dir)
        result = audit(args.rootfs, args.parent_dir, p33)
    except (Hold, OSError) as exc:
        result = {'milestone': 'R40.4.3.7.34', 'result': 'HOLD',
                  'hold_category': exc.category if isinstance(exc, Hold) else 'HOST_IO_HOLD',
                  'boot_authorized': False, 'prune_authorized': False,
                  'immutable_hold': 'NOT_BOOTABLE'}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['result'] == 'FUTURE_IMAGE_GUEST_ALIAS_SIMULATION_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
