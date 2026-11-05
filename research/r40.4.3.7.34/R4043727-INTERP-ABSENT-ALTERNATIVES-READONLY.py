#!/usr/bin/env python3
"""R4043727: classify absent PT_INTERP guest-path alternatives; NOT_BOOTABLE.

Uses the SHA-pinned, unchanged R4043726 scanner from the user's existing
Downloads folder. Does not write to the stage, execute any ELF, or print paths.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat

PARENT_BASENAME = "R4043726-INTERP-GUEST-RESOLVE-READONLY.py"
PARENT_SHA256 = "7068af571b0c57677793eb5722938b3a4f14abfd5ce33c6b4e4ce41040e117b3"
EXPECTED = {"rootfs_regular_files": 1446, "elf_objects": 83,
            "interp_segments": 19, "strict_literal": 9, "padding_only_literal": 10}
EXPECTED_PATHS = {"GUEST_ABSENT_HOLD": 12,
                  "GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE": 7}


class Hold(Exception):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def verify_parent(path):
    if path.is_symlink() or not path.is_file() or path.name != PARENT_BASENAME:
        raise Hold("PARENT_FILE_INVALID")
    # Pin before importing (parent source is locally supplied executable Python).
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != PARENT_SHA256:
        raise Hold("PARENT_SHA256_MISMATCH")
    spec = importlib.util.spec_from_file_location("pw3_r3726_pinned", path)
    if spec is None or spec.loader is None:
        raise Hold("PARENT_MODULE_LOAD_REFUSED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verified_baseline(root, parent):
    if root.is_symlink() or not root.is_dir():
        raise Hold("ROOTFS_INVALID")
    previous = parent.scan(root, EXPECTED["rootfs_regular_files"])
    if previous.get("result") != "STATIC_INTERP_GUEST_PATH_CLASSIFICATION_ONLY":
        raise Hold("PARENT_BASELINE_HOLD")
    if previous.get("counts") != EXPECTED or previous.get("source_parse_holds"):
        raise Hold("PARENT_COUNTS_HOLD")
    if previous.get("path_resolution_counts") != EXPECTED_PATHS:
        raise Hold("PARENT_PATH_COUNTS_HOLD")
    return previous


def inventory(root, parent):
    """Return basename index and source PT_INTERP list, kept private in memory."""
    names = defaultdict(list)
    sources = []
    regular_count = 0
    seen_symlinks = 0

    def onerror(_):
        raise Hold("HOST_WALK_HOLD")

    for base, directories, files in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
        # Symlinked directories must appear in the alias index, but not be walked.
        for name in list(directories):
            path = Path(base) / name
            try:
                mode = path.lstat().st_mode
            except OSError:
                raise Hold("HOST_LSTAT_HOLD") from None
            if stat.S_ISLNK(mode):
                names[name].append((path, "link"))
                seen_symlinks += 1
                directories.remove(name)
            elif not stat.S_ISDIR(mode):
                raise Hold("HOST_UNEXPECTED_DIRECTORY_TYPE")
        directories.sort()
        for name in sorted(files):
            path = Path(base) / name
            try:
                mode = path.lstat().st_mode
            except OSError:
                raise Hold("HOST_LSTAT_HOLD") from None
            if stat.S_ISLNK(mode):
                names[name].append((path, "link"))
                seen_symlinks += 1
            elif stat.S_ISREG(mode):
                regular_count += 1
                names[name].append((path, "regular"))
                try:
                    with parent.open_regular_nofollow(path) as stream:
                        parsed = parent.inspect_elf(stream)
                except parent.Hold:
                    raise Hold("PARENT_ELF_PARSE_HOLD") from None
                if parsed is not None:
                    hdr, segments = parsed
                    for literal, _padded in segments:
                        resolution, _links = parent.classify_guest_target(root, literal, hdr)
                        if resolution == "GUEST_ABSENT_HOLD":
                            sources.append((literal, hdr))
                        elif resolution != "GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE":
                            raise Hold("UNEXPECTED_INTERP_STATUS")
            else:
                raise Hold("UNEXPECTED_SPECIAL_FILE")
    if regular_count != EXPECTED["rootfs_regular_files"] or len(sources) != EXPECTED_PATHS["GUEST_ABSENT_HOLD"]:
        raise Hold("INDEPENDENT_REPLAY_HOLD")
    return names, sources, regular_count, seen_symlinks


def candidate_category(root, name_index, literal, header, parent):
    """Classify one missing PT_INTERP by *same basename* in alternate paths.

    No candidate is interpreted as the actual kernel-selected interpreter.
    """
    basename = literal.rsplit("/", 1)[-1]
    entries = name_index.get(basename, ())
    compatible_regular = 0
    compatible_symlink = 0
    incompatible = 0
    other = 0
    for path, typ in entries:
        # Convert physical path to guest path without ever dereferencing host links.
        guest = "/" + path.relative_to(root).as_posix()
        status, _hops = parent.classify_guest_target(root, guest, header)
        if status == "GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE":
            if typ == "regular":
                compatible_regular += 1
            else:
                compatible_symlink += 1
        elif status in ("GUEST_ELF_ABI_HEADER_MISMATCH_HOLD", "GUEST_ELF_TYPE_HOLD"):
            incompatible += 1
        else:
            other += 1
    compatible = compatible_regular + compatible_symlink
    if compatible > 1:
        classification = "MULTIPLE_SAME_BASENAME_ABI_HEADER_CANDIDATES"
    elif compatible_regular == 1:
        classification = "ONE_REGULAR_SAME_BASENAME_ABI_HEADER_CANDIDATE"
    elif compatible_symlink == 1:
        classification = "ONE_SYMLINK_SAME_BASENAME_ABI_HEADER_CANDIDATE"
    elif incompatible:
        classification = "SAME_BASENAME_ONLY_INCOMPATIBLE_ELF_HEADER"
    elif entries:
        classification = "SAME_BASENAME_ONLY_NONMATCHING_OR_UNRESOLVED"
    else:
        classification = "NO_SAME_BASENAME_IN_STAGE"
    return classification, compatible_regular, compatible_symlink, len(entries)


def audit(root, parent):
    verified_baseline(root, parent)
    index, records, nregular, nlinks = inventory(root, parent)
    classes = Counter()
    aliases = Counter()
    unique_paths = set()
    unique_basenames = set()
    for literal, hdr in records:
        category, regular, link, entry_count = candidate_category(root, index, literal, hdr, parent)
        classes[category] += 1
        aliases["same_basename_regular_abi_header_candidate_entries"] += regular
        aliases["same_basename_symlink_abi_header_candidate_entries"] += link
        if entry_count:
            aliases["absent_segments_with_any_same_basename_entries"] += 1
        unique_paths.add(literal)
        unique_basenames.add(literal.rsplit("/", 1)[-1])
    return {
        "milestone": "R40.4.3.7.27",
        "result": "ABSENT_INTERP_SAME_BASENAME_ALTERNATIVES_CLASSIFIED_ONLY",
        "parent_r3726_sha256_verified": True,
        "parent_r3726_baseline_replayed": True,
        "parent_r3726_path_counts_replayed": True,
        "rootfs_regular_files": nregular,
        "rootfs_symlink_entries_seen": nlinks,
        "absent_interp_segments": len(records),
        "distinct_absent_guest_path_literals": len(unique_paths),
        "distinct_absent_basename_literals": len(unique_basenames),
        "same_basename_alternative_categories": dict(sorted(classes.items())),
        "same_basename_candidate_entry_counts": dict(sorted(aliases.items())),
        "private_path_or_symlink_strings_exported": False,
        "missing_guest_paths_resolved": False,
        "original_r26_source_provenance_authenticated": False,
        "historical_inventory_membership_reverified": False,
        "runtime_loader_resolved": False,
        "transitive_dependency_closure_proven": False,
        "boot_authorized": False,
        "prune_authorized": False,
        "immutable_hold": "NOT_BOOTABLE",
    }


def main():
    ap = argparse.ArgumentParser(description="Read-only PT_INTERP absent-path alternatives; NOT_BOOTABLE")
    ap.add_argument("--rootfs", type=Path, required=True)
    ap.add_argument("--parent-script", type=Path,
                    default=Path.home() / "Downloads/pw3-r3726" / PARENT_BASENAME)
    args = ap.parse_args()
    try:
        parent = verify_parent(args.parent_script)
        result = audit(args.rootfs, parent)
    except (Hold, OSError) as exc:
        result = {
            "milestone": "R40.4.3.7.27",
            "result": "HOLD",
            "hold_category": exc.category if isinstance(exc, Hold) else "HOST_IO_HOLD",
            "boot_authorized": False,
            "prune_authorized": False,
            "immutable_hold": "NOT_BOOTABLE",
        }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["result"] == "ABSENT_INTERP_SAME_BASENAME_ALTERNATIVES_CLASSIFIED_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
