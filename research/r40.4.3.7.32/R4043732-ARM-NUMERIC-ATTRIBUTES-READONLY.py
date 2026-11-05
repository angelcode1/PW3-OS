#!/usr/bin/env python3
"""R4043732: read-only numeric Arm attributes for alternate PT_INTERP and 12 sources.

Source-only. Aggregate integer categories, not filename/guest-path strings.
No stage writes, emulation, hardware interaction, execution, boot or pruning.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct

PARENT_NAME = "R4043731-1-ARM-ATTRIBUTES-CORRECTED-READONLY.py"
PARENT_SHA256 = "1ab0dde8a96fad86608b114e5d20902171d7fd4dedb649bff7026e4c1a372dc4"
TARGET_TAGS = {6: "CPU_ARCH", 7: "CPU_ARCH_PROFILE", 9: "THUMB_ISA_USE",
               10: "FP_ARCH", 18: "ABI_PCS_WCHAR_T", 24: "ABI_ALIGN_NEEDED",
               25: "ABI_ALIGN_PRESERVED", 26: "ABI_ENUM_SIZE",
               27: "ABI_HARDFP_USE", 28: "ABI_VFP_ARGS"}
NUMERIC_TAGS = set(range(6, 32)) | {34, 36, 38, 42, 44, 46, 48, 50, 52, 64, 66, 68, 70}
STRING_TAGS = {4, 5, 65, 67}
COMPOUND_TAGS = {32}


class Hold(Exception):
    def __init__(self, category):
        super().__init__(category)
        self.category = category


def pinned_parent(path):
    if path.is_symlink() or not path.is_file() or path.name != PARENT_NAME:
        raise Hold("PARENT_INVALID")
    if hashlib.sha256(path.read_bytes()).hexdigest() != PARENT_SHA256:
        raise Hold("PARENT_SHA_MISMATCH")
    spec = importlib.util.spec_from_file_location("pw3_r3731_1_pinned", path)
    if not spec or not spec.loader:
        raise Hold("PARENT_IMPORT_REFUSED")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_numeric_attributes(raw, endian, parent):
    """Decode bounded known AEABI file tags and return integer tags only."""
    if not raw or raw[:1] != b"A" or endian not in ("<", ">"):
        raise Hold("ATTRIBUTE_MAGIC_OR_ENDIAN_HOLD")
    cursor = 1
    blocks = []
    while cursor < len(raw):
        if cursor + 4 > len(raw):
            raise Hold("ATTRIBUTE_VENDOR_LENGTH_HOLD")
        length, = struct.unpack_from(endian + "I", raw, cursor)
        if length < 10 or length > 65536 or cursor + length > len(raw):
            raise Hold("ATTRIBUTE_VENDOR_BOUNDS_HOLD")
        end = cursor + length
        try:
            vendor, pos = parent.read_cstr(raw, cursor + 4, end)
        except parent.Hold:
            raise Hold("ATTRIBUTE_VENDOR_CSTRING_HOLD") from None
        if vendor != b"aeabi":
            raise Hold("ATTRIBUTE_VENDOR_UNSUPPORTED_HOLD")
        while pos < end:
            begin = pos
            try:
                kind, pos = parent.read_uleb(raw, pos, end)
            except parent.Hold:
                raise Hold("ATTRIBUTE_SUBTAG_HOLD") from None
            if pos + 4 > end:
                raise Hold("ATTRIBUTE_SUBSECTION_LENGTH_HOLD")
            subsection_length, = struct.unpack_from(endian + "I", raw, pos)
            start = pos + 4
            finish = begin + subsection_length  # Arm ADDENDA32: includes tag
            if subsection_length < start - begin or finish > end or finish < start:
                raise Hold("ATTRIBUTE_SUBSECTION_BOUNDS_HOLD")
            if kind == 1:
                blocks.append(raw[start:finish])
            pos = finish
        cursor = end
    if len(blocks) != 1:
        raise Hold("ATTRIBUTE_FILE_BLOCK_COUNT_HOLD")
    data = blocks[0]
    pos = 0
    values = {}
    while pos < len(data):
        try:
            tag, pos = parent.read_uleb(data, pos, len(data))
        except parent.Hold:
            raise Hold("ATTRIBUTE_TAG_LEB_HOLD") from None
        if tag in values:
            raise Hold("ATTRIBUTE_DUPLICATE_TAG_HOLD")
        if tag in NUMERIC_TAGS:
            try:
                number, pos = parent.read_uleb(data, pos, len(data))
            except parent.Hold:
                raise Hold("ATTRIBUTE_NUMERIC_LEB_HOLD") from None
            values[tag] = number
        elif tag in STRING_TAGS:
            try:
                _, pos = parent.read_cstr(data, pos, len(data))
            except parent.Hold:
                raise Hold("ATTRIBUTE_STRING_HOLD") from None
            values[tag] = None
        elif tag in COMPOUND_TAGS:
            try:
                _, pos = parent.read_uleb(data, pos, len(data))
                _, pos = parent.read_cstr(data, pos, len(data))
            except parent.Hold:
                raise Hold("ATTRIBUTE_COMPOUND_HOLD") from None
            values[tag] = None
        else:
            raise Hold("ATTRIBUTE_UNSUPPORTED_TAG_HOLD")
    return {tag: values.get(tag) for tag in TARGET_TAGS}


def read_numeric_tags(parent, parent26, path):
    # Verify parent corrected parser succeeds on exactly this file too.
    if parent.inspect_arm_attributes(parent26, path).get("status") != "ARM_ATTRIBUTES_PRESENT":
        raise Hold("ATTRIBUTE_MISSING_HOLD")
    try:
        with parent26.open_regular_nofollow(path) as f:
            h = parent26.elf_header(f)
            if h is None or h["cls"] != 1 or h["machine"] != 40:
                raise Hold("NOT_ARM32_ELF_HOLD")
            shoff, = struct.unpack(h["endian"] + "I", parent26.read_at(f, 32, 4))
            shsize, nsections, _ = struct.unpack(h["endian"] + "HHH", parent26.read_at(f, 46, 6))
            if shsize != 40 or nsections < 1 or nsections > 16384:
                raise Hold("SECTION_LAYOUT_HOLD")
            if shoff > h["length"] or nsections * shsize > h["length"] - shoff:
                raise Hold("SECTION_BOUNDS_HOLD")
            blocks = []
            for i in range(nsections):
                entry = parent26.read_at(f, shoff + i * shsize, shsize)
                stype, = struct.unpack_from(h["endian"] + "I", entry, 4)
                if stype != 0x70000003:
                    continue
                start, size = struct.unpack_from(h["endian"] + "II", entry, 16)
                if size < 1 or size > 65536 or start > h["length"] or size > h["length"] - start:
                    raise Hold("ARM_ATTRIBUTES_SECTION_BOUNDS_HOLD")
                blocks.append(parent26.read_at(f, start, size))
            if len(blocks) != 1:
                raise Hold("ARM_ATTRIBUTES_SECTION_COUNT_HOLD")
            return parse_numeric_attributes(blocks[0], h["endian"], parent)
    except parent26.Hold:
        raise Hold("PARENT_ELF_IO_HOLD") from None


def summarize(source_attrs, candidate):
    tally = {}
    compare = {}
    for tag, label in TARGET_TAGS.items():
        t = Counter()
        c = Counter()
        value = candidate.get(tag)
        for s in source_attrs:
            v = s.get(tag)
            t["UNDECLARED" if v is None else "VALUE_" + str(v)] += 1
            if value is None or v is None:
                c["ONE_OR_BOTH_UNDECLARED"] += 1
            elif value == v:
                c["NUMERIC_VALUE_EQUAL"] += 1
            else:
                c["NUMERIC_VALUE_DIFFERENT"] += 1
        tally[label] = dict(sorted(t.items()))
        compare[label] = dict(sorted(c.items()))
    return {
        "alternative_numeric_tags": {label: ("UNDECLARED" if candidate.get(tag) is None else "VALUE_" + str(candidate[tag]))
                                     for tag, label in TARGET_TAGS.items()},
        "source_numeric_tag_categories": tally,
        "source_vs_alternative_numeric_relation_counts": compare,
    }


def audit(root, parent_dir, original_r3731, parent):
    if root.is_symlink() or not root.is_dir():
        raise Hold("INVALID_STAGE_ROOT")
    try:
        previous = parent.classify(root, parent_dir, original_r3731)
    except parent.Hold:
        raise Hold("R3731_1_REPLAY_HOLD") from None
    expected = {"ARM_ATTRIBUTES_PRESENT": 12, "VFP_ARGS_UNDECLARED": 12}
    if (previous.get("result") != "ARM_ATTRIBUTES_CORRECTED_STATIC_CLASSIFIED_ONLY"
            or previous.get("source_elf_count") != 12
            or previous.get("source_arm_attribute_categories") != expected
            or previous.get("alternative_arm_attributes", {}).get("abi_vfp_args") != "UNDECLARED"):
        raise Hold("R3731_1_COUNTS_HOLD")
    p30 = parent.verify_import(parent_dir / parent.R30, parent.R30, parent.R30_SHA)
    p29 = p30.load_r29(parent_dir / p30.R29_NAME)
    chain = {name: p29.load_pinned(parent_dir / name) for name in p29.PINNED}
    p26 = chain["R4043726-INTERP-GUEST-RESOLVE-READONLY.py"]
    p27 = chain["R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py"]
    index, sources, regular, symlinks = p27.inventory(root, p26)
    if regular != 1446 or symlinks != 335 or len(sources) != 12 or len({p for p, _ in sources}) != 1:
        raise Hold("R3727_SOURCE_COUNTS_HOLD")
    guest = sources[0][0]
    basename = guest.rsplit("/", 1)[-1]
    candidates = set()
    for literal, hdr in sources:
        matches = [file for file, typ in index.get(basename, [])
                   if typ == "regular" and p26.classify_guest_target(
                       root, "/" + file.relative_to(root).as_posix(), hdr)[0] == "GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE"]
        if literal != guest or len(matches) != 1:
            raise Hold("CANDIDATE_UNIQUENESS_HOLD")
        candidates.add(matches[0])
    if len(candidates) != 1:
        raise Hold("CANDIDATE_IDENTITY_HOLD")
    candidate_tags = read_numeric_tags(parent, p26, next(iter(candidates)))
    source_attrs = []
    for base, dirs, names in os.walk(root, topdown=True, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(base) / d).is_symlink())
        for name in sorted(names):
            path = Path(base) / name
            if path.is_symlink() or not path.is_file():
                continue
            with p26.open_regular_nofollow(path) as f:
                parsed = p26.inspect_elf(f)
            if parsed is not None and any(lit == guest for lit, _ in parsed[1]):
                source_attrs.append(read_numeric_tags(parent, p26, path))
    if len(source_attrs) != 12:
        raise Hold("REQUESTING_ELF_COUNT_HOLD")
    comparison = summarize(source_attrs, candidate_tags)
    return {
        "milestone": "R40.4.3.7.32",
        "result": "ARM_NUMERIC_ATTRIBUTES_RELATION_CLASSIFIED_ONLY",
        "source_elf_count": 12,
        "alternative_elf_count": 1,
        "r3731_1_corrected_parent_sha_pinned": True,
        "r3731_1_and_older_pinned_chain_replayed": True,
        **comparison,
        "numeric_tag_equality_implies_runtime_compatibility": False,
        "arm_kernel_abi_compatibility_proven": False,
        "guest_interpreter_path_resolved": False,
        "runtime_loader_resolved": False,
        "historical_inventory_hashes_reverified": False,
        "original_r26_source_provenance_authenticated": False,
        "transitive_dependency_closure_proven": False,
        "private_paths_or_strings_exported": False,
        "stage_modified": False,
        "boot_authorized": False,
        "prune_authorized": False,
        "immutable_hold": "NOT_BOOTABLE",
    }


def main():
    p = argparse.ArgumentParser(description="Read-only numeric ARM attributes relation audit; NOT_BOOTABLE")
    p.add_argument("--rootfs", type=Path, required=True)
    p.add_argument("--parent-dir", type=Path, required=True)
    p.add_argument("--original-r3731", type=Path, required=True)
    args = p.parse_args()
    try:
        parent = pinned_parent(args.parent_dir / PARENT_NAME)
        result = audit(args.rootfs, args.parent_dir, args.original_r3731, parent)
    except (Hold, OSError) as exc:
        result = {"milestone": "R40.4.3.7.32", "result": "HOLD",
                  "hold_category": exc.category if isinstance(exc, Hold) else "HOST_IO_HOLD",
                  "boot_authorized": False, "prune_authorized": False,
                  "immutable_hold": "NOT_BOOTABLE"}
    print(json.dumps(result, sort_keys=True))
    return 0 if result["result"] == "ARM_NUMERIC_ATTRIBUTES_RELATION_CLASSIFIED_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
