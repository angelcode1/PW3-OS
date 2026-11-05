#!/usr/bin/env python3
"""Offline ARM ELF attributes audit for the single alternative PT_INTERP.

R4043731: read-only, aggregate-only. Never execute ELF, write stage, access
physical PW3, boot, flash, enable network services, or authorize pruning.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import struct

R30 = "R4043730-INTERP-ABI-SONAME-READONLY.py"
R30_SHA = "980fbe08f23e136a21287f562f9732b8297bfd226f2ec8adb68ef639c66f2741"


class Hold(Exception):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def verify_import(path, expected_name, digest):
    if path.name != expected_name or path.is_symlink() or not path.is_file():
        raise Hold("PINNED_PARENT_INVALID")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise Hold("PINNED_PARENT_HASH_MISMATCH")
    spec = importlib.util.spec_from_file_location("pw3_r3731_parent_" + path.stem.replace('-', '_'), path)
    if not spec or not spec.loader:
        raise Hold("PINNED_PARENT_IMPORT_REFUSED")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_uleb(data, offset, end):
    result = 0
    for i in range(5):
        if offset >= end:
            raise Hold("ARM_ATTRIBUTE_TRUNCATED_LEB")
        part = data[offset]
        offset += 1
        result |= (part & 127) << (7 * i)
        if part < 128:
            return result, offset
    raise Hold("ARM_ATTRIBUTE_LONG_LEB")


def read_cstr(data, offset, end):
    idx = data.find(b'\0', offset, end)
    if idx < 0 or idx - offset > 255:
        raise Hold("ARM_ATTRIBUTE_CSTRING_HOLD")
    return data[offset:idx], idx + 1


def decode_aeabi(raw):
    """Parse recognized AEABI file attributes; refuse unknown tag encodings.

    Only fixed-size or NUL-terminated known tag types are accepted. Tag 28's
    register convention is informative, not full ABI or loader proof.
    """
    if not raw or raw[0:1] != b'A':
        raise Hold("ARM_ATTRIBUTE_MAGIC_HOLD")
    cursor = 1
    file_data = []
    while cursor < len(raw):
        if cursor + 4 > len(raw):
            raise Hold("ARM_ATTRIBUTE_SECTION_LENGTH_HOLD")
        length, = struct.unpack_from('<I', raw, cursor)
        if length < 6 or length > 65536 or cursor + length > len(raw):
            raise Hold("ARM_ATTRIBUTE_SECTION_BOUNDS_HOLD")
        end = cursor + length
        vendor, pos = read_cstr(raw, cursor + 4, end)
        if vendor != b'aeabi':
            raise Hold("ARM_ATTRIBUTE_VENDOR_HOLD")
        while pos < end:
            subsection_tag, after_tag = read_uleb(raw, pos, end)
            if after_tag + 4 > end:
                raise Hold("ARM_ATTRIBUTE_SUBSECTION_HEADER_HOLD")
            subsection_len, = struct.unpack_from('<I', raw, after_tag)
            # The length counts the subsection length field and its payload.
            attr_start = after_tag + 4
            attr_end = after_tag + subsection_len
            if subsection_len < 4 or attr_end > end:
                raise Hold("ARM_ATTRIBUTE_SUBSECTION_BOUNDS_HOLD")
            if subsection_tag == 1:
                file_data.append(raw[attr_start:attr_end])
            # Section/symbol attributes have a different grammar; ignore them.
            pos = attr_end
        cursor = end
    if len(file_data) != 1:
        raise Hold("ARM_ATTRIBUTE_FILE_BLOCK_COUNT_HOLD")
    blob = file_data[0]
    pos = 0
    values = {}
    string_tags = {4, 5, 65, 67}
    compound_tags = {32}
    # Known numerical ABI attribute tags; others are not silently skipped.
    numeric_tags = set(range(6, 32)) | {34, 36, 38, 42, 44, 46, 48, 50, 52, 64, 66, 68, 70}
    while pos < len(blob):
        tag, pos = read_uleb(blob, pos, len(blob))
        if tag in values:
            raise Hold("ARM_ATTRIBUTE_DUPLICATE_TAG_HOLD")
        if tag in string_tags:
            _s, pos = read_cstr(blob, pos, len(blob))
            values[tag] = "STRING"
        elif tag in compound_tags:
            _v, pos = read_uleb(blob, pos, len(blob))
            _s, pos = read_cstr(blob, pos, len(blob))
            values[tag] = "COMPOUND"
        elif tag in numeric_tags:
            v, pos = read_uleb(blob, pos, len(blob))
            values[tag] = v
        else:
            raise Hold("ARM_ATTRIBUTE_UNSUPPORTED_TAG_HOLD")
    vfp = values.get(28)
    vfp_category = {0: "AAPCS_CORE_REGISTERS", 1: "AAPCS_VFP_REGISTERS", 2: "TOOLCHAIN_SPECIFIC", 3: "AAPCS_BOTH"}.get(vfp, "UNDECLARED" if vfp is None else "UNKNOWN_VALUE")
    return {"file_attributes_parsed": True,
            "abi_vfp_args": vfp_category,
            "cpu_arch_tag_present": 6 in values,
            "fp_arch_tag_present": 10 in values,
            "abi_hardfp_use_tag_present": 27 in values}


def inspect_arm_attributes(parent26, path):
    """Classify a regular 32-bit ARM ELF SHT_ARM_ATTRIBUTES section in bounds."""
    try:
        with parent26.open_regular_nofollow(path) as f:
            h = parent26.elf_header(f)
            if h is None or h['cls'] != 1 or h['machine'] != 40:
                raise Hold("NOT_ELF32_ARM_HOLD")
            shoff, = struct.unpack(h['endian'] + 'I', parent26.read_at(f, 32, 4))
            ehentsize, nsections, shstrndx = struct.unpack(h['endian'] + 'HHH', parent26.read_at(f, 46, 6))
            if shoff == 0 or nsections == 0:
                return {"status": "SECTION_TABLE_ABSENT"}
            if ehentsize != 40 or shstrndx == 0xffff or nsections > 16384:
                raise Hold("SECTION_TABLE_UNSUPPORTED_HOLD")
            if shoff > h['length'] or nsections * ehentsize > h['length'] - shoff:
                raise Hold("SECTION_TABLE_BOUNDS_HOLD")
            found = []
            for i in range(nsections):
                raw = parent26.read_at(f, shoff + i * ehentsize, ehentsize)
                typ, = struct.unpack_from(h['endian'] + 'I', raw, 4)
                if typ != 0x70000003:  # SHT_ARM_ATTRIBUTES
                    continue
                off, size = struct.unpack_from(h['endian'] + 'II', raw, 16)
                if size == 0 or size > 65536 or off > h['length'] or size > h['length'] - off:
                    raise Hold("ARM_ATTRIBUTE_SECTION_BOUNDS_HOLD")
                found.append(parent26.read_at(f, off, size))
            if not found:
                return {"status": "ARM_ATTRIBUTES_ABSENT"}
            if len(found) != 1:
                raise Hold("MULTIPLE_ARM_ATTRIBUTE_SECTIONS_HOLD")
            return {"status": "ARM_ATTRIBUTES_PRESENT", **decode_aeabi(found[0])}
    except parent26.Hold:
        raise Hold("PARENT_ELF_HOLD") from None


def classify(root, parent_dir):
    if root.is_symlink() or not root.is_dir():
        raise Hold("STAGE_ROOT_INVALID")
    p30 = verify_import(parent_dir / R30, R30, R30_SHA)
    p29 = p30.load_r29(parent_dir / p30.R29_NAME)
    chain = {name:p29.load_pinned(parent_dir/name) for name in p29.PINNED}
    p26 = chain['R4043726-INTERP-GUEST-RESOLVE-READONLY.py']
    p27 = chain['R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py']
    p28 = chain['R4043728-INTERP-PATH-TOPOLOGY-READONLY.py']
    prev = p30.audit(root, p26, p27, p28, p29)
    if prev.get('result') != 'INTERP_ABI_AND_SONAME_STATIC_CLASSIFICATION_ONLY' or prev.get('requesting_elf_count') != 12:
        raise Hold("R3730_BASELINE_HOLD")
    if prev.get('candidate_soname_and_flags',{}).get('soname_basename_match') != 'MATCH':
        raise Hold("R3730_SONAME_HOLD")
    index, sources, _nfiles, _nlinks = p27.inventory(root, p26)
    if len(sources) != 12 or len({lit for lit,_ in sources}) != 1:
        raise Hold("R3727_SOURCE_HOLD")
    missing = sources[0][0]
    basename = missing.rsplit('/',1)[-1]
    matching = set()
    for literal, hdr in sources:
        entries = [p for p,kind in index.get(basename,())
                   if kind == 'regular' and p26.classify_guest_target(root,'/'+p.relative_to(root).as_posix(),hdr)[0] == 'GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE']
        if literal != missing or len(entries)!=1:
            raise Hold("UNIQUE_ALTERNATIVE_HOLD")
        matching.add(entries[0])
    if len(matching)!=1:
        raise Hold("ALTERNATIVE_IDENTITY_HOLD")
    candidate = next(iter(matching))
    candidate_attr = inspect_arm_attributes(p26,candidate)
    counts = Counter()
    seen = 0
    for base, dirs, names in os.walk(root, topdown=True, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(base)/d).is_symlink())
        for name in sorted(names):
            path=Path(base)/name
            if path.is_symlink() or not path.is_file():
                continue
            with p26.open_regular_nofollow(path) as f:
                parsed = p26.inspect_elf(f)
            if parsed is not None and any(lit == missing for lit,_ in parsed[1]):
                obj = inspect_arm_attributes(p26,path)
                counts[obj['status']] += 1
                if obj['status'] == 'ARM_ATTRIBUTES_PRESENT':
                    counts['VFP_ARGS_'+obj['abi_vfp_args']] += 1
                seen += 1
    if seen != 12:
        raise Hold("SOURCE_COUNT_HOLD")
    return {
        "milestone":"R40.4.3.7.31",
        "result":"ARM_ATTRIBUTES_STATIC_CLASSIFIED_ONLY",
        "source_elf_count":seen,
        "source_arm_attribute_categories":dict(sorted(counts.items())),
        "alternative_arm_attributes":candidate_attr,
        "r3730_sha_pinned_and_replayed":True,
        "all_parent_pins_verified":True,
        "guest_interpreter_path_resolved":False,
        "loader_runtime_verified":False,
        "arm_cpu_kernel_compatibility_proven":False,
        "historical_inventory_hashes_reverified":False,
        "original_r26_source_provenance_authenticated":False,
        "transitive_dependency_closure_proven":False,
        "path_strings_exported":False,
        "stage_modified":False,"boot_authorized":False,"prune_authorized":False,
        "immutable_hold":"NOT_BOOTABLE"
    }


def main():
    p=argparse.ArgumentParser(description="Read-only ARM attributes comparison; NOT_BOOTABLE")
    p.add_argument('--rootfs',type=Path,required=True)
    p.add_argument('--parent-dir',type=Path,required=True)
    args=p.parse_args()
    try:
        result=classify(args.rootfs,args.parent_dir)
    except (Hold, OSError) as exc:
        result={"milestone":"R40.4.3.7.31","result":"HOLD",
                "hold_category":exc.code if isinstance(exc,Hold) else "HOST_IO_HOLD",
                "boot_authorized":False,"prune_authorized":False,"immutable_hold":"NOT_BOOTABLE"}
    print(json.dumps(result,sort_keys=True))
    return 0 if result['result']=='ARM_ATTRIBUTES_STATIC_CLASSIFIED_ONLY' else 2


if __name__=='__main__':
    raise SystemExit(main())
