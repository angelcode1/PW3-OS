#!/usr/bin/env python3
"""R4043726: source-only PT_INTERP guest-path/ABI candidate audit. NOT_BOOTABLE.

Host traversal is read-only. Stage object paths, guest interpreter literals and
symlink target strings never appear in output. No ELF/loader is executed.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import stat
import struct


class Hold(Exception):
    """A classified source/guest namespace rejection; never include path in output."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def read_at(stream, offset, length):
    if offset < 0 or length < 0:
        raise Hold("ELF_BOUNDS")
    stream.seek(offset)
    data = stream.read(length)
    if len(data) != length:
        raise Hold("ELF_TRUNCATED")
    return data


def elf_header(stream):
    """Read ELF ident/e_type/e_machine without invoking the platform loader."""
    stream.seek(0, os.SEEK_END)
    length = stream.tell()
    if length < 4:
        return None
    magic = read_at(stream, 0, 4)
    if magic != b"\x7fELF":
        return None
    if length < 16:
        raise Hold("ELF_SHORT_IDENT")
    ident = read_at(stream, 0, 16)
    if ident[4] not in (1, 2) or ident[5] not in (1, 2) or ident[6] != 1:
        raise Hold("ELF_INVALID_IDENT")
    cls = ident[4]
    endian = "<" if ident[5] == 1 else ">"
    header_size = 52 if cls == 1 else 64
    if length < header_size:
        raise Hold("ELF_SHORT_HEADER")
    header = read_at(stream, 0, header_size)
    e_type, machine = struct.unpack_from(endian + "HH", header, 16)
    if cls == 1:
        phoff, = struct.unpack_from(endian + "I", header, 28)
        ehsize, phentsize, phnum = struct.unpack_from(endian + "HHH", header, 40)
        phsize = 32
    else:
        phoff, = struct.unpack_from(endian + "Q", header, 32)
        ehsize, phentsize, phnum = struct.unpack_from(endian + "HHH", header, 52)
        phsize = 56
    if ehsize != header_size or (phnum and phentsize != phsize) or phnum == 65535:
        raise Hold("ELF_UNSUPPORTED_PH_LAYOUT")
    if phnum and (phoff == 0 or phoff > length or phnum * phsize > length - phoff):
        raise Hold("ELF_PH_BOUNDS")
    return {
        "cls": cls,
        "data": ident[5],
        "machine": machine,
        "type": e_type,
        "phoff": phoff,
        "phnum": phnum,
        "phsize": phsize,
        "endian": endian,
        "length": length,
    }


def interpreter_literal(raw):
    """Return (POSIX guest path, padding_only) or a strict morphology hold."""
    if not raw or raw[-1] != 0:
        raise Hold("LITERAL_NO_FINAL_NUL")
    nul = raw.find(b"\0")
    name = raw[:nul]
    if not name.startswith(b"/") or not name:
        raise Hold("LITERAL_NOT_ABSOLUTE")
    if any(c < 33 or c > 126 for c in name) or b"\\" in name:
        raise Hold("LITERAL_UNSAFE_BYTE")
    parts = name.split(b"/")
    if any(p in (b"", b".", b"..") for p in parts[1:]):
        raise Hold("LITERAL_UNSAFE_COMPONENT")
    if any(raw[nul + 1:]):
        raise Hold("LITERAL_NONZERO_AFTER_NUL")
    return name.decode("ascii"), nul + 1 < len(raw)


