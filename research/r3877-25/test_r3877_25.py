"""Offline synthetic cryptographic APK v2 verification tests (host RSA only)."""
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from test_r3877_24 import make_tar
from pw3_r3877_24_public_apk_loader_match import digest, Refusal
from pw3_r3877_25_signed_apk_provenance import (
    git_blob_sha, validate_pinned_key, signature_segment, verify_with_openssl,
    audit_authenticity, base, main, PINNED_KEYS,
)

NAME='alpine-devel@lists.alpinelinux.org-616adfeb.rsa.pub'

def openssl(args):
    return subprocess.run(['openssl']+args,check=True,capture_output=True).stdout

class AuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.folder=Path(cls.tmp.name)
        cls.private=cls.folder/'key.pem'
        cls.public=cls.folder/NAME
        openssl(['genpkey','-algorithm','RSA','-pkeyopt','rsa_keygen_bits:2048','-out',str(cls.private)])
        cls.public.write_bytes(openssl(['pkey','-in',str(cls.private),'-pubout']))
        cls.pins={NAME:git_blob_sha(cls.public.read_bytes())}
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def signed(self, payload, algo='RSA'):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'content';p.write_bytes(payload)
            s=Path(d)/'sig'
            openssl(['dgst',{'RSA':'-sha1','RSA256':'-sha256','RSA512':'-sha512'}[algo],'-sign',str(self.private),'-out',str(s),str(p)])
            return gzip.compress(make_tar({f'.SIGN.{algo}.{NAME}':s.read_bytes()}),mtime=0)
    def fixture(self):
        loader=b'custom fixture loader only'
        data=gzip.compress(make_tar({'lib/ld-musl-armhf.so.1':loader}),mtime=0)
        info=f'pkgname = musl\npkgver = 1.2.6-r3\narch = armv7\ndatahash = {digest(data)}\n'.encode()
        ctl=gzip.compress(make_tar({'.PKGINFO':info}),mtime=0)
        apk=self.signed(ctl)+ctl+data
        q1='Q1'+base64.b64encode(hashlib.sha1(ctl).digest()).decode()
        idx=gzip.compress(make_tar({'APKINDEX':f'P:musl\nV:1.2.6-r3\nA:armv7\nC:{q1}\n\n'.encode()}),mtime=0)
        index=self.signed(idx)+idx
        return apk,index,loader
    def test_real_rsa_signatures_verify_synthetic_v2(self):
        apk,index,loader=self.fixture()
        r=audit_authenticity(apk,index,loader,self.folder,pins=self.pins,expected_loader_sha256=digest(loader))
        self.assertTrue(r['repository_and_package_signatures_cryptographically_verified_with_pinned_aports_keys'])
        self.assertFalse(r['patched_source_to_binary_equivalence_verified'])
    def test_wrong_key_blob_rejected(self):
        with self.assertRaisesRegex(Refusal,'BLOB_HASH_MISMATCH'):
            validate_pinned_key(NAME,self.public.read_bytes(),pins={NAME:'a'*40})
    def test_key_from_fixture_matches_test_git_pin(self):
        self.assertEqual(validate_pinned_key(NAME,self.public.read_bytes(),self.pins),self.pins[NAME])
    def test_tampered_signed_index_rejected(self):
        apk,index,loader=self.fixture()
        chunks = __import__('pw3_r3877_24_public_apk_loader_match').gzip_members(index)
        altered=chunks[0][0] + gzip.compress(make_tar({'APKINDEX':b'broken'}),mtime=0)
        with self.assertRaises(Refusal):
            audit_authenticity(apk,altered,loader,self.folder,pins=self.pins,expected_loader_sha256=digest(loader))
    def test_tampered_signature_rejected(self):
        apk,index,loader=self.fixture()
        chunks=__import__('pw3_r3877_24_public_apk_loader_match').gzip_members(index)
        bad=gzip.compress(make_tar({f'.SIGN.RSA.{NAME}':b'x'*256}),mtime=0) + chunks[1][0]
        with self.assertRaisesRegex(Refusal,'CRYPTOGRAPHIC_SIGNATURE'):
            audit_authenticity(apk,bad,loader,self.folder,pins=self.pins,expected_loader_sha256=digest(loader))
    def test_trusted_key_not_signature_key_rejected(self):
        other=b'-----BEGIN PUBLIC KEY-----\nAAAA\n-----END PUBLIC KEY-----\n'
        with self.assertRaises(Refusal): validate_pinned_key(NAME,other,self.pins)
    def test_unsigned_index_refused(self):
        _,index,_=self.fixture();parts=__import__('pw3_r3877_24_public_apk_loader_match').gzip_members(index)
        with self.assertRaisesRegex(Refusal,'UNSIGNED_OR_BAD_MEMBER_COUNT'):
            signature_segment(parts[1][0], 'INDEX')
    def test_unpinned_signer_refused(self):
        sig=gzip.compress(make_tar({'.SIGN.RSA.attacker.rsa.pub':b'z'*256}),mtime=0)
        other=gzip.compress(make_tar({'APKINDEX':b'entry'}),mtime=0)
        with self.assertRaisesRegex(Refusal,'UNRECOGNIZED_SIGNATURE_FORMAT'):
            signature_segment(sig+other,'INDEX')
    def test_no_device_access_default_flags(self):
        d=base();self.assertEqual(d['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(d['public_alpine_repository_signature_verified'])
        self.assertFalse(d['target_musl_runtime_verified'])
        self.assertEqual(d['kindle_ssh_sessions'],0)
    def test_missing_input_refuses(self):
        import contextlib,io
        with contextlib.redirect_stdout(io.StringIO()) as out:
            ret=main(['--apk','missing','--index','missing','--candidate-loader','missing','--key-dir','missing'])
        self.assertEqual(ret,2);self.assertEqual(json.loads(out.getvalue())['result'],'HOLD')
    def test_expected_key_pins_have_valid_git_shas(self):
        self.assertEqual(len(PINNED_KEYS),2)
        self.assertTrue(all(len(s)==40 for s in PINNED_KEYS.values()))
    def test_index_signature_is_bound_to_second_compressed_member(self):
        _,index,_=self.fixture();record=signature_segment(index,'INDEX')
        self.assertTrue(verify_with_openssl(record['signature'],record['signed_bytes'],self.public.read_bytes(),'RSA'))

if __name__=='__main__':unittest.main()
