#!/usr/bin/env python3
"""R3763 read-only offline investigation of an Amazon-listed PW3 source bundle.

No network or extraction, no device access, no guest execution, no firmware writes.
An archive's name/bytes alone do not independently authenticate its download origin.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tarfile

MILESTONE = "R40.4.3.7.63"
OFFICIAL_SOURCE_NOTICE = "https://digprjsurvey.amazon.com/csad/help/node/200203720"
OFFICIAL_ARCHIVE_NAME = "Kindle_src_5.16.2.1.1_4097470002.tar.gz"
OFFICIAL_ARCHIVE_URL = "https://kindledownloads.s3.amazonaws.com/" + OFFICIAL_ARCHIVE_NAME
WARIO_SUFFIX = "/arch/arm/configs/imx60_wario_defconfig"
PIN_BLOB = "bbc2f92713d05dfd6ea52973fc7d958e49fa6464"
PIN_SIZE = 59582
MAX_ARCHIVE_BYTES = 4 * 1024**3
MAX_NESTED_BYTES = 2 * 1024**3
MAX_ARCHIVE_MEMBERS = 120000
MAX_CONFIG_MATCHES = 8

class Hold(Exception):
    def __init__(self, category):
        self.category = category
        super().__init__(category)


def open_regular_nofollow(path):
    p = Path(os.path.abspath(str(path)))
    for part in (p, *p.parents):
        try:
            s = part.lstat()
        except OSError as exc:
            raise Hold("LOCAL_ARCHIVE_MISSING_HOLD") from exc
        if stat.S_ISLNK(s.st_mode):
            raise Hold("LOCAL_ARCHIVE_SYMLINK_HOLD")
    try:
        fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError as exc:
        raise Hold("LOCAL_ARCHIVE_OPEN_HOLD") from exc
    s = os.fstat(fd)
    if not stat.S_ISREG(s.st_mode) or not 0 < s.st_size <= MAX_ARCHIVE_BYTES:
        os.close(fd)
        raise Hold("LOCAL_ARCHIVE_TYPE_OR_SIZE_HOLD")
    return fd, s


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()


def is_wario(name):
    return name == WARIO_SUFFIX[1:] or name.endswith(WARIO_SUFFIX)


def is_kernel_source_tar(name):
    base = name.rsplit("/", 1)[-1].lower()
    return "linux" in base and base.endswith((".tar", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2"))


def scan_tar(fileobj, depth, found, budget):
    try:
        with tarfile.open(fileobj=fileobj, mode="r|*") as archive:
            for member in archive:
                budget[0] += 1
                if budget[0] > MAX_ARCHIVE_MEMBERS:
                    raise Hold("ARCHIVE_MEMBER_LIMIT_HOLD")
                if not member.isfile():
                    continue
                if is_wario(member.name):
                    if member.size > PIN_SIZE * 4 or member.size <= 0:
                        raise Hold("WARIO_CONFIG_SIZE_HOLD")
                    reader = archive.extractfile(member)
                    if reader is None:
                        raise Hold("WARIO_CONFIG_UNREADABLE_HOLD")
                    data = reader.read(PIN_SIZE * 4 + 1)
                    if len(data) != member.size:
                        raise Hold("WARIO_CONFIG_SHORT_READ_HOLD")
                    found.append((len(data), git_blob(data), depth))
                    if len(found) > MAX_CONFIG_MATCHES:
                        raise Hold("WARIO_CONFIG_AMBIGUOUS_HOLD")
                elif depth == 0 and is_kernel_source_tar(member.name):
                    if member.size > MAX_NESTED_BYTES or member.size <= 0:
                        raise Hold("KERNEL_SOURCE_MEMBER_SIZE_HOLD")
                    inner = archive.extractfile(member)
                    if inner is None:
                        raise Hold("KERNEL_SOURCE_MEMBER_UNREADABLE_HOLD")
                    scan_tar(inner, depth + 1, found, budget)
    except (tarfile.TarError, EOFError, OSError) as exc:
        raise Hold("INVALID_ARCHIVE_HOLD") from exc


def analyze(path):
    if Path(path).name != OFFICIAL_ARCHIVE_NAME:
        raise Hold("UNEXPECTED_AMAZON_SOURCE_FILENAME_HOLD")
    fd, start = open_regular_nofollow(path)
    try:
        sha = hashlib.sha256()
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            sha.update(chunk)
        after_digest = os.fstat(fd)
        if (start.st_dev, start.st_ino, start.st_size, start.st_mtime_ns) != (after_digest.st_dev, after_digest.st_ino, after_digest.st_size, after_digest.st_mtime_ns):
            raise Hold("LOCAL_ARCHIVE_CHANGED_HOLD")
        os.lseek(fd, 0, os.SEEK_SET)
        matches, budget = [], [0]
        with os.fdopen(os.dup(fd), "rb") as reader:
            scan_tar(reader, 0, matches, budget)
        after_scan = os.fstat(fd)
        if (start.st_dev, start.st_ino, start.st_size, start.st_mtime_ns) != (after_scan.st_dev, after_scan.st_ino, after_scan.st_size, after_scan.st_mtime_ns):
            raise Hold("LOCAL_ARCHIVE_CHANGED_HOLD")
        if not matches:
            raise Hold("OFFICIAL_ARCHIVE_WARIO_CONFIG_NOT_LOCATED_HOLD")
        blobs = set((size, blob) for size, blob, _ in matches)
        if len(blobs) > 1:
            raise Hold("OFFICIAL_ARCHIVE_WARIO_CONFIG_AMBIGUOUS_HOLD")
        if len(matches) != 1:
            raise Hold("OFFICIAL_ARCHIVE_WARIO_CONFIG_AMBIGUOUS_HOLD")
        length, blob = next(iter(blobs))
        if length != PIN_SIZE or blob != PIN_BLOB:
            raise Hold("OFFICIAL_ARCHIVE_WARIO_CONFIG_BLOB_DIFFERS_HOLD")
        return {
            "result": "AMAZON_LISTED_ARCHIVE_WARIO_BLOB_MATCH_STATIC_ONLY",
            "archive_sha256_observed": sha.hexdigest(),
            "archive_size_bytes": start.st_size,
            "archive_members_scanned": budget[0],
            "candidate_configs_found": len(matches),
            "candidate_configs_in_nested_archive": sum(depth > 0 for _, _, depth in matches),
            "wario_config_blob_sha1": blob,
            "wario_config_size": length,
            "official_source_notice": OFFICIAL_SOURCE_NOTICE,
            "expected_amazon_archive_url": OFFICIAL_ARCHIVE_URL,
            "archive_origin_cryptographically_authenticated": False,
            "r13_image_provenance_authenticated": False,
            "actual_pw3_running_kernel_verified": False,
            "kernel_abi_runtime_compatibility_verified": False,
            "boot_authorized": False,
            "firmware_write_authorized": False,
            "device_access_authorized": False,
            "guest_execution_authorized": False,
            "mapping_applied": False,
            "prune_authorized": False,
            "immutable_hold": "NOT_BOOTABLE",
        }
    finally:
        os.close(fd)


def main(argv=None):
    p = argparse.ArgumentParser(description="Offline, read-only comparison of Amazon PW3 source archive")
    p.add_argument("--archive", required=True, type=Path)
    args = p.parse_args(argv)
    try:
        output = analyze(args.archive)
        status = 0
    except Hold as exc:
        output = {"result": "HOLD", "hold_category": exc.category, "archive_origin_cryptographically_authenticated": False,
                  "r13_image_provenance_authenticated": False, "actual_pw3_running_kernel_verified": False,
                  "boot_authorized": False, "firmware_write_authorized": False, "device_access_authorized": False,
                  "guest_execution_authorized": False, "mapping_applied": False, "prune_authorized": False,
                  "immutable_hold": "NOT_BOOTABLE"}
        status = 2
    output["milestone"] = MILESTONE
    print(json.dumps(output, sort_keys=True))
    return status


if __name__ == "__main__":
    sys.exit(main())
