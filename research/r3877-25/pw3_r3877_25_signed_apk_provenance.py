#!/usr/bin/env python3
"""R3877.25: offline Alpine APKv2 index+package signature validation.

Only reads host files, uses openssl dgst on bounded local temp files, never Kindle/Alpine.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from pw3_r3877_24_public_apk_loader_match import (
    audit_bytes, base_result, check, digest, gzip_members, read_bounded, tar_files,
    Refusal, MAX_APK_BYTES, MAX_INDEX_BYTES, MAX_LOADER_BYTES,
)

MILESTONE = 'R3877.25'
APORTS_COMMIT = '35f5eb2864e50dd4448758d31f3e2a32f733ab84'
# Git blob SHA-1 of original text key files, not key fingerprints.
PINNED_KEYS = {
    'alpine-devel@lists.alpinelinux.org-616adfeb.rsa.pub': 'bb15efe96d7c95a0602b243ce0848aa42cf80020',
    'alpine-devel@lists.alpinelinux.org-6165ee59.rsa.pub': 'f2165aebadab1c1e43798f1278c3897d85f16da1',
}
# Accept only documented APKv2 RSA types, fail closed on ambiguous/malformed signatures.
SIG_REGEX = re.compile(r'^\.SIGN\.(RSA|RSA256|RSA512)\.(alpine-devel@lists\.alpinelinux\.org-[0-9a-f]{8}\.rsa\.pub)$')
DIGEST_ARGS = {'RSA':'-sha1','RSA256':'-sha256','RSA512':'-sha512'}


def git_blob_sha(data):
    return hashlib.sha1(f'blob {len(data)}\0'.encode('ascii') + data).hexdigest()


def validate_pinned_key(name, key_bytes, pins=PINNED_KEYS):
    check(name in pins, 'SIGNER_KEY_NOT_PINNED_IN_APORTS')
    check(100 <= len(key_bytes) <= 16000, 'SIGNER_PUBLIC_KEY_INVALID_SIZE')
    check(git_blob_sha(key_bytes) == pins[name], 'SIGNER_PUBLIC_KEY_BLOB_HASH_MISMATCH')
    check(key_bytes.startswith(b'-----BEGIN PUBLIC KEY-----\n') and key_bytes.rstrip().endswith(b'-----END PUBLIC KEY-----'), 'SIGNER_NOT_PEM_PUBLIC_KEY')
    return git_blob_sha(key_bytes)


def signature_segment(archive_bytes, label):
    members = gzip_members(archive_bytes)
    check(len(members) in (2, 3), label + '_UNSIGNED_OR_BAD_MEMBER_COUNT')
    names = tar_files(members[0][1]); candidates = [(k,v) for k,v in names.items() if k.startswith('.SIGN.')]
    check(len(names) == 1 and len(candidates) == 1, label + '_MISSING_OR_MULTIPLE_SIGNATURE_FILES')
    name, signature = candidates[0]
    match = SIG_REGEX.fullmatch(name)
    check(match is not None, label + '_UNRECOGNIZED_SIGNATURE_FORMAT')
    algorithm, signer = match.groups()
    check(signer in PINNED_KEYS, label + '_SIGNER_NOT_IN_PINNED_KEY_SET')
    check(64 <= len(signature) <= 4096, label + '_SIGNATURE_SIZE_INVALID')
    if label == 'INDEX':
        check(len(members) == 2, 'INDEX_SIGNED_STREAM_COUNT_INVALID')
        check('APKINDEX' in tar_files(members[1][1]), 'SIGNED_INDEX_PAYLOAD_MISSING')
    else:
        check(len(members) == 3, 'APK_SIGNED_STREAM_COUNT_INVALID')
        check('.PKGINFO' in tar_files(members[1][1]), 'APK_SIGNED_CONTROL_MISSING')
    # A v2 signature with .PKGINFO datahash authenticates compressed control bytes;
    # index signature authenticates the second compressed gzip member.
    return {'signer': signer, 'algorithm': algorithm, 'signature': signature,
            'signed_bytes': members[1][0]}


def verify_with_openssl(signature, signed_bytes, key_bytes, algorithm, openssl='openssl'):
    """OpenSSL is a host tool; no shell, no ARM code, bounded temp files."""
    with tempfile.TemporaryDirectory(prefix='pw3-r3877-25-') as td:
        p = Path(td)
        sig = p / 'signature.bin'; content = p / 'signed.gz'; key = p / 'trusted.pem'
        sig.write_bytes(signature); content.write_bytes(signed_bytes); key.write_bytes(key_bytes)
        try:
            proc = subprocess.run([openssl, 'dgst', DIGEST_ARGS[algorithm], '-verify', str(key), '-signature', str(sig), str(content)],
                                  capture_output=True, text=True, timeout=15, check=False)
        except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
            raise Refusal('HOST_OPENSSL_UNAVAILABLE_OR_FAILED') from None
    check(proc.returncode == 0 and proc.stdout.strip() == 'Verified OK', 'CRYPTOGRAPHIC_SIGNATURE_VERIFICATION_FAILED')
    return True


def audit_authenticity(apk, index, loader, key_dir, *, pins=PINNED_KEYS, openssl='openssl', expected_loader_sha256=None):
    # First verify previous R3877.24 full byte/index consistency and pinned loader baseline.
    prior = audit_bytes(apk, index, loader, expected_loader_sha256=expected_loader_sha256 or '2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990')
    index_sig = signature_segment(index, 'INDEX')
    apk_sig = signature_segment(apk, 'APK')
    result = {}
    for label, record in [('INDEX', index_sig), ('APK', apk_sig)]:
        signer = record['signer']
        path = Path(key_dir) / signer
        check(path.is_file() and not path.is_symlink(), label + '_TRUSTED_KEY_FILE_MISSING')
        raw_key = read_bounded(path, 16000, label + '_KEY')
        identity = validate_pinned_key(signer, raw_key, pins=pins)
        verify_with_openssl(record['signature'], record['signed_bytes'], raw_key,
                            record['algorithm'], openssl=openssl)
        result[label.lower()] = {'signature_verified': True, 'signature_algorithm': record['algorithm'],
                                'signer_public_key_filename': signer, 'aports_key_blob_sha1': identity}
    return {'prior_r3877_24_check_preserved': True, 'public_package_loader_sha256': prior['public_package_loader_sha256'],
            'package_sha256': prior['package_sha256'], 'index_sha256': prior['index_sha256'],
            'candidate_loader_byte_for_byte_match': True, 'alpine_aports_key_snapshot_commit': APORTS_COMMIT,
            'index': result['index'], 'apk': result['apk'],
            'repository_and_package_signatures_cryptographically_verified_with_pinned_aports_keys': True,
            'key_trust_anchored_to_pinned_aports_git_snapshot': True,
            'key_authenticity_independently_verified': False,
            'patched_source_to_binary_equivalence_verified': False,
            'vendor_kernel_runtime_compatibility_verified': False}


def base():
    o = base_result(); o.update(milestone=MILESTONE, result='HOLD',
                              public_alpine_repository_signature_verified=False,
                              public_alpine_package_signature_verified=False,
                              binary_provenance_to_patched_source_verified=False)
    return o


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apk', required=True)
    ap.add_argument('--index', required=True)
    ap.add_argument('--candidate-loader', required=True)
    ap.add_argument('--key-dir', required=True)
    args = ap.parse_args(argv)
    out=base()
    try:
        inventory = audit_authenticity(read_bounded(args.apk, MAX_APK_BYTES, 'APK'),
                                       read_bounded(args.index, MAX_INDEX_BYTES, 'INDEX'),
                                       read_bounded(args.candidate_loader, MAX_LOADER_BYTES, 'LOADER'),
                                       args.key_dir)
        out.update(result='PASS_PINNED_APORTS_SIGNATURES_AND_PUBLIC_LOADER_MATCH_ONLY',
                   inventory=inventory,
                   public_alpine_repository_signature_verified=True,
                   public_alpine_package_signature_verified=True)
    except (Refusal, OSError, ValueError) as e:
        out['hold_category'] = str(e) if isinstance(e, Refusal) else 'HOST_INPUT_UNAVAILABLE'
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out['result'].startswith('PASS_') else 2

if __name__ == '__main__':
    raise SystemExit(main())