def inspect_elf(stream):
    """Return None for non-ELF; else (header, zero/one interpreter segments)."""
    hdr = elf_header(stream)
    if hdr is None:
        return None
    found = []
    for i in range(hdr["phnum"]):
        ph = read_at(stream, hdr["phoff"] + i * hdr["phsize"], hdr["phsize"])
        ptype, = struct.unpack_from(hdr["endian"] + "I", ph, 0)
        if ptype != 3:
            continue
        if hdr["cls"] == 1:
            off, = struct.unpack_from(hdr["endian"] + "I", ph, 4)
            length, = struct.unpack_from(hdr["endian"] + "I", ph, 16)
        else:
            off, = struct.unpack_from(hdr["endian"] + "Q", ph, 8)
            length, = struct.unpack_from(hdr["endian"] + "Q", ph, 32)
        if not 1 <= length <= 4096 or off > hdr["length"] or length > hdr["length"] - off:
            raise Hold("ELF_INTERP_BOUNDS")
        found.append(interpreter_literal(read_at(stream, off, length)))
        if len(found) > 1:
            raise Hold("ELF_MULTIPLE_INTERP")
    return hdr, found


def resolve_guest(root, guest_path, max_symlinks=40):
    """Resolve symlinks inside a *modeled* guest root, never host absolute root.

    Every component is lstat'ed before stepping into it. Absolute symlink targets
    reset to guest root, and '..' escaping the modeled guest root is held.
    Returns resolved regular-file Path and number of symlinks consumed.
    """
    if not guest_path.startswith("/") or guest_path == "/":
        raise Hold("GUEST_INVALID_PATH")
    if not isinstance(max_symlinks, int) or max_symlinks < 0:
        raise Hold("GUEST_BAD_LINK_LIMIT")
    pending = guest_path.split("/")[1:]
    settled = []
    symlinks = 0
    while pending:
        part = pending.pop(0)
        if part in ("", "."):
            continue
        if part == "..":
            if not settled:
                raise Hold("GUEST_ESCAPE_HOLD")
            settled.pop()
            continue
        if "\0" in part or "\\" in part:
            raise Hold("GUEST_INVALID_COMPONENT")
        target = root.joinpath(*settled, part)
        try:
            mode = target.lstat().st_mode
        except FileNotFoundError:
            raise Hold("GUEST_ABSENT_HOLD") from None
        except OSError:
            raise Hold("GUEST_IO_HOLD") from None
        if stat.S_ISLNK(mode):
            symlinks += 1
            if symlinks > max_symlinks:
                raise Hold("GUEST_SYMLINK_LIMIT_HOLD")
            try:
                link = os.readlink(target)
            except OSError:
                raise Hold("GUEST_IO_HOLD") from None
            if not link:
                raise Hold("GUEST_EMPTY_SYMLINK_HOLD")
            if link.startswith("/"):
                settled.clear()
                pending = link.split("/")[1:] + pending
            else:
                pending = link.split("/") + pending
            continue
        if pending and not stat.S_ISDIR(mode):
            raise Hold("GUEST_PARENT_NONDIR_HOLD")
        settled.append(part)
    target = root.joinpath(*settled)
    try:
        mode = target.lstat().st_mode
    except OSError:
        raise Hold("GUEST_IO_HOLD") from None
    if not stat.S_ISREG(mode):
        raise Hold("GUEST_FINAL_NONREGULAR_HOLD")
    return target, symlinks


def open_regular_nofollow(path):
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise Hold("HOST_NO_NOFOLLOW_HOLD")
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0))
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise Hold("HOST_NONREGULAR_HOLD")
        stream = os.fdopen(fd, "rb", closefd=True)
        fd = None
        return stream
    except OSError:
        raise Hold("HOST_OPEN_HOLD") from None
    finally:
        if fd is not None:
            os.close(fd)


def classify_guest_target(root, path, source_header):
    try:
        physical, links = resolve_guest(root, path)
        with open_regular_nofollow(physical) as stream:
            candidate = elf_header(stream)
        if candidate is None:
            return "GUEST_REGULAR_NONELF_HOLD", links
        if candidate["type"] not in (2, 3):
            return "GUEST_ELF_TYPE_HOLD", links
        if (candidate["cls"], candidate["data"], candidate["machine"]) != (
            source_header["cls"], source_header["data"], source_header["machine"]
        ):
            return "GUEST_ELF_ABI_HEADER_MISMATCH_HOLD", links
        return "GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE", links
    except Hold as exc:
        return exc.code, 0


