"""Synthetic, Mac-compatible offline tests; no live network/Docker/Kindle."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pw3_r3877_55_busybox_seedrng_source_audit as mod

SAMPLES={
 'alpine/APKBUILD':'pkgver=1.37.0\npkgrel=31\ncp "$_config" .config\ninstall -Dm755 busybox "$pkgdir"/bin/busybox\n',
 'alpine/busyboxconfig':'# CONFIG_SEEDRNG is not set\nCONFIG_ASH_RANDOM_SUPPORT=y\n',
 'alpine/busyboxconfig-extras':'# CONFIG_SEEDRNG is not set\n# CONFIG_ASH_RANDOM_SUPPORT is not set\n',
 'busybox/miscutils/seedrng.c':'//kbuild:lib-$(CONFIG_SEEDRNG) += seedrng.o\nret = getrandom(seed, len, GRND_NONBLOCK)\nret < 0 && errno == ENOSYS\nopen_read_close("/dev/urandom", seed, len)\n',
 'busybox/shell/random.c':'next_random(random_t *rnd)\nINIT_RANDOM_T(rnd, getpid(), monotonic_us())\n',
}


def prior():
    return {'milestone':'R3877.54','result':'PASS_PINNED_BUSYBOX_DIRECT_ELF_ENTROPY_INDICATORS_ONLY',
            'immutable_hold':'NOT_BOOTABLE','original_image_unchanged':True,'stopped_container_removed':True,
            'binary_audit':{
                'dynamic_import_table_readable':True,
                'direct_getrandom_dynamic_import_present':False,
                'direct_getentropy_dynamic_import_present':False,
                'interesting_undefined_imports':{'syscall':True},
                'embedded_byte_marker_present':{'/dev/urandom':True},
                'linkage':{'busybox_sha256':mod.BUSYBOX_HASH,'loader_sha256':mod.LOADER_HASH}}}

class R55Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='r55-')
        # macOS /var -> /private/var; tests should not feed symlink paths.
        self.root=Path(self.tmp.name).resolve()
        self.sources=self.root/'source';self.sources.mkdir()
        self.r54=self.root/'r54.json'
        self.r54.write_text(json.dumps(prior()))
        self.pins={k:('fixture','fixture',k,mod.git_blob(v.encode())) for k,v in SAMPLES.items()}
        for key,value in SAMPLES.items():
            dest=self.sources/key;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(value)
    def tearDown(self):self.tmp.cleanup()
    def audit(self):
        return mod.check_source(self.sources,pins=self.pins)
    def runner(self,*args):
        stdout=io.StringIO()
        with contextlib.redirect_stdout(stdout):rc=mod.main(args)
        return rc,json.loads(stdout.getvalue())
    def mutate(self,path,needle,new):
        f=self.sources/path;f.write_text(f.read_text().replace(needle,new))
        k=self.pins[path];self.pins[path]=(*k[:3],mod.git_blob(f.read_bytes()))
    def test_01_positive_source(self):self.assertEqual(self.audit()['verified_source_git_blob_count'],5)
    def test_02_seedrng_disabled_both(self):self.assertTrue(self.audit()['source_recipe_seedrng_disabled'])
    def test_03_upstream_fallback_not_install_proof(self):self.assertTrue(self.audit()['source_seedrng_fallback_not_enabled_by_pinned_alpine_recipe'])
    def test_04_ash_is_not_crypto(self):self.assertTrue(self.audit()['ash_random_is_not_a_cryptographic_entropy_fallback'])
    def test_05_installed_recipe_unverified(self):self.assertFalse(self.audit()['installed_busybox_exact_recipe_build_verified'])
    def test_06_check_prior_pass(self):self.assertTrue(mod.check_prior(self.r54)['prior_busybox_imports_syscall'])
    def test_07_no_input_hold(self):
        code,r=self.runner();self.assertEqual(code,2);self.assertEqual(r['result'],'HOLD');self.assertFalse(r['docker_used'])
    def test_08_mismatched_hash(self):
        (self.sources/'alpine/APKBUILD').write_text('tampered')
        with self.assertRaisesRegex(mod.AuditHold,'GIT_BLOB_MISMATCH'):self.audit()
    def test_09_missing_source(self):
        (self.sources/'busybox/shell/random.c').unlink()
        with self.assertRaisesRegex(mod.AuditHold,'INPUT_MISSING'):self.audit()
    def test_10_source_symlink(self):
        p=self.sources/'busybox/shell/random.c';p.unlink();p.symlink_to(self.sources/'alpine/APKBUILD')
        with self.assertRaisesRegex(mod.AuditHold,'INPUT_MISSING_OR_SYMLINK'):self.audit()
    def test_11_wrong_busybox_version(self):
        self.mutate('alpine/APKBUILD','pkgver=1.37.0','pkgver=1.38.0')
        with self.assertRaisesRegex(mod.AuditHold,'RECIPE_VERSION'):self.audit()
    def test_12_wrong_busybox_rel(self):
        self.mutate('alpine/APKBUILD','pkgrel=31','pkgrel=30')
        with self.assertRaisesRegex(mod.AuditHold,'RECIPE_VERSION'):self.audit()
    def test_13_config_no_build_link(self):
        self.mutate('alpine/APKBUILD','cp "$_config" .config','false')
        with self.assertRaisesRegex(mod.AuditHold,'CONFIG_LINKAGE'):self.audit()
    def test_14_normal_seedrng_enabled_is_hold(self):
        self.mutate('alpine/busyboxconfig','# CONFIG_SEEDRNG is not set','CONFIG_SEEDRNG=y')
        with self.assertRaisesRegex(mod.AuditHold,'SEEDRNG_NOT_DISABLED'):self.audit()
    def test_15_extras_seedrng_enabled_is_hold(self):
        self.mutate('alpine/busyboxconfig-extras','# CONFIG_SEEDRNG is not set','CONFIG_SEEDRNG=y')
        with self.assertRaisesRegex(mod.AuditHold,'SEEDRNG_NOT_DISABLED'):self.audit()
    def test_16_ash_disabled_change_is_hold(self):
        self.mutate('alpine/busyboxconfig','CONFIG_ASH_RANDOM_SUPPORT=y','# CONFIG_ASH_RANDOM_SUPPORT is not set')
        with self.assertRaisesRegex(mod.AuditHold,'NORMAL_ASH_RANDOM'):self.audit()
    def test_17_extra_ash_enabled_change_is_hold(self):
        self.mutate('alpine/busyboxconfig-extras','# CONFIG_ASH_RANDOM_SUPPORT is not set','CONFIG_ASH_RANDOM_SUPPORT=y')
        with self.assertRaisesRegex(mod.AuditHold,'EXTRAS_ASH_RANDOM'):self.audit()
    def test_18_missing_fallback_is_hold(self):
        self.mutate('busybox/miscutils/seedrng.c','errno == ENOSYS','errno == EACCES')
        with self.assertRaisesRegex(mod.AuditHold,'UPSTREAM_SEEDRNG_SOURCE'):self.audit()
    def test_19_missing_shell_source_is_hold(self):
        self.mutate('busybox/shell/random.c','next_random(random_t *rnd)','next_random2(random_t *rnd)')
        with self.assertRaisesRegex(mod.AuditHold,'UPSTREAM_ASH_RANDOM_SOURCE'):self.audit()
    def test_20_prior_hash_wrong_is_hold(self):
        r=prior();r['binary_audit']['linkage']['busybox_sha256']='0'*64;self.r54.write_text(json.dumps(r))
        with self.assertRaisesRegex(mod.AuditHold,'PINNED_BINARY_IDENTITY'):mod.check_prior(self.r54)
    def test_21_prior_missing_syscall_is_hold(self):
        r=prior();r['binary_audit']['interesting_undefined_imports']['syscall']=False;self.r54.write_text(json.dumps(r))
        with self.assertRaisesRegex(mod.AuditHold,'ENTROPY_INDICATORS'):mod.check_prior(self.r54)
    def test_22_prior_missing_urandom_marker_is_hold(self):
        r=prior();r['binary_audit']['embedded_byte_marker_present']['/dev/urandom']=False;self.r54.write_text(json.dumps(r))
        with self.assertRaisesRegex(mod.AuditHold,'ENTROPY_INDICATORS'):mod.check_prior(self.r54)
    def test_23_prior_status_tamper_is_hold(self):
        r=prior();r['result']='PASS_OTHER';self.r54.write_text(json.dumps(r))
        with self.assertRaisesRegex(mod.AuditHold,'PRIOR_R54_RESULT'):mod.check_prior(self.r54)
    def test_24_prior_image_cleanup_false_is_hold(self):
        r=prior();r['stopped_container_removed']=False;self.r54.write_text(json.dumps(r))
        with self.assertRaisesRegex(mod.AuditHold,'ISOLATION'):mod.check_prior(self.r54)
    def test_25_default_has_not_bootable(self):
        rc,r=self.runner();self.assertEqual(r['immutable_hold'],'NOT_BOOTABLE')
    def test_26_sources_audited_before_prior(self):
        self.assertEqual(self.audit()['source_recipe_busybox_version'],'1.37.0-r31')
    def test_27_unknown_prior_import_is_hold(self):
        r=prior();r['binary_audit']['direct_getrandom_dynamic_import_present']=None;self.r54.write_text(json.dumps(r))
        with self.assertRaisesRegex(mod.AuditHold,'IMPORT_EVIDENCE'):mod.check_prior(self.r54)
    def test_28_exact_git_pins_are_fixed(self):
        self.assertEqual(mod.PINNED['alpine/busyboxconfig'][3],'f94784573735b83ad7129c92ef37c170a676bf8e')
    def test_29_github_origin_is_pinned(self):
        self.assertEqual(mod.ALPINE_REV,'35f5eb2864e50dd4448758d31f3e2a32f733ab84')
    def test_30_missing_prior_is_hold(self):
        self.r54.unlink()
        with self.assertRaisesRegex(mod.AuditHold,'INPUT_MISSING'):mod.check_prior(self.r54)

if __name__=='__main__':unittest.main()