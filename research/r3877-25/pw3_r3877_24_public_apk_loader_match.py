#!/usr/bin/env python3
"""R3877.24: compare a stopped Alpine image loader to indexed public musl APK bytes.

No network, subprocess, SSH, container operation, file extraction, writes, or ARM execution.
"""
import argparse
import base64
import hashlib
import io
import json
import re
import tarfile
import zlib
from pathlib import Path

MILESTONE = 'R3877.24'
PACKAGE_NAME = 'musl'
PACKAGE_VERSION = '1.2.6-r3'
ARCH = 'armv7'
LOADER_FILE = 'lib/ld-musl-armhf.so.1'
IMAGE_ID = 'sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a'
EXPECTED_LOADER_SHA256 = '2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990'
MAX_APK_BYTES = 8 * 1024 * 1024
MAX_INDEX_BYTES = 8 * 1024 * 1024
MAX_INFLATED_MEMBER_BYTES = 64 * 1024 * 1024
MAX_LOADER_BYTES = 4 * 1024 * 1024


class Refusal(Exception):
    pass


def check(condition, reason):
    if not condition:
        raise Refusal(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_bounded(path, limit, label):
    with Path(path).open('rb') as f:
        payload = f.read(limit + 1)
    check(len(payload) <= limit, label + '_FILE_TOO_LARGE')
    return payload


def gzip_members(data, max_inflated=MAX_INFLATED_MEMBER_BYTES):
    check(data.startswith(b'\x1f\x8b\x08'), 'NOT_GZIP_V2_APK')
    parts = []
    offset = 0
    while offset < len(data):
        check(len(parts) < 5, 'TOO_MANY_GZIP_MEMBERS')
        check(data[offset:offset+3] == b'\x1f\x8b\x08', 'INVALID_GZIP_MEMBER_HEADER')
        obj = zlib.decompressobj(16 + zlib.MAX_WBITS)
        try:
            raw = obj.decompress(data[offset:], max_inflated + 1)
            check(len(raw) <= max_inflated, 'GZIP_MEMBER_DECOMPRESS_LIMIT')
            check(obj.eof, 'GZIP_MEMBER_TRUNCATED_OR_TOO_LARGE')
            remaining = obj.flush()
        except zlib.error:
            raise Refusal('GZIP_MEMBER_CORRUPT') from None
        check(len(raw) + len(remaining) <= max_inflated, 'GZIP_MEMBER_DECOMPRESS_LIMIT')
        consumed = len(data) - offset - len(obj.unused_data)
        check(consumed > 0, 'EMPTY_GZIP_MEMBER')
        parts.append((data[offset:offset+consumed], raw + remaining))
        offset += consumed
    return parts


def clean_member_name(name):
    while name.startswith('./'):
        name = name[2:]
    check(bool(name) and not name.startswith('/'), 'UNSAFE_TAR_NAME')
    check(all(x not in ('.', '..', '') for x in name.split('/')), 'UNSAFE_TAR_NAME')
    return name


def tar_files(raw):
    """Return regular-file bytes, never extracting paths or symlinks to the host."""
    result = {}
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
            count = 0
            for entry in archive:
                count += 1
                check(count <= 600, 'TOO_MANY_TAR_MEMBERS')
                if entry.isdir() and entry.name in ('.', './'):
                    continue
                name = clean_member_name(entry.name)
                if entry.isdir() or entry.issym() or entry.islnk():
                    continue
                check(entry.isfile(), 'UNSUPPORTED_TAR_ENTRY')
                check(name not in result, 'DUPLICATE_TAR_PATH')
                check(entry.size <= MAX_INFLATED_MEMBER_BYTES, 'TAR_FILE_TOO_LARGE')
                stream = archive.extractfile(entry)
                check(stream is not None, 'TAR_READ_FAILED')
                data = stream.read(entry.size + 1)
                check(len(data) == entry.size, 'TAR_FILE_TRUNCATED')
                result[name] = data
    except (tarfile.TarError, OSError, ValueError):
        raise Refusal('INVALID_TAR_DATA') from None
    return result


def pkginfo(text):
    values = {}
    for line in text.decode('utf-8', errors='strict').splitlines():
        if not line or line.startswith('#'):
            continue
        if ' = ' not in line:
            continue
        name, value = line.split(' = ', 1)
        if name in ('pkgname', 'pkgver', 'arch', 'datahash'):
            check(name not in values, 'DUPLICATE_PKGINFO_FIELD')
            values[name] = value
    return values


def index_record(text):
    matches = []
    for block in text.decode('utf-8', errors='strict').split('\n\n'):
        record = {}
        for line in block.splitlines():
            if len(line) >= 2 and line[1] == ':':
                if line[0] in ('P', 'V', 'A', 'C'):
                    check(line[0] not in record, 'DUPLICATE_INDEX_FIELD')
                    record[line[0]] = line[2:]
        if record.get('P') == PACKAGE_NAME and record.get('V') == PACKAGE_VERSION:
            matches.append(record)
    check(len(matches) == 1, 'INDEX_MUSL_VERSION_MISSING_OR_DUPLICATE')
    record = matches[0]
    check(record.get('A') == ARCH, 'INDEX_ARCH_MISMATCH')
    check(bool(re.fullmatch(r'Q1[A-Za-z0-9+/=]{20,32}', record.get('C', ''))), 'INDEX_CHECKSUM_FORMAT_INVALID')
    return record


def audit_bytes(apk, index, candidate_loader, expected_loader_sha256=EXPECTED_LOADER_SHA256):
    """Returns an inventory on success; otherwise raises Refusal."""
    check(len(apk) <= MAX_APK_BYTES, 'APK_TOO_LARGE')
    check(len(index) <= MAX_INDEX_BYTES, 'INDEX_TOO_LARGE')
    check(len(candidate_loader) <= MAX_LOADER_BYTES, 'CANDIDATE_LOADER_TOO_LARGE')
    check(digest(candidate_loader) == expected_loader_sha256, 'CANDIDATE_LOADER_BASELINE_HASH_MISMATCH')

    apk_streams = gzip_members(apk)
    check(len(apk_streams) in (2, 3), 'APK_STREAM_COUNT_UNEXPECTED')
    control = []
    data = []
    for i, (compressed, inflated) in enumerate(apk_streams):
        files = tar_files(inflated)
        if '.PKGINFO' in files:
            control.append((i, compressed, files['.PKGINFO']))
        if LOADER_FILE in files:
            data.append((i, compressed, files[LOADER_FILE]))
    check(len(control) == 1 and len(data) == 1, 'APK_CONTROL_OR_LOADER_NOT_UNIQUE')
    ci, control_gz, control_content = control[0]
    di, data_gz, loader = data[0]
    check(ci < di and di == len(apk_streams) - 1, 'APK_STREAM_ORDER_INVALID')
    info = pkginfo(control_content)
    check(info.get('pkgname') == PACKAGE_NAME, 'APK_PKGNAME_MISMATCH')
    check(info.get('pkgver') == PACKAGE_VERSION, 'APK_VERSION_MISMATCH')
    check(info.get('arch') == ARCH, 'APK_ARCH_MISMATCH')
    check(bool(re.fullmatch(r'[0-9a-f]{64}', info.get('datahash', ''))), 'APK_DATAHASH_MISSING_OR_INVALID')
    check(info['datahash'] == digest(data_gz), 'APK_DATAHASH_MISMATCH')
    check(digest(loader) == expected_loader_sha256, 'PUBLIC_APK_LOADER_DIFFERS_FROM_CANDIDATE')
    check(loader == candidate_loader, 'PUBLIC_APK_LOADER_BYTES_DIFFER')

    idx = gzip_members(index)
    check(len(idx) in (1, 2), 'INDEX_STREAM_COUNT_UNEXPECTED')
    matching = []
    for _, inflated in idx:
        files = tar_files(inflated)
        if 'APKINDEX' in files:
            matching.append(files['APKINDEX'])
    check(len(matching) == 1, 'INDEX_FILE_MISSING_OR_DUPLICATE')
    record = index_record(matching[0])
    control_sha1 = base64.b64encode(hashlib.sha1(control_gz).digest()).decode('ascii')
    check(record['C'] == 'Q1' + control_sha1, 'APK_INDEX_CONTROL_SHA1_MISMATCH')
    return {
        'installed_musl_version': PACKAGE_VERSION,
        'installed_musl_arch': ARCH,
        'candidate_loader_sha256': digest(candidate_loader),
        'public_package_loader_sha256': digest(loader),
        'loader_byte_for_byte_match': True,
        'package_sha256': digest(apk),
        'index_sha256': digest(index),
        'package_data_gzip_sha256_verified_against_pkginfo': True,
        'index_q1_control_gzip_sha1_verified': True,
        'public_alpine_repository_signature_verified': False,
        'source_to_binary_reproducibility_verified': False,
        'target_runtime_kernel_compatibility_verified': False,
    }


def base_result():
    return {
        'milestone': MILESTONE,
        'result': 'HOLD',
        'hold_category': 'NOT_BOOTABLE',
        'immutable_hold': 'NOT_BOOTABLE',
        'candidate_image_id_expected': IMAGE_ID,
        'kindle_ssh_sessions': 0,
        'physical_device_access_performed': False,
        'new_kindle_binary_installed_or_executed': False,
        'firmware_write_performed': False,
        'boot_performed': False,
        'original_r13_stage_accessed': False,
        'recovery_verified': False,
        'vendor_kernel_dispatch_verified': False,
        'target_musl_runtime_verified': False,
        'binary_provenance_to_patched_source_verified': False,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apk', required=True)
    ap.add_argument('--index', required=True)
    ap.add_argument('--candidate-loader', required=True)
    ns = ap.parse_args(argv)
    result = base_result()
    try:
        data = audit_bytes(
            read_bounded(ns.apk, MAX_APK_BYTES, 'APK'),
            read_bounded(ns.index, MAX_INDEX_BYTES, 'INDEX'),
            read_bounded(ns.candidate_loader, MAX_LOADER_BYTES, 'LOADER'),
        )
        result['inventory'] = data
        result['result'] = 'PASS_INDEXED_PUBLIC_MUSL_LOADER_BYTES_MATCH_ONLY'
        exit_code = 0
    except (Refusal, OSError, UnicodeError) as e:
        result['hold_category'] = str(e) if isinstance(e, Refusal) else 'LOCAL_INPUT_READ_FAILED'
        exit_code = 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
