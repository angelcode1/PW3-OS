"""Synthetic-only APK v2 tests. Never touches Docker, network or the Kindle."""
import base64
import contextlib
import gzip
import hashlib
import io
import json
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from pw3_r3877_24_public_apk_loader_match import (
    ARCH, EXPECTED_LOADER_SHA256, LOADER_FILE, PACKAGE_NAME, PACKAGE_VERSION,
    Refusal, audit_bytes, base_result, clean_member_name, digest, gzip_members,
    index_record, main, pkginfo, read_bounded, tar_files
)


def make_tar(files):
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode='w') as a:
        for name, body in files.items():
            entry = tarfile.TarInfo(name=name)
            entry.size = len(body)
            a.addfile(entry, io.BytesIO(body))
    return out.getvalue()


def make_fixture(loader=b'fake-ARMv7-musl-loader', packaged_loader=None,
                 pkgver=PACKAGE_VERSION, arch=ARCH, indexarch=ARCH,
                 bad_datahash=False, bad_index_checksum=False,
                 signature=True, loaderpath=LOADER_FILE):
    if packaged_loader is None:
        packaged_loader = loader
    data_gzip = gzip.compress(make_tar({loaderpath: packaged_loader}), mtime=0)
    datahash = digest(data_gzip)
    if bad_datahash: datahash = 'a' * 64
    info = f'pkgname = {PACKAGE_NAME}\npkgver = {pkgver}\narch = {arch}\ndatahash = {datahash}\n'.encode()
    control_gzip = gzip.compress(make_tar({'.PKGINFO': info}), mtime=0)
    sig_gzip = gzip.compress(make_tar({'.SIGN.RSA.testing': b'fake signature NOT AUTHENTICATED'}), mtime=0)
    streams = ([sig_gzip] if signature else []) + [control_gzip, data_gzip]
    checksum = 'Q1' + base64.b64encode(hashlib.sha1(control_gzip).digest()).decode()
    if bad_index_checksum: checksum = 'Q1' + base64.b64encode(b'x'*20).decode()
    entry = f'P:{PACKAGE_NAME}\nV:{PACKAGE_VERSION}\nA:{indexarch}\nC:{checksum}\n\n'.encode()
    index = gzip.compress(make_tar({'APKINDEX': entry}), mtime=0)
    return b''.join(streams), index, loader


