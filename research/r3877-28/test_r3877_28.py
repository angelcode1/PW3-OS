"""R3877.28 synthetic host-only safety and metadata parser regression suite."""
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

import pw3_r3877_28_build_environment_inputs as r28
import pw3_r3877_26_aports_input_audit as r26

PINS=json.loads(Path(r28.__file__).with_name(r28.PINS).read_text())

def tar_gzip(files):
    b=io.BytesIO()
    with tarfile.open(fileobj=b,mode='w') as t:
        for name,data in files.items():
            ti=tarfile.TarInfo(name)
            ti.size=len(data)
            ti.mode=0o644
            t.addfile(ti,io.BytesIO(data))
    return gzip.compress(b.getvalue())

def apk(pkginfo):
    return tar_gzip({'.SIGN.RSA.example':b'a'*256})+tar_gzip({'.PKGINFO':pkginfo})+tar_gzip({'lib/ld-musl-armhf.so.1':b'fake binary'})

BASE=b'pkgname = musl\npkgver = 1.2.6-r3\narch = armv7\norigin = musl\nbuilddate = 1794000000\ncommit = '+r28.EXPECTED_COMMIT.encode()+b'\n'

class RecipeTests(unittest.TestCase):
    def test_full_pins_valid(self):
        self.assertEqual(len(r28.safe_pins(PINS)),5)
    def test_snapshot_changed_rejected(self):
        x=copy.deepcopy(PINS);x['alpine_aports_commit']='0'*40
        with self.assertRaisesRegex(r26.AuditHold,'UNEXPECTED_APORTS_SNAPSHOT'):r28.safe_pins(x)
    def test_expected_tree_changed_rejected(self):
        x=copy.deepcopy(PINS);x['expected_patched_tree_sha256']='0'*64
        with self.assertRaisesRegex(r26.AuditHold,'UNEXPECTED_PATCHED_TREE_PIN'):r28.safe_pins(x)
    def test_pin_name_set_changed_rejected(self):
        x=copy.deepcopy(PINS);x['snapshot_recipe_git_blobs'].pop('gcc')
        with self.assertRaisesRegex(r26.AuditHold,'RECIPE_SET_INVALID'):r28.safe_pins(x)
    def test_pin_sha_changed_rejected(self):
        x=copy.deepcopy(PINS);x['snapshot_recipe_git_blobs']['gcc']['git_blob_sha1']='0'*40
        with self.assertRaisesRegex(r26.AuditHold,'RECIPE_PIN_VALUES_MISMATCH'):r28.safe_pins(x)
    def test_recipe_version_parsed(self):
        self.assertEqual(r28.pkgver_from_recipe(b'pkgname=make\npkgver=4.4.1\npkgrel=4\n'),'4.4.1-r4')
    def test_dynamic_version_rejected(self):
        with self.assertRaisesRegex(r26.AuditHold,'RECIPE_VERSION_NOT_LITERAL'):
            r28.pkgver_from_recipe(b'pkgver=$VERSION\npkgrel=1\n')
    def test_synthetic_recipe_pins_verified(self):
        with tempfile.TemporaryDirectory() as d:
            raw=b'pkgname=make\npkgver=4.4.1\npkgrel=4\n'
            Path(d,'make.APKBUILD').write_bytes(raw)
            pins={'make':{'git_blob_sha1':r26.git_blob(raw),'version':'4.4.1-r4'}}
            self.assertFalse(r28.check_recipes(Path(d),pins)['make']['historical_builder_package_version_verified'])
    def test_synthetic_recipe_modified_fails(self):
        with tempfile.TemporaryDirectory() as d:
            raw=b'pkgname=make\npkgver=4.4.1\npkgrel=4\n'
            Path(d,'make.APKBUILD').write_bytes(raw+b'#altered\n')
            pins={'make':{'git_blob_sha1':r26.git_blob(raw),'version':'4.4.1-r4'}}
            with self.assertRaisesRegex(r26.AuditHold,'RECIPE_GIT_BLOB_MISMATCH'):
                r28.check_recipes(Path(d),pins)
    def test_missing_recipe_fails(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(r26.AuditHold,'RECIPE_FILE_MISSING_OR_SYMLINK'):
                r28.check_recipes(Path(d),{'gcc':{'git_blob_sha1':'0'*40,'version':'1-r0'}})
    def test_symlink_recipe_fails(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'real').write_text('pkgver=1\npkgrel=1\n')
            Path(d,'gcc.APKBUILD').symlink_to('real')
            with self.assertRaisesRegex(r26.AuditHold,'RECIPE_FILE_MISSING_OR_SYMLINK'):
                r28.check_recipes(Path(d),{'gcc':{'git_blob_sha1':'0'*40,'version':'1-r0'}})

class PackageInfoTests(unittest.TestCase):
    def test_valid_build_metadata(self):
        i=r28.read_signed_package_info(apk(BASE))
        self.assertTrue(i['declared_source_commit_matches_pinned_snapshot'])
        self.assertEqual(i['declared_builddate_utc_epoch'],'1794000000')
    def test_missing_commit_is_unknown_not_false(self):
        i=r28.read_signed_package_info(apk(BASE.split(b'commit = ')[0]))
        self.assertIsNone(i['declared_source_commit_matches_pinned_snapshot'])
        self.assertFalse(i['package_commit_field_present'])
    def test_changed_commit_not_claimed_matched(self):
        i=r28.read_signed_package_info(apk(BASE.replace(r28.EXPECTED_COMMIT.encode(),b'1'*40)))
        self.assertFalse(i['declared_source_commit_matches_pinned_snapshot'])
    def test_duplicate_commit_rejected(self):
        with self.assertRaisesRegex(r26.AuditHold,'PKGINFO_DUPLICATE_commit'):
            r28.read_signed_package_info(apk(BASE+b'commit = '+b'0'*40+b'\n'))
    def test_bad_commit_rejected(self):
        with self.assertRaisesRegex(r26.AuditHold,'PKGINFO_COMMIT_FORMAT_INVALID'):
            r28.read_signed_package_info(apk(BASE.replace(r28.EXPECTED_COMMIT.encode(),b'abc')))
    def test_bad_date_rejected(self):
        with self.assertRaisesRegex(r26.AuditHold,'PKGINFO_BUILD_DATE_INVALID'):
            r28.read_signed_package_info(apk(BASE.replace(b'1794000000',b'bad')))
    def test_wrong_arch_rejected(self):
        with self.assertRaisesRegex(r26.AuditHold,'PKGINFO_PACKAGE_IDENTITY_MISMATCH'):
            r28.read_signed_package_info(apk(BASE.replace(b'armv7',b'aarch64')))
    def test_wrong_origin_rejected(self):
        with self.assertRaisesRegex(r26.AuditHold,'PKGINFO_ORIGIN_DIFFERENT'):
            r28.read_signed_package_info(apk(BASE.replace(b'origin = musl',b'origin = glibc')))
    def test_missing_control_rejected(self):
        archive=tar_gzip({'a':b'sig'})+tar_gzip({'x':b'noinfo'})+tar_gzip({'file':b'bytes'})
        with self.assertRaisesRegex(r26.AuditHold,'PKGINFO_NOT_IN_CONTROL'):
            r28.read_signed_package_info(archive)
    def test_nonutf8_rejected(self):
        with self.assertRaisesRegex(r26.AuditHold,'PKGINFO_NOT_UTF8'):
            r28.read_signed_package_info(apk(BASE+b'\xff'))
    def test_buildhost_not_leaked(self):
        i=r28.read_signed_package_info(apk(BASE+b'buildhost = sensitive-example\n'))
        self.assertNotIn('buildhost',i)
    def test_malformed_apk_rejected(self):
        with self.assertRaises(Exception):r28.read_signed_package_info(b'not an apk')

class SafetyTests(unittest.TestCase):
    def test_no_args_fail_closed_json(self):
        p=subprocess.run([sys.executable,'-B',str(Path(r28.__file__).resolve())],capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        result=json.loads(p.stdout)
        self.assertEqual(result['result'],'HOLD')
        self.assertEqual(result['immutable_hold'],'NOT_BOOTABLE')
        self.assertEqual(result['kindle_ssh_sessions'],0)
        self.assertFalse(result['signed_loader_rebuild_performed'])
        self.assertFalse(result['historical_alpine_builder_toolchain_versions_verified'])
    def test_safety_base_fields(self):
        b=r28.base()
        self.assertFalse(b['target_musl_runtime_verified'])
        self.assertFalse(b['firmware_write_performed'])
        self.assertFalse(b['binary_provenance_to_patched_source_verified'])
    def test_digests_pinned(self):
        self.assertEqual(len(r28.EXPECTED_TREE),64)
        self.assertEqual(r28.EXPECTED_TREE,PINS['expected_patched_tree_sha256'])

if __name__=='__main__': unittest.main()
