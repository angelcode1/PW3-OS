#!/usr/bin/env python3
"""R3877.56 offline tests only; no Docker, networking or Kindle."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pw3_r3877_56_busybox_package_inventory as mod

GOOD_DB=b'P:musl\nV:1.2.6-r3\nA:armv7\n\nP:busybox\nV:1.37.0-r31\nA:armv7\n\nP:foo\nV:0.1\nA:armv7\n'
GOOD_LIST=b'/bin/ash\n/bin/sh\n/usr/bin/awk\n/usr/bin/wget\n'
DUMMY_BIN={'linkage':{'busybox_sha256':'df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c','loader_sha256':'2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990','interpreter_path_matches_pinned_loader':True},'direct_getrandom_dynamic_import_present':False,'direct_getentropy_dynamic_import_present':False,'interesting_undefined_imports':{'syscall':True},'embedded_byte_marker_present':{'/dev/urandom':True}}

class MetadataTests(unittest.TestCase):
    def assertHold(self, fn, substr):
        with self.assertRaises(mod.AuditHold) as e:fn()
        self.assertIn(substr,str(e.exception))
    def test_01_apk_db_positive(self):
        self.assertEqual(mod.parse_apk_db(GOOD_DB)['installed_package_version'],'1.37.0-r31')
    def test_02_apk_db_crlf(self):
        self.assertEqual(mod.parse_apk_db(GOOD_DB.replace(b'\n',b'\r\n'))['installed_package_arch'],'armv7')
    def test_03_missing_busybox(self):
        self.assertHold(lambda:mod.parse_apk_db(b'P:musl\nV:1.2.6-r3\nA:armv7\n'),'MISSING_OR_DUPLICATED')
    def test_04_duplicate_package(self):
        self.assertHold(lambda:mod.parse_apk_db(GOOD_DB+b'\n'+GOOD_DB),'MISSING_OR_DUPLICATED')
    def test_05_wrong_version(self):
        self.assertHold(lambda:mod.parse_apk_db(GOOD_DB.replace(b'1.37.0-r31',b'1.37.0-r30')),'VERSION_DIFFERS')
    def test_06_wrong_arch(self):
        self.assertHold(lambda:mod.parse_apk_db(GOOD_DB.replace(b'V:1.37.0-r31\nA:armv7',b'V:1.37.0-r31\nA:aarch64')),'ARCH_UNEXPECTED')
    def test_07_duplicate_version_field(self):
        self.assertHold(lambda:mod.parse_apk_db(GOOD_DB.replace(b'V:1.37.0-r31',b'V:1.37.0-r31\nV:1.37.0-r31')),'DUPLICATE_RECORD_FIELD')
    def test_08_binary_nul_rejected(self):
        self.assertHold(lambda:mod.parse_apk_db(GOOD_DB+b'\0'),'INVALID_SIZE_OR_NUL')
    def test_09_invalid_utf8(self):
        self.assertHold(lambda:mod.parse_apk_db(GOOD_DB+b'\xff'),'NOT_UTF8')
    def test_10_apk_db_oversize(self):
        self.assertHold(lambda:mod.parse_apk_db(b'x'*(mod.MAX_INSTALLED+1)),'INVALID_SIZE_OR_NUL')
    def test_11_applet_list_positive(self):
        self.assertEqual(mod.parse_applet_list(GOOD_LIST)['listed_paths_count'],4)
    def test_12_seedrng_absent(self):
        self.assertFalse(mod.parse_applet_list(GOOD_LIST)['seedrng_listed'])
    def test_13_app_list_ash_required(self):
        self.assertHold(lambda:mod.parse_applet_list(b'/bin/sh\n'),'ASH_MISSING')
    def test_14_seedrng_conflict_hold(self):
        self.assertHold(lambda:mod.parse_applet_list(GOOD_LIST+b'/usr/sbin/seedrng\n'),'SEEDRNG_CONFLICTS')
    def test_15_applet_list_duplicate_path(self):
        self.assertHold(lambda:mod.parse_applet_list(GOOD_LIST+GOOD_LIST),'DUPLICATE_PATH')
    def test_16_applet_traversal(self):
        self.assertHold(lambda:mod.parse_applet_list(GOOD_LIST+b'/usr/bin/../a\n'),'INVALID_OR_DUPLICATE_PATH')
    def test_17_applet_whitespace(self):
        self.assertHold(lambda:mod.parse_applet_list(GOOD_LIST+b' /bin/foo\n'),'INVALID_LINE')
    def test_18_applet_backslash(self):
        self.assertHold(lambda:mod.parse_applet_list(GOOD_LIST+b'/bin/foo\\bar\n'),'INVALID_LINE')
    def test_19_applet_invalid_utf8(self):
        self.assertHold(lambda:mod.parse_applet_list(GOOD_LIST+b'/bin/\xff\n'),'NOT_ASCII')
    def test_20_applet_nul(self):
        self.assertHold(lambda:mod.parse_applet_list(GOOD_LIST+b'/bin/a\x00\n'),'INVALID_SIZE_OR_NUL')
    def test_21_applet_oversize(self):
        self.assertHold(lambda:mod.parse_applet_list(b'x'*(mod.MAX_LIST+1)),'INVALID_SIZE_OR_NUL')
    def test_22_app_list_relative_paths(self):
        self.assertTrue(mod.parse_applet_list(b'\n'.join(line.lstrip(b'/') for line in GOOD_LIST.splitlines())+b'\n')['ash_listed'])
    def test_23_app_list_hash(self):
        self.assertEqual(mod.parse_applet_list(GOOD_LIST)['sha256'],hashlib.sha256(GOOD_LIST).hexdigest())
    def test_24_app_list_no_proof_of_execution(self):
        self.assertTrue(mod.parse_applet_list(GOOD_LIST)['list_is_not_actual_binary_applet_execution'])

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir=Path(self.tmp.name).resolve()
        self.paths={x:self.dir/x for x in ('installed','listing','busybox','loader')}
        for key,path in self.paths.items():path.write_bytes(GOOD_DB if key=='installed' else GOOD_LIST if key=='listing' else b'ELF-SYNTHETIC-NOT_REAL')
    def audited(self):
        with patch.object(mod,'require_r54_code'),patch.object(mod.r54,'inspect_binary_pair',return_value=DUMMY_BIN):
            return mod.analyze(**self.paths)
    def test_25_synthetic_audit_positive(self):
        self.assertEqual(self.audited()['installed_package']['installed_package_version'],mod.EXPECTED_BUSYBOX_VERSION)
    def test_26_reproducibility_is_false(self):
        self.assertFalse(self.audited()['installed_recipe_binary_reproducibility_verified'])
    def test_27_compiled_inventory_not_claimed(self):
        self.assertFalse(self.audited()['actual_compiled_applet_table_verified'])
    def test_28_entropy_runtime_not_claimed(self):
        self.assertFalse(self.audited()['runtime_entropy_fallback_verified'])
    def test_29_vendor_runtime_not_claimed(self):
        self.assertFalse(self.audited()['vendor_kernel_syscalls_verified'])
    def test_30_no_docker_preflight(self):
        with patch.object(mod.base,'docker',side_effect=AssertionError('docker invoked')):
            self.assertEqual(mod.main([]),2)
    def test_31_no_partial_local_input(self):
        self.assertEqual(mod.main(['--installed-db',str(self.paths['installed'])]),2)
    def test_32_symlink_db_rejected(self):
        dest=self.dir/'installed_link'
        dest.symlink_to(self.paths['installed'])
        self.assertHold(lambda:mod.bounded(dest,mod.MAX_INSTALLED),'SYMLINK')
    def test_33_missing_list_holds(self):
        self.paths['listing'].unlink()
        self.assertHold(lambda:self.audited(),'INPUT_FILE_MISSING')
    def test_34_changed_version_holds(self):
        self.paths['installed'].write_bytes(GOOD_DB.replace(b'1.37.0-r31',b'1.37.0-r9'))
        self.assertHold(lambda:self.audited(),'VERSION_DIFFERS')
    def test_35_seedrng_listed_holds(self):
        self.paths['listing'].write_bytes(GOOD_LIST+b'/usr/sbin/seedrng\n')
        self.assertHold(lambda:self.audited(),'SEEDRNG_CONFLICTS')
    def test_36_run_local_pass_uses_synthetic_mock(self):
        with patch.object(mod,'require_r54_code'),patch.object(mod.r54,'inspect_binary_pair',return_value=DUMMY_BIN):
            r=mod.run_local(**self.paths)
        self.assertEqual(r['result'],mod.PASS)
        self.assertEqual(r['immutable_hold'],'NOT_BOOTABLE')
    def test_37_run_local_fail_closed(self):
        with patch.object(mod,'require_r54_code',side_effect=mod.AuditHold('PIN_CHANGED')):
            r=mod.run_local(**self.paths)
        self.assertEqual(r['result'],'HOLD')
        self.assertEqual(r['hold_category'],'PIN_CHANGED')
    def test_38_preflight_safe_flags(self):
        r=mod.preflight()
        for key in ('docker_used','arm_executable_launched','boot_performed','firmware_write_performed','physical_device_access_performed','recovery_verified'):
            self.assertFalse(r[key])
    def test_39_wrong_r54_auditor_hash_rejected(self):
        with patch.object(mod,'EXPECTED_R54_SOURCE_SHA256','0'*64):
            self.assertHold(mod.require_r54_code,'PINNED_R54_AUDITOR_CHANGED')
    def test_40_stop_hardening_rejects_rw_container(self):
        metadata=[{'HostConfig':{'ReadonlyRootfs':False,'CapDrop':['ALL'],
           'SecurityOpt':['no-new-privileges'],'PidsLimit':32}}]
        stub=type('R',(),{'stdout':json.dumps(metadata)})()
        with patch.object(mod.base,'inspect_stopped'), patch.object(mod.base,'docker',return_value=stub):
            self.assertHold(lambda:mod.check_stopped_isolation('a'*64),'HARDENING_UNVERIFIED')
    def assertHold(self, fn, substr):
        with self.assertRaises(mod.AuditHold) as e:fn()
        self.assertIn(substr,str(e.exception))

if __name__=='__main__':unittest.main()
