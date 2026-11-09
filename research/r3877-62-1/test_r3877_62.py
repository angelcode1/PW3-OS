import contextlib
import io
import json
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
import pw3_r3877_62_recovery_inventory as r

class Tests(unittest.TestCase):
    def test_default_hold_and_no_scan(self):
        with patch.object(r,'inventory',side_effect=AssertionError('unexpected scan')):
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                self.assertEqual(r.main([]),2)
        self.assertEqual(json.loads(buf.getvalue())['hold_category'],'EXPLICIT_LOCAL_DIRECTORY_REQUIRED')
        self.assertEqual(json.loads(buf.getvalue())['milestone'],'R3877.62.1')
    def test_no_classify_nonmatch(self):
        self.assertIsNone(r.classify('ordinary.txt'))
    def test_stock_image(self):
        self.assertEqual(r.classify('original_rootfs.img'),'stock_partition_image_candidate')
    def test_generic_image(self):
        self.assertEqual(r.classify('dump.img'),'image_or_dump_other')
    def test_rec_doc(self):
        self.assertEqual(r.classify('recovery-notes.md'),'recovery_document_candidate')
    def test_backup_zip(self):
        self.assertEqual(r.classify('pw3-backup.zip'),'backup_archive_candidate')
    def test_no_file_read_and_no_names(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'stock_rootfs.img').write_bytes(b'a')
            Path(d,'recovery.log').write_bytes(b'x')
            x=r.inventory(d)
            self.assertEqual(x['candidate_counts_by_category']['stock_partition_image_candidate'],1)
            self.assertFalse(x['raw_names_or_paths_published'])
            self.assertNotIn('rootfs',str(x))
    def test_subdir_depth(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'first');p.mkdir();(p/'backup.zip').write_bytes(b'x')
            self.assertEqual(r.inventory(d,max_depth=0)['regular_files_considered'],0)
            self.assertEqual(r.inventory(d,max_depth=1)['regular_files_considered'],1)
    def test_symlink_files_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            x=Path(d,'test');x.write_bytes(b'x')
            (Path(d)/'stock_kernel.img').symlink_to(x)
            y=r.inventory(d)
            self.assertEqual(y['symlink_entries_skipped'],1)
            self.assertFalse(y['candidate_counts_by_category'])
    def test_symlink_dirs_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            t=Path(d,'actual');t.mkdir();(t/'rootfs.img').write_bytes(b'x')
            (Path(d)/'linked').symlink_to(t,target_is_directory=True)
            self.assertEqual(r.inventory(d)['symlink_entries_skipped'],1)
    def test_symlink_root_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'a');p.mkdir();link=Path(d,'b');link.symlink_to(p,target_is_directory=True)
            with self.assertRaises(r.Hold):r.inventory(link)
    def test_file_cap(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(3):Path(d,f'{i}.bin').write_bytes(b'x')
            self.assertTrue(r.inventory(d,cap=1)['file_budget_exhausted'])
    def test_depth_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(r.Hold):r.inventory(d,max_depth=5)
    def test_filecap_rejects(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(r.Hold):r.inventory(d,cap=20001)
    def test_unknown_dir_hold(self):
        with contextlib.redirect_stdout(io.StringIO()) as buf:r.main(['--scan-root','/no-such-directory-123456'])
        self.assertEqual(json.loads(buf.getvalue())['result'],'HOLD')
    def test_no_privileged_features(self):
        x=r.preflight()
        for key in ('docker_used','network_access_performed','physical_device_access_performed','firmware_write_performed','boot_performed','recovery_verified'):
            self.assertFalse(x[key])
        self.assertEqual(x['immutable_hold'],'NOT_BOOTABLE')
    def test_metadata_only_cant_verify_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'rootfs.img').write_bytes(b'not a real rootfs')
            res=r.inventory(d)
            self.assertFalse(res['recovery_assets_authenticated'])
            self.assertFalse(res['recovery_procedure_tested'])
            self.assertFalse(res['file_hashes_verified'])
    def test_missing_skipped_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d,'.git');p.mkdir();(p/'stock_kernel.img').write_bytes(b'x')
            self.assertFalse(r.inventory(d)['candidate_counts_by_category'])

class MacAliasRegression(unittest.TestCase):
    def test_user_controlled_ancestor_symlink_still_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            real=base/'actual'; real.mkdir()
            child=real/'child';child.mkdir()
            alias=base/'alias';alias.symlink_to(real,target_is_directory=True)
            with self.assertRaisesRegex(r.Hold,'SYMLINK_IN_DIRECTORY_ANCESTRY'):
                r.inventory(alias/'child')

    def test_alias_acceptance_is_exact_and_resolved(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            real=base/'real';real.mkdir()
            child=real/'child';child.mkdir()
            alias=base/'macos_alias';alias.symlink_to(real,target_is_directory=True)
            # Inject one approved alias for this test; actual implementation
            # still requires a real /var or /tmp -> /private mapping on macOS.
            real_alias = r.approved_macos_system_alias
            with patch.object(r,'approved_macos_system_alias',side_effect=lambda p:p==alias or real_alias(p)):
                self.assertEqual(r.check_root(alias/'child'),child.resolve())
                self.assertEqual(r.inventory(alias/'child')['regular_files_considered'],0)

    def test_nested_symlink_under_approved_alias_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            real=base/'real';real.mkdir()
            elsewhere=base/'elsewhere';elsewhere.mkdir()
            alias=base/'macos_alias';alias.symlink_to(real,target_is_directory=True)
            nested=real/'nested';nested.symlink_to(elsewhere,target_is_directory=True)
            child=elsewhere/'child';child.mkdir()
            real_alias = r.approved_macos_system_alias
            with patch.object(r,'approved_macos_system_alias',side_effect=lambda p:p==alias or real_alias(p)):
                with self.assertRaisesRegex(r.Hold,'SYMLINK_IN_DIRECTORY_ANCESTRY'):
                    r.check_root(alias/'nested'/'child')

    def test_selected_scan_root_cannot_be_a_symlink_even_if_alias(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            real=base/'real';real.mkdir()
            alias=base/'macos_alias';alias.symlink_to(real,target_is_directory=True)
            with patch.object(r,'approved_macos_system_alias',return_value=True):
                with self.assertRaisesRegex(r.Hold,'DIRECTORY_MISSING_INVALID_OR_SYMLINK'):
                    r.check_root(alias)

    def test_untrusted_alias_never_permitted(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            real=base/'real';real.mkdir()
            alias=base/'fakevar';alias.symlink_to(real,target_is_directory=True)
            child=real/'child';child.mkdir()
            with patch.object(r.sys,'platform','darwin'):
                self.assertFalse(r.approved_macos_system_alias(alias))
                with self.assertRaisesRegex(r.Hold,'SYMLINK_IN_DIRECTORY_ANCESTRY'):
                    r.check_root(alias/'child')

    def test_dotdot_component_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            real=Path(d)
            with self.assertRaisesRegex(r.Hold,'PARENT_DIRECTORY_COMPONENT_UNVERIFIED'):
                r.check_root(real/'x'/'..')

    def test_relative_directory_path_is_supported(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            with patch('pathlib.Path.cwd',return_value=base):
                self.assertEqual(r.check_root(''),base.resolve())

    @unittest.skipUnless(sys.platform=='darwin','actual macOS /var symlink check')
    def test_real_macos_tempdir_alias(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(r.check_root(d),Path(d).resolve(strict=True))
        if Path('/var').is_symlink():
            self.assertEqual(r.check_root('/var/folders'),Path('/private/var/folders').resolve())

if __name__=='__main__':unittest.main()
