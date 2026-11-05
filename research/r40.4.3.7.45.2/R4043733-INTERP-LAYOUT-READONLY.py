#!/usr/bin/env python3
"""R4043733: source-pinned PT_INTERP location contrast. READONLY; NOT_BOOTABLE.

No stage modifications, no loader execution. By default emits no pathname strings.
--show-local-guest-paths opts in to terminal-only guest path display.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path

R3726 = 'R4043726-INTERP-GUEST-RESOLVE-READONLY.py'
R3727 = 'R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py'
PINS = {
    R3726: '7068af571b0c57677793eb5722938b3a4f14abfd5ce33c6b4e4ce41040e117b3',
    R3727: 'abd04b8af7f66fa0a5fe46ab889c04811eb1c34c984e91857183f87c838ecaaa',
}

class Hold(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def import_parent(path, name):
    if path.name != name or not path.is_file() or path.is_symlink():
        raise Hold('PARENT_INVALID_HOLD')
    if hashlib.sha256(path.read_bytes()).hexdigest() != PINS[name]:
        raise Hold('PARENT_SHA_MISMATCH_HOLD')
    spec = importlib.util.spec_from_file_location('pw3_r3733_' + str(len(name)), path)
    if not spec or not spec.loader:
        raise Hold('PARENT_IMPORT_HOLD')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def relative_guest_path(root, physical):
    """Use lexical paths only, never host symlink resolution."""
    try:
        rel = physical.relative_to(root)
    except ValueError:
        raise Hold('CANDIDATE_OUTSIDE_ROOT_HOLD') from None
    if not rel.parts or any(x in ('', '..', '.') for x in rel.parts):
        raise Hold('CANDIDATE_PATH_COMPONENT_HOLD')
    return '/' + rel.as_posix()


def classify_layout(missing, candidate_guest, *, show_local_paths=False):
    if (not isinstance(missing, str) or not isinstance(candidate_guest, str)
            or not missing.startswith('/') or not candidate_guest.startswith('/')
            or missing == '/' or candidate_guest == '/' or '\x00' in missing
            or '\x00' in candidate_guest or '\\' in missing or '\\' in candidate_guest):
        raise Hold('INVALID_GUEST_PATH_HOLD')
    left, right = missing.split('/')[1:], candidate_guest.split('/')[1:]
    if any(v in ('', '.', '..') for v in left + right):
        raise Hold('INVALID_GUEST_COMPONENT_HOLD')
    if left[-1] != right[-1]:
        raise Hold('BASENAME_DIFFERENT_HOLD')
    if missing == candidate_guest:
        raise Hold('EXPECTED_ABSENT_PATH_NOT_DISTINCT_HOLD')
    relation = 'SAME_PARENT_DIRECTORY' if left[:-1] == right[:-1] else 'DIFFERENT_PARENT_DIRECTORY'
    overlap = 0
    for a, b in zip(left[:-1], right[:-1]):
        if a != b:
            break
        overlap += 1
    result = {
        'missing_parent_vs_candidate_parent': relation,
        'common_parent_components': overlap,
        'missing_parent_component_count': len(left) - 1,
        'candidate_parent_component_count': len(right) - 1,
        'basename_equal': True,
        'requested_guest_path_still_absent': True,
        'potential_future_independent_image_mapping': 'REVIEW_ONLY_NOT_EXECUTED',
        'alias_creation_authorized': False,
        'local_guest_paths_exported': bool(show_local_paths),
    }
    if show_local_paths:
        result['missing_interpreter_guest_path'] = missing
        result['alternative_candidate_guest_path'] = candidate_guest
    return result


def audit(root, parentdir, show_local_paths=False):
    if root.is_symlink() or not root.is_dir() or parentdir.is_symlink() or not parentdir.is_dir():
        raise Hold('ROOT_OR_PARENT_DIRECTORY_INVALID_HOLD')
    p26 = import_parent(parentdir / R3726, R3726)
    p27 = import_parent(parentdir / R3727, R3727)
    try:
        previous = p27.audit(root, p26)
        if (previous.get('result') != 'ABSENT_INTERP_SAME_BASENAME_ALTERNATIVES_CLASSIFIED_ONLY'
            or previous.get('absent_interp_segments') != 12
            or previous.get('distinct_absent_guest_path_literals') != 1
            or previous.get('same_basename_alternative_categories') != {
                'ONE_REGULAR_SAME_BASENAME_ABI_HEADER_CANDIDATE': 12
            }):
            raise Hold('PARENT_REPLAY_MISMATCH_HOLD')
        index, sources, nregular, nlinks = p27.inventory(root, p26)
    except p27.Hold:
        raise Hold('PARENT_REPLAY_OR_INVENTORY_HOLD') from None
    if nregular != 1446 or nlinks != 335 or len(sources) != 12:
        raise Hold('INDEPENDENT_INVENTORY_HOLD')
    missing_set = {guest for guest, _ in sources}
    if len(missing_set) != 1:
        raise Hold('MISSING_GUEST_PATH_UNIQUENESS_HOLD')
    missing = next(iter(missing_set))
    basename = missing.rsplit('/', 1)[-1]
    candidate_set = set()
    for guest, header in sources:
        if guest != missing:
            raise Hold('SOURCE_PATH_INCONSISTENT_HOLD')
        matches = set()
        for path, kind in index.get(basename, []):
            if kind != 'regular':
                continue
            candidate_guest = relative_guest_path(root, path)
            category, _ = p26.classify_guest_target(root, candidate_guest, header)
            if category == 'GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE':
                matches.add(candidate_guest)
        if len(matches) != 1:
            raise Hold('CANDIDATE_NONUNIQUE_HOLD')
        candidate_set.update(matches)
    if len(candidate_set) != 1:
        raise Hold('CANDIDATE_IDENTITY_HOLD')
    candidate = next(iter(candidate_set))
    source_category, _ = p26.classify_guest_target(root, missing, sources[0][1])
    if source_category != 'GUEST_ABSENT_HOLD':
        raise Hold('MISSING_PATH_STATUS_CHANGED_HOLD')
    layout = classify_layout(missing, candidate, show_local_paths=show_local_paths)
    return {
        'milestone': 'R40.4.3.7.33',
        'result': 'INTERP_SINGLE_MISSING_PATH_LAYOUT_REVIEW_ONLY',
        'parent_r3726_and_r3727_sha_pins_verified': True,
        'parent_r3727_baseline_and_counts_replayed': True,
        'absent_interpreter_references': 12,
        'distinct_missing_guest_paths': 1,
        'unique_compatible_alternative_elfs': 1,
        **layout,
        'runtime_loader_resolved': False,
        'full_abi_compatibility_proven': False,
        'r26_source_provenance_authenticated': False,
        'rootfs_stage_modified': False,
        'boot_authorized': False,
        'prune_authorized': False,
        'firmware_write_authorized': False,
        'immutable_hold': 'NOT_BOOTABLE',
    }


def main():
    ap = argparse.ArgumentParser(description='Read-only guest interpreter layout comparison; NOT_BOOTABLE')
    ap.add_argument('--rootfs', required=True, type=Path)
    ap.add_argument('--parent-dir', required=True, type=Path)
    ap.add_argument('--show-local-guest-paths', action='store_true',
                    help='Opt in to printing guest path literals only on the local terminal')
    args = ap.parse_args()
    try:
        result = audit(args.rootfs, args.parent_dir, args.show_local_guest_paths)
    except (Hold, OSError) as e:
        result = {'milestone': 'R40.4.3.7.33', 'result': 'HOLD',
                  'hold_category': e.code if isinstance(e, Hold) else 'HOST_IO_HOLD',
                  'boot_authorized': False, 'prune_authorized': False,
                  'immutable_hold': 'NOT_BOOTABLE'}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['result'] == 'INTERP_SINGLE_MISSING_PATH_LAYOUT_REVIEW_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
