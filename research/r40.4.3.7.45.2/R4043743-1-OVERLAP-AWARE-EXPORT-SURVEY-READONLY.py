#!/usr/bin/env python3
"""R3743.1: safely classify source/provider overlap, then scan other ELF exports.

A source (PT_INTERP requester) and a direct provider (DT_NEEDED candidate) may
be the same stage file. This wrapper keeps the original R3743 source immutable,
SHA-pins it and its historical HOLD, and counts overlapping files while
excluding the *union* of both sets from the additional-ELF survey.

Read-only source research. No guest paths, symbols or version strings exported.
No source stage writes, alias, loader execution, QEMU, firmware, boot or pruning.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat

ORIGINAL = 'R4043743-STAGED-ELF-WEAK-EXPORT-SURVEY-READONLY.py'
ORIGINAL_SHA256 = 'be4ec4c3557073ece8016fdf395a6142687a32876cd680cd0ff71559e13cc34a'


class Hold(Exception):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def load_original(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_INVALID_HOLD')
    path = folder / ORIGINAL
    if path.name != ORIGINAL or path.is_symlink() or not path.is_file():
        raise Hold('ORIGINAL_R3743_SOURCE_INVALID_HOLD')
    if hashlib.sha256(path.read_bytes()).hexdigest() != ORIGINAL_SHA256:
        raise Hold('ORIGINAL_R3743_SOURCE_SHA_HOLD')
    spec = importlib.util.spec_from_file_location('pw3_original_r3743_preserved', path)
    if spec is None or spec.loader is None:
        raise Hold('ORIGINAL_R3743_IMPORT_HOLD')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def overlap_aware_inventory(root, p26, sourcefiles, providerfiles, parser, old):
    """Same read-only scan as R3743, excluding union of sets, not rejecting overlap.

    A file can be both source and provider. It is still excluded from the
    'additional' inventory exactly once; counted, never interpreted as a
    provider resolving its own undefined symbols.
    """
    sourceset = set(sourcefiles)
    providerset = set(providerfiles)
    overlap = sourceset & providerset
    if not sourceset or not providerset:
        raise Hold('SOURCE_OR_PROVIDER_SET_EMPTY_HOLD')
    if len(sourceset) != len(sourcefiles) or len(providerset) != len(providerfiles):
        raise Hold('SOURCE_OR_PROVIDER_DUPLICATE_HOLD')
    if len(sourceset) != 12 or len(providerset) != 6:
        raise Hold('SOURCE_PROVIDER_COUNT_CHANGED_HOLD')
    if not overlap:
        # The user's original R3743 HOLD reported overlap; fail closed if
        # rerunning on a different stage or unfaithful source inventory.
        raise Hold('ORIGINAL_SOURCE_PROVIDER_OVERLAP_NOT_REPRODUCED_HOLD')
    excluded = sourceset | providerset
    for p in excluded:
        if p.is_symlink() or not p.is_file():
            raise Hold('SOURCE_PROVIDER_REGULAR_FILE_CHANGED_HOLD')
        try:
            p.relative_to(root)
        except ValueError:
            raise Hold('SOURCE_PROVIDER_OUTSIDE_ROOT_HOLD') from None
    exports = defaultdict(set)
    counts = Counter({
        'source_provider_overlap_regular_files': len(overlap),
        'excluded_unique_source_or_provider_regular_files': len(excluded),
    })
    pathcount = 0
    for base, dirs, names in os.walk(root, topdown=True, followlinks=False):
        dirs[:] = sorted(n for n in dirs if not (Path(base) / n).is_symlink())
        for n in sorted(names):
            p = Path(base) / n
            mode = p.lstat().st_mode
            if not stat.S_ISREG(mode) or p in excluded:
                continue
            pathcount += 1
            counts['other_regular_stage_files_seen'] += 1
            if pathcount > 200000:
                raise Hold('STAGE_ENUMERATION_BOUNDS_HOLD')
            kind = old.probe_arm32_dynamic(p26, p)
            if kind == 'NOT_ARM32':
                continue
            counts['additional_arm_elf_files_seen'] += 1
            if kind == 'ARM_NO_DYNAMIC':
                counts['additional_arm_elf_without_dynamic'] += 1
                continue
            counts['additional_arm_elf_with_dynamic'] += 1
            if counts['additional_arm_elf_with_dynamic'] > old.MAX_ADDITIONAL_ELFS:
                raise Hold('ADDITIONAL_DYNAMIC_ELF_LIMIT_HOLD')
            try:
                obj = parser(p)
            except Exception as exc:
                if not isinstance(exc, (OSError, old.Hold, *parser.hold_types)):
                    raise
                counts['additional_dynamic_elf_parser_refusals'] += 1
                continue
            counts['additional_dynamic_elf_parsed'] += 1
            for name in old.exported_names(obj['symbols']):
                exports[name].add(p)
    return exports, dict(sorted(counts.items()))


def audit(root, folder, old):
    if root.is_symlink() or not root.is_dir():
        raise Hold('ROOTFS_DIR_HOLD')
    r42 = old.load_pinned_parent(folder)
    try:
        p11 = r42.load_parent(folder)
        baseline = r42.audit(root, folder, p11)
    except (r42.Hold, OSError):
        raise Hold('R3742_PINNED_REPLAY_HOLD') from None
    if (baseline.get('result') != 'UNDEFINED_WEAK_LOCAL_VERSION_RELOCATION_CONTEXT_STATIC_ONLY'
            or baseline.get('local_index_weak_symbol_entries') != 42
            or baseline.get('local_index_weak_relocation_sites') != 58
            or baseline.get('no_staged_provider_name_entries') != 2
            or baseline.get('source_elf_count') != 12
            or baseline.get('provider_elf_count') != 6
            or baseline.get('local_index_weak_relocation_type_counts') != {'21': 42, '22': 16}
            or baseline.get('no_staged_provider_name_symbol_categories') != {'GNU_VERSION_INDEX_1': 2, 'STB_2': 2, 'TYPE_0': 2}
            or baseline.get('local_index_weak_relocation_context_categories', {}).get('LOCAL_NAME_ZERO_PROVIDER') != 33
            or baseline.get('local_index_weak_relocation_context_categories', {}).get('LOCAL_NAME_ONE_PROVIDER') != 9):
        raise Hold('R3742_USER_MAC_BASELINE_HOLD')
    original41 = p11.load_original(folder)
    p40 = original41.load_parent(folder)
    p26, sourcefiles, providerfiles = original41.locate_sources_providers(root, folder, p40)
    sourceobjs = [original41.parse_version_file(p26, p40, p) for p in sourcefiles]
    providerobjs = [original41.parse_version_file(p26, p40, p) for p in providerfiles]
    targets = old.missing_weak_targets(sourceobjs, providerobjs)

    def read_provider(p):
        return p40.parse_dynamic_and_sections(p26, p)
    read_provider.hold_types = (p40.Hold, p26.Hold)
    exports, counts = overlap_aware_inventory(root, p26, sourcefiles, providerfiles, read_provider, old)
    info = old.compare_extra_targets(targets, sourceobjs, exports, counts)
    return {
        'milestone': 'R40.4.3.7.43.1',
        'result': 'OVERLAP_AWARE_ADDITIONAL_WEAK_EXPORT_NAME_REVIEW_ONLY',
        'original_r3743_sha_pinned_and_original_overlap_hold_preserved': True,
        'parent_r3742_source_sha_pinned_and_replayed': True,
        'prior_source_pins_inherited': True,
        'source_elf_count': 12,
        'initial_provider_elf_count': 6,
        'source_provider_overlap_regular_files': counts['source_provider_overlap_regular_files'],
        'excluded_unique_source_or_provider_regular_files': counts['excluded_unique_source_or_provider_regular_files'],
        **info,
        'overlap_is_not_runtime_symbol_resolution': True,
        'complete_dynamic_loader_namespace_verified': False,
        'symbol_version_resolution_verified': False,
        'weak_runtime_semantics_verified': False,
        'guest_interpreter_path_resolved': False,
        'mapping_applied': False,
        'runtime_tls_compatibility_verified': False,
        'transitive_dependency_closure_proven': False,
        'original_r26_source_provenance_authenticated': False,
        'historical_inventory_hashes_reverified': False,
        'stage_modified': False,
        'paths_symbols_versions_exported': False,
        'boot_authorized': False,
        'prune_authorized': False,
        'firmware_write_authorized': False,
        'immutable_hold': 'NOT_BOOTABLE',
    }


def main():
    ap = argparse.ArgumentParser(description='R3743.1 overlap-aware read-only weak export name survey; NOT_BOOTABLE')
    ap.add_argument('--rootfs', required=True, type=Path)
    ap.add_argument('--parent-dir', required=True, type=Path)
    args = ap.parse_args()
    try:
        result = audit(args.rootfs, args.parent_dir, load_original(args.parent_dir))
    except (Hold, OSError, RecursionError) as exc:
        result = {
            'milestone': 'R40.4.3.7.43.1', 'result': 'HOLD',
            'hold_category': exc.category if isinstance(exc, Hold) else 'HOST_IO_OR_GRAPH_HOLD',
            'boot_authorized': False, 'prune_authorized': False,
            'immutable_hold': 'NOT_BOOTABLE',
        }
    except Exception:
        # Unknown parent or ELF parser failures are never a classification PASS.
        # Avoid emitting file paths or source strings in an exception traceback.
        result = {
            'milestone': 'R40.4.3.7.43.1', 'result': 'HOLD',
            'hold_category': 'UNEXPECTED_PARENT_OR_ELF_PARSER_HOLD',
            'boot_authorized': False, 'prune_authorized': False,
            'immutable_hold': 'NOT_BOOTABLE',
        }
    print(json.dumps(result, sort_keys=True))
    return 0 if result['result'] == 'OVERLAP_AWARE_ADDITIONAL_WEAK_EXPORT_NAME_REVIEW_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
