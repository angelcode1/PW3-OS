#!/usr/bin/env python3
"""R3741.1: preserve original R3741 HOLD; classify VERSYM=0 as review.

Source-only GNU ELF32 ARM symbol-version triage. SHA-pinned original R3741
and all predecessor sources; stage files are read without executing an ELF.
No filenames, guest paths, ELF strings, symbols, version names or symbol bytes
are emitted. A local version index is unresolved, NEVER an acceptable match.
This audit never resolves symbols, applies an alias, edits the rootfs or boots.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path

ORIGINAL = 'R4043741-GNU-SYMBOL-VERSION-CANDIDATES-READONLY.py'
ORIGINAL_SHA256 = 'd598134eb1709be0a8b0729834ee6bfe837663f2aabb4341b73aaa46b6e86e69'

class Hold(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def load_original(folder):
    if folder.is_symlink() or not folder.is_dir():
        raise Hold('PARENT_DIRECTORY_HOLD')
    source = folder / ORIGINAL
    if source.is_symlink() or not source.is_file():
        raise Hold('ORIGINAL_R3741_SOURCE_MISSING_HOLD')
    if hashlib.sha256(source.read_bytes()).hexdigest() != ORIGINAL_SHA256:
        raise Hold('ORIGINAL_R3741_SOURCE_SHA_HOLD')
    spec = importlib.util.spec_from_file_location('pw3_r3741_original_pinned', source)
    if spec is None or spec.loader is None:
        raise Hold('ORIGINAL_R3741_IMPORT_HOLD')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def classify_with_local_review(sources, providers):
    """Return numerical review categories. Local index cannot resolve.

    Preserve R3741's version-name semantics for all nonlocal references,
    but isolate VERSYM index 0 before any version/provider matching.
    """
    names = defaultdict(list)
    for provider in providers:
        if len(provider['symbols']) != len(provider['versym']):
            raise Hold('PROVIDER_VERSYM_LENGTH_HOLD')
        for i, sym in enumerate(provider['symbols']):
            if sym['defined'] and sym['name'] and sym['binding'] in (1, 2, 10) and sym['visibility'] in (0, 3):
                raw = provider['versym'][i]
                idx = raw & 0x7fff
                if idx > 1 and idx not in provider['verdef']:
                    raise Hold('PROVIDER_VERSION_DEFINITION_MISSING_HOLD')
                names[sym['name']].append((idx, bool(raw & 0x8000), provider['verdef'].get(idx)))
    categories = Counter()
    requirements = Counter()
    local_binding = Counter()
    local_types = Counter()
    seen = 0
    refnames = set()
    versions = set()
    local_count = 0
    local_hidden = 0
    local_empty = 0
    for source in sources:
        if len(source['symbols']) != len(source['versym']):
            raise Hold('SOURCE_VERSYM_LENGTH_HOLD')
        for index in sorted(source['referenced_indices']):
            if index <= 0 or index >= len(source['symbols']):
                raise Hold('SOURCE_DYNSYM_INDEX_HOLD')
            sym = source['symbols'][index]
            if sym['defined']:
                continue
            seen += 1
            name = sym['name']
            if name:
                refnames.add(name)
            raw = source['versym'][index]
            idx = raw & 0x7fff
            if idx == 0:
                # In a GNU versym table, 0 means LOCAL, not unversioned.
                # Never count this as a resolved or version-name matching symbol.
                local_count += 1
                local_hidden += bool(raw & 0x8000)
                binding = sym['binding']
                local_binding[({0:'STB_LOCAL', 1:'STB_GLOBAL', 2:'STB_WEAK'}.get(binding, 'STB_OTHER'))] += 1
                local_types[str(sym.get('type', -1))] += 1
                if not name:
                    local_empty += 1
                    categories['LOCAL_VERSION_INDEX_EMPTY_NAME_REVIEW'] += 1
                else:
                    categories['UNDEFINED_LOCAL_VERSION_INDEX_REVIEW'] += 1
                requirements['LOCAL_VERSION_INDEX_REQUIRES_REVIEW'] += 1
                continue
            if not name:
                raise Hold('UNDEFINED_EMPTY_NAME_NONLOCAL_HOLD')
            if idx > 1:
                req = source['verneed'].get(idx)
                if req is None:
                    raise Hold('REQUEST_VERSION_REQUIREMENT_MISSING_HOLD')
                required = req['version']
                versions.add(required)
                requirements['EXPLICIT_GNU_VERSION_REQUIREMENT'] += 1
            else:
                required = None
                requirements['UNVERSIONED_OR_GLOBAL_REFERENCE'] += 1
            options = names.get(name, [])
            if not options:
                categories['NO_STAGED_PROVIDER_NAME_CANDIDATE'] += 1
            elif required is not None:
                exact = sum(1 for vi, hidden, vername in options if vi > 1 and vername == required)
                if exact == 0:
                    categories['NAME_CANDIDATE_BUT_NO_EQUAL_GNU_VERSION_NAME'] += 1
                elif exact == 1:
                    categories['ONE_GNU_VERSION_NAME_MATCHING_CANDIDATE'] += 1
                else:
                    categories['MULTIPLE_GNU_VERSION_NAME_MATCHING_CANDIDATES'] += 1
            else:
                available = sum(1 for vi, hidden, vername in options if vi <= 1 or not hidden)
                if available == 0:
                    categories['ONLY_NONDEFAULT_VERSIONED_NAME_CANDIDATES'] += 1
                elif available == 1:
                    categories['ONE_DEFAULT_OR_UNVERSIONED_NAME_CANDIDATE'] += 1
                else:
                    categories['MULTIPLE_DEFAULT_OR_UNVERSIONED_NAME_CANDIDATES'] += 1
    if seen != sum(categories.values()) or seen != sum(requirements.values()):
        raise Hold('VERSION_CLASSIFICATION_ACCOUNTING_HOLD')
    return {
        'referenced_undefined_entries_reclassified': seen,
        'distinct_undefined_names_reverified': len(refnames),
        'distinct_required_version_names_in_memory': len(versions),
        'source_symbol_version_requirement_categories': dict(sorted(requirements.items())),
        'version_filtered_static_candidate_categories': dict(sorted(categories.items())),
        'local_version_index_review': {
            'unresolved_referenced_undefined_entries': local_count,
            'binding_categories': dict(sorted(local_binding.items())),
            'symbol_type_numeric_categories': dict(sorted(local_types.items())),
            'hidden_bit_set': local_hidden,
            'empty_symbol_name_entries': local_empty,
            'remains_unresolved': bool(local_count),
        },
        'local_version_index_zero_is_never_counted_as_resolved': True,
        'version_name_equality_is_not_runtime_resolution': True,
    }


def audit(root, folder, original):
    if root.is_symlink() or not root.is_dir():
        raise Hold('ROOTFS_INVALID_HOLD')
    # Reuse the exact SHA-pinned R3741 ELF version record and source parsing.
    # R3741.audit itself is intentionally NOT called: its historical zero-index
    # gate remains preserved; R3741.1 classifies the gate without weakening it.
    try:
        p40 = original.load_parent(folder)
        prev = p40.audit(root, folder, p40.import_parent(folder))
    except p40.Hold:
        raise Hold('R3740_PARENT_REPLAY_HOLD') from None
    expected = {'MULTIPLE_STAGED_PROVIDER_NAME_CANDIDATES':80,
                'NO_STAGED_PROVIDER_NAME_CANDIDATE':35,
                'ONE_STAGED_PROVIDER_NAME_CANDIDATE':517}
    if (prev.get('result') != 'STAGED_SYMBOL_NAME_CANDIDATES_AND_VERSION_TAGS_STATIC_ONLY'
        or prev.get('source_elf_count') != 12 or prev.get('provider_elf_count') != 6
        or prev.get('referenced_undefined_dynsym_entries') != 632
        or prev.get('referenced_defined_or_special_dynsym_entries') != 145
        or prev.get('distinct_referenced_undefined_symbol_names') != 369
        or prev.get('undefined_symbol_candidate_categories') != expected):
        raise Hold('R3740_STABLE_BASELINE_HOLD')
    try:
        p26, sourcefiles, providerfiles = original.locate_sources_providers(root, folder, p40)
        sources = [original.parse_version_file(p26, p40, p) for p in sourcefiles]
        providers = [original.parse_version_file(p26, p40, p) for p in providerfiles]
    except (p40.Hold, original.Hold) as exc:
        raise Hold('PINNED_FILE_OR_GNU_VERSION_PARSE_HOLD') from None
    summary = classify_with_local_review(sources, providers)
    if summary['referenced_undefined_entries_reclassified'] != 632 or summary['distinct_undefined_names_reverified'] != 369:
        raise Hold('SYMBOL_BASELINE_DIFFERENT_HOLD')
    if summary['local_version_index_review']['unresolved_referenced_undefined_entries'] < 1:
        # The supplied R3741 HOLD requires at least one original local index.
        raise Hold('ORIGINAL_HOLD_NOT_REPRODUCED_HOLD')
    return {
        'milestone': 'R40.4.3.7.41.1',
        'result': 'GNU_VERSION_LOCAL_INDEX_REVIEW_STATIC_ONLY',
        'original_r3741_sha_pinned_and_original_hold_preserved': True,
        'r3740_and_prior_sha_pins_replayed': True,
        'source_elf_count': 12,
        'provider_elf_count': 6,
        **summary,
        'local_index_runtime_semantics_verified': False,
        'version_aware_symbol_resolution_verified': False,
        'actual_loader_search_and_interposition_verified': False,
        'tls_runtime_compatibility_verified': False,
        'guest_interpreter_path_resolved': False,
        'mapping_applied': False,
        'transitive_dependency_closure_proven': False,
        'original_source_provenance_authenticated': False,
        'historical_inventory_hashes_reverified': False,
        'stage_modified': False,
        'paths_symbols_or_versions_exported': False,
        'boot_authorized': False,
        'prune_authorized': False,
        'firmware_write_authorized': False,
        'immutable_hold': 'NOT_BOOTABLE',
    }


def main():
    ap = argparse.ArgumentParser(description='Read-only local-version-index triage; NOT_BOOTABLE')
    ap.add_argument('--rootfs', type=Path, required=True)
    ap.add_argument('--parent-dir', type=Path, required=True)
    args = ap.parse_args()
    try:
        original = load_original(args.parent_dir)
        result = audit(args.rootfs, args.parent_dir, original)
    except (Hold, OSError, RecursionError) as exc:
        result = {'milestone': 'R40.4.3.7.41.1', 'result': 'HOLD',
                  'hold_category': exc.code if isinstance(exc, Hold) else 'HOST_IO_OR_GRAPH_HOLD',
                  'boot_authorized': False, 'prune_authorized': False,
                  'immutable_hold': 'NOT_BOOTABLE'}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['result'] == 'GNU_VERSION_LOCAL_INDEX_REVIEW_STATIC_ONLY' else 2


if __name__ == '__main__':
    raise SystemExit(main())
