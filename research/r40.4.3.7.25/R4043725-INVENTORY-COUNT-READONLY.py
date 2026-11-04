#!/usr/bin/env python3
"""Independent staged-rootfs inode-type inventory; NO BOOT, NO PRUNE."""
import argparse
import json
import os
import stat
from collections import Counter
from pathlib import Path


class Hold(Exception):
    pass


def _kind(mode):
    if stat.S_ISREG(mode):
        return "regular_files"
    if stat.S_ISDIR(mode):
        return "directories"
    if stat.S_ISLNK(mode):
        return "symlinks"
    return "other_nodes"


def _classify_link(path, out):
    # Read the link's literal text only; never follow it in the host filesystem.
    target = os.readlink(path)
    if target.startswith("/"):
        out["absolute_symlink_literals"] += 1
    else:
        out["relative_symlink_literals"] += 1
    if ".." in target.split("/"):
        out["symlinks_with_parent_components"] += 1


def scan_scandir(root):
    out = Counter()
    stack = [root]
    while stack:
        base = stack.pop()
        with os.scandir(base) as it:
            entries = sorted(it, key=lambda e: e.name)
        for entry in entries:
            info = entry.stat(follow_symlinks=False)
            kind = _kind(info.st_mode)
            out[kind] += 1
            if kind == "directories":
                stack.append(Path(entry.path))
            elif kind == "symlinks":
                _classify_link(entry.path, out)
    return out


def scan_walk(root):
    out = Counter()

    def onerror(exc):
        raise Hold("walk_io_error") from exc

    for base, dirs, filenames in os.walk(root, topdown=True, followlinks=False, onerror=onerror):
        for name in dirs + filenames:
            path = Path(base) / name
            info = path.lstat()
            kind = _kind(info.st_mode)
            out[kind] += 1
            if kind == "symlinks":
                _classify_link(path, out)
    return out


def audit(root, expected_regular):
    if root.is_symlink() or not root.is_dir():
        raise Hold("stage_root_missing_or_symlink")
    a = scan_scandir(root)
    b = scan_walk(root)
    equal = a == b
    gap = a["regular_files"] - expected_regular
    return {
        "milestone": "R40.4.3.7.25",
        "result": "STANDALONE_INVENTORY_COUNTS_MATCH" if equal and gap == 0 else "INVENTORY_COUNT_GAP_HOLD",
        "expected_prior_regular_files": expected_regular,
        "current_regular_files": a["regular_files"],
        "prior_baseline_delta": gap,
        "independent_scanners_agree": equal,
        "lstat_inode_type_counts": {k: a[k] for k in ("regular_files", "directories", "symlinks", "other_nodes")},
        "symlink_literal_summary": {k: a[k] for k in (
            "absolute_symlink_literals", "relative_symlink_literals",
            "symlinks_with_parent_components")},
        "historic_inventory_membership_compared": False,
        "source_provenance_authenticated": False,
        "interp_runtime_resolved": False,
        "dependency_closure_proven": False,
        "boot_authorized": False,
        "prune_authorized": False,
        "immutable_hold": "NOT_BOOTABLE",
    }


def main():
    ap = argparse.ArgumentParser(description="Read-only staged-rootfs type counts; NOT_BOOTABLE")
    ap.add_argument("--stage-root", type=Path, required=True)
    ap.add_argument("--expected-regular-files", type=int, default=1448)
    args = ap.parse_args()
    if args.expected_regular_files < 0:
        ap.error("expected-regular-files must be nonnegative")
    try:
        result = audit(args.stage_root, args.expected_regular_files)
    except (Hold, OSError):
        result = {"milestone": "R40.4.3.7.25", "result": "HOLD_INVENTORY_SCAN_ERROR",
                  "boot_authorized": False, "prune_authorized": False,
                  "immutable_hold": "NOT_BOOTABLE"}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["result"] == "STANDALONE_INVENTORY_COUNTS_MATCH" else 2


if __name__ == "__main__":
    raise SystemExit(main())
