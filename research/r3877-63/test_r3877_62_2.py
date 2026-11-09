"""Host-only, Python 3.9 compatible tests. No Kindle, network, Docker or QEMU."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pw3_r3877_62_2_candidate_triage as m

class CandidateTriageTests(unittest.TestCase):
    def test_01_default_no_scan(self):
        with patch.object(m,'triage',side_effect=AssertionError('Unexpected scan')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(m.main([]),2)
        r=json.loads(output.getvalue())
        self.assertEqual(r['milestone'],'R3877.62.2')
        self.assertEqual(r['hold_category'],'EXPLICIT_LOCAL_DIRECTORY_REQUIRED')
        self.assertEqual(r['immutable_hold'],'NOT_BOOTABLE')
    def test_02_base_pinned(self): self.assertTrue(m.require_base())
    def test_03_research_zip_separated(self):
        self.assertEqual(m.category('pw3-r3877-61-getentropy-enosys.zip'), 'research_named_archive_candidate_not_authenticated_backup')
        self.assertEqual(m.category('pw3-os-r50-synthetic-evidence.tar.gz'), 'research_named_archive_candidate_not_authenticated_backup')
    def test_04_backup_zip_not_research(self):
        self.assertEqual(m.category('kindle-backup-2025.zip'),'nonresearch_named_backup_archive_candidate')
    def test_05_stock_img(self):
        self.assertEqual(m.category('original_mmcblk0p1.img'),'stock_partition_image_candidate')
    def test_06_generic_img(self): self.assertEqual(m.category('unlabeled.img'),'image_or_dump_other')
    def test_07_update_bin_not_restorable_backup(self):
        self.assertEqual(m.category('update_kindle_5.16.1.bin'), 'official_update_package_candidate_not_recovery_backup')
    def test_08_checksum(self):
        self.assertEqual(m.category('SHA256SUMS_R3877_61.txt'),'integrity_manifest_filename_candidate')
    def test_09_other_ignored(self): self.assertIsNone(m.category('video.mp4'))
    def test_10_archive_extension_require_match(self): self.assertIsNone(m.category('fresh-photos.zip'))
    def test_11_size_band(self):
        self.assertEqual([m.band(n) for n in (0,1,1024*1024,16*1024*1024,128*1024*1024)], list(m.BANDS))
    def test_12_report_counts_and_no_names(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'pw3-r3877-61-test.zip').write_bytes(b'x')
            (root/'kindle_backup.zip').write_bytes(b'123')
            (root/'stock_rootfs.img').write_bytes(b'abc')
            (root/'update_kindle.bin').write_bytes(b'zz')
            r=m.triage(root)
            self.assertEqual(r['candidate_count_total'],4)
            self.assertEqual(r['regular_files_considered'],4)
            self.assertTrue(r['bounded_scope_scan_complete'])
            self.assertEqual(r['candidate_counts_by_category']['research_named_archive_candidate_not_authenticated_backup'],1)
            self.assertFalse(r['candidate_file_contents_read'])
            self.assertFalse(r['raw_names_or_paths_published'])
            self.assertNotIn('kindle_backup.zip',repr(r))
            self.assertFalse(r['recovery_assets_authenticated'])
    def test_13_entry_budget(self):
        with tempfile.TemporaryDirectory() as d:
            for n in range(8): (Path(d)/('file%02d.txt'%n)).write_bytes(b'x')
            r=m.triage(d,max_entries=3)
            self.assertTrue(r['entry_budget_exhausted'])
            self.assertFalse(r['bounded_scope_scan_complete'])
    def test_14_candidate_budget(self):
        with tempfile.TemporaryDirectory() as d:
            for n in range(6): (Path(d)/('backup%02d.zip'%n)).write_bytes(b'x')
            r=m.triage(d,max_candidates=2)
            self.assertTrue(r['candidate_budget_exhausted'])
            self.assertFalse(r['bounded_scope_scan_complete'])
            self.assertEqual(r['candidate_count_total'],2)
    def test_15_does_not_limit_by_ordinary_file_count(self):
        with tempfile.TemporaryDirectory() as d:
            for n in range(55): (Path(d)/('ordinary%02d.log'%n)).write_bytes(b'x')
            (Path(d)/'stock_kernel.img').write_bytes(b'x')
            r=m.triage(d,max_entries=100,max_candidates=1)
            self.assertEqual(r['regular_files_considered'],56)
            self.assertTrue(r['bounded_scope_scan_complete'])
            self.assertEqual(r['candidate_count_total'],1)
    def test_16_symlink_files_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'data').write_bytes(b'abc')
            (Path(d)/'stock_kernel.img').symlink_to('data')
            r=m.triage(d)
            self.assertEqual(r['symlink_entries_skipped'],1)
            self.assertEqual(r['candidate_count_total'],0)
    def test_17_symlink_directories_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'real';target.mkdir()
            (target/'rootfs.img').write_bytes(b'abc')
            (Path(d)/'shortcut').symlink_to(target,target_is_directory=True)
            r=m.triage(d)
            self.assertEqual(r['symlink_entries_skipped'],1)
            self.assertEqual(r['candidate_count_total'],1)
    def test_18_depth_limit(self):
        with tempfile.TemporaryDirectory() as d:
            t=Path(d)/'deep';t.mkdir()
            (t/'backup.zip').write_bytes(b'abc')
            a=m.triage(d,max_depth=0)
            b=m.triage(d,max_depth=1)
            self.assertEqual(a['candidate_count_total'],0)
            self.assertEqual(b['candidate_count_total'],1)
            self.assertGreaterEqual(a['directory_entries_skipped'],1)
    def test_19_reject_symlink_scan_root(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'real';target.mkdir()
            link=Path(d)/'link';link.symlink_to(target,target_is_directory=True)
            with self.assertRaises(m.base.Hold):m.triage(link)
    def test_20_bounded_validation(self):
        with tempfile.TemporaryDirectory() as d:
            for kw in ({'max_depth':5},{'max_entries':0},{'max_entries':150001},{'max_candidates':0},{'max_candidates':10001}):
                with self.assertRaises(m.Hold):m.triage(d,**kw)
    def test_21_missing_root_is_hold(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            rc=m.main(['--scan-root','/some/path/that/does/not/exist/zz'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(output.getvalue())['result'],'HOLD')
    def test_22_metadata_only_no_open(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'stock_kernel.img').write_bytes(b'abc')
            with patch('builtins.open',side_effect=AssertionError('Contents read')):
                r=m.triage(d)
            self.assertEqual(r['candidate_count_total'],1)
    def test_23_no_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'recovery-notes.md').write_bytes(b'abc')
            with patch.object(Path,'write_bytes',side_effect=AssertionError('Writes must not occur')):
                r=m.triage(d)
            self.assertEqual(r['candidate_count_total'],1)
    def test_24_cli_remains_hold_with_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'stock_mmcblk0.img').write_bytes(b'x')
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code=m.main(['--scan-root',d,'--max-entries','1000'])
            result=json.loads(output.getvalue())
            self.assertEqual(code,2)
            self.assertEqual(result['result'],'HOLD')
            self.assertFalse(result['recovery_verified'])
            self.assertTrue(result['inventory']['bounded_scope_scan_complete'])
    def test_25_no_unbounded_features(self):
        source=Path(m.__file__).read_text()
        for needle in ['subprocess.', 'requests.', 'urllib.', 'paramiko', 'docker run', 'adb ', 'ssh ', 'shutil.copy', 'open(\'rb\')', 'write_bytes(', 'write_text(']:
            self.assertNotIn(needle,source)
    def test_26_macos_real_tmpdir_base_regression(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(m.triage(d)['bounded_scope_scan_complete'])

if __name__=='__main__':unittest.main()
