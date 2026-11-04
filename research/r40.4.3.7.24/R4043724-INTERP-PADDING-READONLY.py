#!/usr/bin/env python3
"""R4043724 standalone, read-only PT_INTERP diagnostic. NOT_BOOTABLE."""
import argparse
import json
import os
import stat
import struct
from collections import Counter
from pathlib import Path

class Hold(Exception):
    pass

def read_at(f, offset, length):
    f.seek(offset)
    data = f.read(length)
    if len(data) != length:
        raise Hold("truncated")
    return data

def classify_literal(data):
    if not data or data[-1] != 0:
        return "HOLD_MISSING_FINAL_NUL"
    first = data.find(b"\0")
    name = data[:first]
    if not name or not name.startswith(b"/"):
        return "HOLD_NONABSOLUTE_OR_EMPTY"
    if any(c < 33 or c > 126 for c in name):
        return "HOLD_NONASCII_OR_CONTROL"
    if b"\\" in name or b"//" in name or any(
        x in (b"", b".", b"..") for x in name.split(b"/")[1:]
    ):
        return "HOLD_UNSAFE_COMPONENT"
    if any(data[first + 1:]):
        return "HOLD_EMBEDDED_NONZERO_AFTER_NUL"
    return "PADDING_ONLY_CANDIDATE" if first + 1 < len(data) else "STRICT_LITERAL_PASS"

def inspect_elf(f):
    f.seek(0, os.SEEK_END)
    size = f.tell()
    if size < 4:
        return None
    ident = read_at(f, 0, min(size, 16))
    if ident[:4] != b"\x7fELF":
        return None
    if len(ident) != 16 or ident[4] not in (1, 2) or ident[5] not in (1, 2) or ident[6] != 1:
        raise Hold("invalid_elf_ident")
    cls = ident[4]
    endian = "<" if ident[5] == 1 else ">"
    hdrsize = 52 if cls == 1 else 64
    if size < hdrsize:
        raise Hold("short_elf_header")
    hdr = read_at(f, 0, hdrsize)
    if cls == 1:
        phoff, = struct.unpack_from(endian + "I", hdr, 28)
        ehsize, phentsize, phnum = struct.unpack_from(endian + "HHH", hdr, 40)
        expected_ph = 32
    else:
        phoff, = struct.unpack_from(endian + "Q", hdr, 32)
        ehsize, phentsize, phnum = struct.unpack_from(endian + "HHH", hdr, 52)
        expected_ph = 56
    if ehsize != hdrsize or phentsize != expected_ph or phnum == 65535:
        raise Hold("unsupported_program_headers")
    if phnum and (phoff == 0 or phoff > size or phnum * phentsize > size - phoff):
        raise Hold("program_header_bounds")
    segments = []
    for i in range(phnum):
        ph = read_at(f, phoff + i * phentsize, phentsize)
        ptype, = struct.unpack_from(endian + "I", ph, 0)
        if ptype != 3:
            continue
        if cls == 1:
            offset, = struct.unpack_from(endian + "I", ph, 4)
            length, = struct.unpack_from(endian + "I", ph, 16)
        else:
            offset, = struct.unpack_from(endian + "Q", ph, 8)
            length, = struct.unpack_from(endian + "Q", ph, 32)
        if not 1 <= length <= 4096 or offset > size or length > size - offset:
            raise Hold("interp_bounds")
        segments.append(classify_literal(read_at(f, offset, length)))
    if len(segments) > 1:
        raise Hold("multiple_pt_interp")
    return segments

def scan(root):
    if root.is_symlink() or not root.is_dir():
        raise Hold("invalid_root")
    counts = Counter()
    for base, dirs, filenames in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(base) / d).is_symlink())
        for filename in sorted(filenames):
            path = Path(base) / filename
            if path.is_symlink():
                continue
            fd = None
            try:
                fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    continue
                counts["regular_files_scanned"] += 1
                if counts["regular_files_scanned"] > 100000:
                    raise Hold("file_count_limit")
                with os.fdopen(fd, "rb", closefd=True) as f:
                    fd = None
                    segments = inspect_elf(f)
                if segments is not None:
                    counts["elf_objects"] += 1
                    counts["interp_segments"] += len(segments)
                    counts.update(segments)
            except (OSError, Hold):
                raise Hold("stage_scan_failure") from None
            finally:
                if fd is not None:
                    os.close(fd)
    return counts

def main():
    ap = argparse.ArgumentParser(description="Read-only PT_INTERP padding classification; never boot or prune")
    ap.add_argument("--stage-root", type=Path, required=True)
    ap.add_argument("--expected-elf", type=int, default=83)
    ap.add_argument("--expected-interp", type=int, default=19)
    ap.add_argument("--expected-strict", type=int, default=9)
    ap.add_argument("--expected-padding", type=int, default=10)
    args = ap.parse_args()
    try:
        counts = scan(args.stage_root)
        expected = {"elf_objects": args.expected_elf,
                    "interp_segments": args.expected_interp,
                    "STRICT_LITERAL_PASS": args.expected_strict,
                    "PADDING_ONLY_CANDIDATE": args.expected_padding}
        good = all(counts[k] == v for k, v in expected.items())
        good = good and not any(k.startswith("HOLD_") and v for k, v in counts.items())
        result = {"milestone": "R40.4.3.7.24",
                  "result": "SOURCE_ONLY_PADDING_CLASSIFICATION" if good else "HOLD",
                  "counts": dict(sorted(counts.items())), "expected_counts": expected,
                  "parent_source_pins_verified": False,
                  "interp_runtime_resolved": False,
                  "dependency_closure_proven": False,
                  "boot_authorized": False, "prune_authorized": False,
                  "immutable_hold": "NOT_BOOTABLE"}
    except Hold:
        good = False
        result = {"milestone": "R40.4.3.7.24", "result": "HOLD_SCAN_FAILURE",
                  "immutable_hold": "NOT_BOOTABLE"}
    print(json.dumps(result, sort_keys=True))
    return 0 if good else 2

if __name__ == "__main__":
    raise SystemExit(main())