class V2StreamTests(unittest.TestCase):
    def test_split_two_members(self):
        apk, _, _ = make_fixture(signature=False)
        self.assertEqual(len(gzip_members(apk)), 2)

    def test_split_three_members(self):
        apk, _, _ = make_fixture()
        self.assertEqual(len(gzip_members(apk)), 3)

    def test_truncated_member(self):
        apk, _, _ = make_fixture()
        with self.assertRaises(Refusal): gzip_members(apk[:-10])

    def test_corrupt_gzip(self):
        apk, _, _ = make_fixture()
        with self.assertRaises(Refusal): gzip_members(apk[:20] + b'\0'*17 + apk[37:])

    def test_reject_not_gzip(self):
        with self.assertRaisesRegex(Refusal, 'NOT_GZIP_V2_APK'):
            gzip_members(b'not a gzip')

    def test_gzip_expansion_cap(self):
        inflated = gzip.compress(b'A'*10000,mtime=0)
        with self.assertRaises(Refusal): gzip_members(inflated, 100)

    def test_no_traversal(self):
        for s in ('../thing', 'lib/../thing', '/etc/passwd'):
            with self.subTest(s=s), self.assertRaises(Refusal):
                clean_member_name(s)

    def test_dot_slash_normalization(self):
        self.assertEqual(clean_member_name('./lib/foo'), 'lib/foo')

    def test_empty_tar_rejected(self):
        with self.assertRaises(Refusal): tar_files(b'not tar')

    def test_root_directory_tar_entry_accepted(self):
        raw=io.BytesIO()
        with tarfile.open(fileobj=raw,mode='w') as t:
            e=tarfile.TarInfo('./');e.type=tarfile.DIRTYPE
            t.addfile(e)
            e=tarfile.TarInfo('./lib/file');e.size=3
            t.addfile(e,io.BytesIO(b'abc'))
        self.assertEqual(tar_files(raw.getvalue()), {'lib/file': b'abc'})

    def test_tar_files_do_not_extract_to_disk(self):
        self.assertEqual(tar_files(make_tar({'foo/bar':b'yes'})),{'foo/bar':b'yes'})

    def test_parse_pkginfo_fields(self):
        self.assertEqual(pkginfo(b'pkgname = musl\nignored = something\n')['pkgname'], 'musl')

    def test_index_checksum_format(self):
        with self.assertRaises(Refusal): index_record(b'P:musl\nV:1.2.6-r3\nA:armv7\nC:invalid\n')

    def test_deny_duplicates(self):
        with self.assertRaises(Refusal): pkginfo(b'pkgname = musl\npkgname = other\n')

    def test_max_file_input(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'big';p.write_bytes(b'a'*50)
            with self.assertRaises(Refusal): read_bounded(p,20,'TEST')


class ProvenanceTests(unittest.TestCase):
    def accept(self, **kw):
        apk,index,loader=make_fixture(**kw)
        return audit_bytes(apk,index,loader,expected_loader_sha256=digest(loader))

    def test_good_signed_layout_not_trusted_as_signature(self):
        result=self.accept()
        self.assertTrue(result['loader_byte_for_byte_match'])
        self.assertFalse(result['public_alpine_repository_signature_verified'])
        self.assertFalse(result['source_to_binary_reproducibility_verified'])

    def test_good_unsigned_layout(self):
        self.assertTrue(self.accept(signature=False)['loader_byte_for_byte_match'])

    def test_different_candidate_loader(self):
        apk,index,loader=make_fixture(packaged_loader=b'different-loader')
        with self.assertRaisesRegex(Refusal,'PUBLIC_APK_LOADER_DIFFERS'):
            audit_bytes(apk,index,loader,expected_loader_sha256=digest(loader))

    def test_wrong_candidate_baseline(self):
        apk,index,loader=make_fixture()
        with self.assertRaisesRegex(Refusal,'CANDIDATE_LOADER_BASELINE'):
            audit_bytes(apk,index,loader)

    def test_wrong_package_version(self):
        apk,index,loader=make_fixture(pkgver='1.2.5-r0')
        with self.assertRaisesRegex(Refusal,'APK_VERSION_MISMATCH'):
            audit_bytes(apk,index,loader,expected_loader_sha256=digest(loader))

    def test_wrong_package_arch(self):
        apk,index,loader=make_fixture(arch='armhf')
        with self.assertRaisesRegex(Refusal,'APK_ARCH_MISMATCH'):
            audit_bytes(apk,index,loader,expected_loader_sha256=digest(loader))

    def test_wrong_index_arch(self):
        apk,index,loader=make_fixture(indexarch='aarch64')
        with self.assertRaisesRegex(Refusal,'INDEX_ARCH_MISMATCH'):
            audit_bytes(apk,index,loader,expected_loader_sha256=digest(loader))

    def test_wrong_datahash(self):
        apk,index,loader=make_fixture(bad_datahash=True)
        with self.assertRaisesRegex(Refusal,'APK_DATAHASH_MISMATCH'):
            audit_bytes(apk,index,loader,expected_loader_sha256=digest(loader))

    def test_wrong_index_checksum(self):
        apk,index,loader=make_fixture(bad_index_checksum=True)
        with self.assertRaisesRegex(Refusal,'APK_INDEX_CONTROL_SHA1_MISMATCH'):
            audit_bytes(apk,index,loader,expected_loader_sha256=digest(loader))

    def test_wrong_loader_path(self):
        apk,index,loader=make_fixture(loaderpath='usr/lib/libc.so')
        with self.assertRaisesRegex(Refusal,'APK_CONTROL_OR_LOADER_NOT_UNIQUE'):
            audit_bytes(apk,index,loader,expected_loader_sha256=digest(loader))

    def test_not_all_strong_provenance_flags(self):
        d=base_result()
        self.assertFalse(d['recovery_verified'])
        self.assertFalse(d['target_musl_runtime_verified'])
        self.assertFalse(d['binary_provenance_to_patched_source_verified'])
        self.assertEqual(d['immutable_hold'],'NOT_BOOTABLE')
        self.assertEqual(d['kindle_ssh_sessions'],0)

    def test_cli_fail_closed_absent_inputs(self):
        with tempfile.TemporaryDirectory() as t:
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc=main(['--apk',str(Path(t)/'noapk'),'--index',str(Path(t)/'noindex'),'--candidate-loader',str(Path(t)/'noloader')])
            data=json.loads(out.getvalue())
            self.assertEqual(rc,2)
            self.assertEqual(data['result'],'HOLD')
            self.assertEqual(data['hold_category'],'LOCAL_INPUT_READ_FAILED')
            self.assertEqual(data['kindle_ssh_sessions'],0)


if __name__=='__main__': unittest.main()