def scan(root, expected_files):
    if root.is_symlink() or not root.is_dir():
        raise Hold("HOST_INVALID_ROOT")
    counts = Counter()
    statuses = Counter()
    source_holds = Counter()
    link_counts = Counter()
    def walk_error(_):
        raise Hold("HOST_STAGE_WALK_HOLD")
    for base, dirs, filenames in os.walk(root, topdown=True, followlinks=False, onerror=walk_error):
        dirs[:] = sorted(d for d in dirs if not (Path(base) / d).is_symlink())
        for name in sorted(filenames):
            path = Path(base) / name
            try:
                mode = path.lstat().st_mode
            except OSError:
                raise Hold("HOST_STAGE_LSTAT_HOLD") from None
            if not stat.S_ISREG(mode):
                continue
            counts["rootfs_regular_files"] += 1
            if counts["rootfs_regular_files"] > 100000:
                raise Hold("HOST_TOO_MANY_FILES")
            try:
                with open_regular_nofollow(path) as stream:
                    inspected = inspect_elf(stream)
                if inspected is None:
                    continue
                counts["elf_objects"] += 1
                source_hdr, segments = inspected
                counts["interp_segments"] += len(segments)
                for guest_path, padded in segments:
                    counts["padding_only_literal" if padded else "strict_literal"] += 1
                    category, hops = classify_guest_target(root, guest_path, source_hdr)
                    statuses[category] += 1
                    if hops:
                        link_counts["resolved_via_at_least_one_symlink"] += 1
                    else:
                        link_counts["zero_symlink_hops_or_unresolved"] += 1
            except Hold as exc:
                source_holds[exc.code] += 1
    expected = {"rootfs_regular_files": expected_files,
                "elf_objects": 83, "interp_segments": 19,
                "strict_literal": 9, "padding_only_literal": 10}
    exact = all(counts[key] == val for key, val in expected.items()) and not source_holds
    return {
        "milestone": "R40.4.3.7.26",
        "result": "STATIC_INTERP_GUEST_PATH_CLASSIFICATION_ONLY" if exact else "HOLD_BASELINE_OR_ELF_PARSE",
        "counts": {key: counts[key] for key in sorted(expected)},
        "expected": expected,
        "path_resolution_counts": dict(sorted(statuses.items())),
        "guest_symlink_hop_summary": dict(sorted(link_counts.items())),
        "source_parse_holds": dict(sorted(source_holds.items())),
        "path_strings_exported": False,
        "source_sha_pins_reverified": False,
        "historical_inventory_hashes_reverified": False,
        "runtime_loader_selected": False,
        "runtime_loader_resolved": False,
        "transitive_dependency_closure_proven": False,
        "boot_authorized": False,
        "prune_authorized": False,
        "immutable_hold": "NOT_BOOTABLE",
    }


def main():
    ap = argparse.ArgumentParser(description="Offline PT_INTERP guest namespace candidate audit; NOT_BOOTABLE")
    ap.add_argument("--rootfs", type=Path, required=True)
    ap.add_argument("--expected-rootfs-regular", type=int, default=1446)
    args = ap.parse_args()
    if args.expected_rootfs_regular < 0:
        ap.error("expected-rootfs-regular must be nonnegative")
    try:
        summary = scan(args.rootfs, args.expected_rootfs_regular)
    except Hold as exc:
        summary = {"milestone": "R40.4.3.7.26", "result": "HOLD_SCANNER_ERROR",
                   "error_category": exc.code, "boot_authorized": False,
                   "prune_authorized": False, "immutable_hold": "NOT_BOOTABLE"}
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["result"] == "STATIC_INTERP_GUEST_PATH_CLASSIFICATION_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
