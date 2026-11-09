"""R3877.20.1: regression for legitimate rootfs + ext3 / dual-root metadata."""
import unittest
from pathlib import Path
from pw3_r3877_20_analyze import analyze

RAW = Path(__file__).with_name('R3877_20_USER_OBSERVED_MOUNT_METADATA.txt').read_text()

class DualRootMetadataTests(unittest.TestCase):
    def check_not_bootable(self, result):
        self.assertEqual(result['immutable_hold'], 'NOT_BOOTABLE')
        self.assertFalse(result['recovery_verified'])
        self.assertFalse(result['bootloader_verified'])
        self.assertFalse(result['rootfs_backup_verified'])
        self.assertFalse(result['boot_performed'])
        self.assertFalse(result['raw_block_data_read'])
        self.assertFalse(result['firmware_write_performed'])
        self.assertFalse(result['device_files_written'])

    def test_user_observed_inventory_p1(self):
        r = analyze(RAW)
        self.assertEqual(r['milestone'], 'R3877.20.1')
        self.assertEqual(r['result'], 'PASS_MOUNT_MAPPING_METADATA_ONLY')
        self.assertEqual(r['hold_category'], 'NOT_BOOTABLE')
        self.assertTrue(r['root_backing_partition_verified'])
        i = r['inventory']
        self.assertEqual(i['root_partition_supported_by_direct_live_mount_metadata'], 'mmcblk0p1')
        self.assertEqual(i['root_partition_evidence_type'], 'LIVE_VFS_MOUNTINFO_PROC_MOUNTS_SYSFS_METADATA')
        self.assertFalse(i['root_metadata_ambiguous'])
        self.assertTrue(i['rootfs_pseudo_mount_observed'])
        self.assertTrue(i['rootfs_pseudo_mount_ignored_for_physical_root_crosscheck'])
        self.assertEqual(i['nonpseudo_proc_root_mount_count'], 1)
        self.assertFalse(i['boot_root_hint_is_runtime_proof'])
        self.check_not_bootable(r)

    def test_pseudo_proc_root_missing_still_match_direct_root(self):
        r = analyze(RAW.replace('proc_mount_root=rootfs|rootfs|rw\n','')
                    .replace('proc_mount_root_count=2','proc_mount_root_count=1'))
        self.assertTrue(r['root_backing_partition_verified'])
        self.assertFalse(r['inventory']['rootfs_pseudo_mount_observed'])
        self.check_not_bootable(r)

    def test_boot_hint_mismatch_not_used_as_mount_proof(self):
        r = analyze(RAW.replace('boot_root_hint=/dev/mmcblk0p1','boot_root_hint=/dev/mmcblk0p2'))
        self.assertTrue(r['root_backing_partition_verified'])
        self.assertEqual(r['inventory']['root_partition_supported_by_direct_live_mount_metadata'],'mmcblk0p1')
        self.assertFalse(r['inventory']['boot_root_hint_is_runtime_proof'])
        self.check_not_bootable(r)

    def test_sysfs_partition_mapping_missing(self):
        r = analyze(RAW.replace('sysfs_map=mmcblk0p1|179:1\n',''))
        self.assertFalse(r['root_backing_partition_verified'])
        self.check_not_bootable(r)

    def test_mismatched_mountinfo_device(self):
        r = analyze(RAW.replace('mountinfo_root=179:1','mountinfo_root=179:7'))
        self.assertFalse(r['root_backing_partition_verified'])
        self.check_not_bootable(r)

    def test_nonhint_live_root_p2_is_distinguished_from_boot_hint(self):
        r = analyze(RAW.replace('mountinfo_root=179:1','mountinfo_root=179:2'))
        self.assertEqual(r['inventory']['root_partition_supported_by_direct_live_mount_metadata'], 'mmcblk0p2')
        self.assertFalse(r['inventory']['boot_root_hint_is_runtime_proof'])
        self.check_not_bootable(r)

    def test_mismatched_mountinfo_fstype(self):
        r = analyze(RAW.replace('mountinfo_root=179:1|ext3','mountinfo_root=179:1|ext4'))
        self.assertFalse(r['root_backing_partition_verified'])
        self.check_not_bootable(r)

    def test_mismatched_read_only_mode(self):
        r = analyze(RAW.replace('mountinfo_root=179:1|ext3|/dev/root|/|ro','mountinfo_root=179:1|ext3|/dev/root|/|rw'))
        self.assertFalse(r['root_backing_partition_verified'])
        self.check_not_bootable(r)

    def test_mismatched_proc_device(self):
        r = analyze(RAW.replace('proc_mount_root=/dev/root|ext3|ro', 'proc_mount_root=/dev/mmcblk0p2|ext3|ro'))
        self.assertFalse(r['root_backing_partition_verified'])
        self.check_not_bootable(r)

    def test_extra_physical_proc_root_marks_ambiguous(self):
        r = analyze(RAW.replace('proc_mount_root_count=2','proc_mount_root=/dev/mmcblk0p2|ext3|ro\nproc_mount_root_count=3'))
        self.assertTrue(r['inventory']['root_metadata_ambiguous'])
        self.assertFalse(r['root_backing_partition_verified'])
        self.check_not_bootable(r)

    def test_duplicate_pseudo_proc_mount_marks_ambiguous(self):
        r = analyze(RAW.replace('proc_mount_root_count=2', 'proc_mount_root=rootfs|rootfs|rw\nproc_mount_root_count=3'))
        self.assertTrue(r['inventory']['root_metadata_ambiguous'])
        self.assertFalse(r['root_backing_partition_verified'])
        self.check_not_bootable(r)

    def test_extra_mountinfo_root_marks_ambiguous(self):
        r = analyze(RAW.replace('mountinfo_root_count=1', 'mountinfo_root=0:1|rootfs|rootfs|/|rw\nmountinfo_root_count=2'))
        self.assertTrue(r['inventory']['root_metadata_ambiguous'])
        self.assertFalse(r['root_backing_partition_verified'])
        self.check_not_bootable(r)

    def test_only_pseudo_proc_root_cannot_prove_partition(self):
        r = analyze(RAW.replace('proc_mount_root=/dev/root|ext3|ro\n','').replace('proc_mount_root_count=2','proc_mount_root_count=1'))
        self.assertFalse(r['root_backing_partition_verified'])
        self.check_not_bootable(r)

    def test_changed_proc_ro_against_mountinfo_ro(self):
        r=analyze(RAW.replace('proc_mount_root=/dev/root|ext3|ro','proc_mount_root=/dev/root|ext3|rw'))
        self.assertFalse(r['root_backing_partition_verified'])
        self.check_not_bootable(r)

    def test_redacted_unexpected_root_source(self):
        r=analyze(RAW.replace('mountinfo_root=179:1|ext3|/dev/root','mountinfo_root=179:1|ext3|OTHER_REDACTED'))
        self.assertFalse(r['root_backing_partition_verified'])
        self.check_not_bootable(r)

    def test_non_ext_filesystem_not_counted_block_root(self):
        r=analyze(RAW.replace('proc_mount_root=/dev/root|ext3|ro','proc_mount_root=/dev/root|tmpfs|ro')
                  .replace('mountinfo_root=179:1|ext3','mountinfo_root=179:1|tmpfs'))
        self.assertFalse(r['root_backing_partition_verified'])
        self.check_not_bootable(r)

    def test_full_cmdline_disclosure_rejected(self):
        r=analyze(RAW.replace('boot_root_hint=/dev/mmcblk0p1','boot_root_hint=console=tty1 password=bad'))
        self.assertEqual(r['result'],'HOLD')
        self.assertEqual(r['hold_category'],'UNREDACTED_CMDLINE_TOKEN')
        self.check_not_bootable(r)

    def test_missing_sentinel_is_hold(self):
        r=analyze(RAW.replace('R3877_20_MOUNT_MAPPING_COMPLETE',''))
        self.assertEqual(r['result'],'HOLD')
        self.check_not_bootable(r)

    def test_forged_count_is_hold(self):
        r=analyze(RAW.replace('proc_mount_root_count=2','proc_mount_root_count=1'))
        self.assertEqual(r['result'],'HOLD')
        self.assertEqual(r['hold_category'],'INCONSISTENT_MOUNT_COUNT')
        self.check_not_bootable(r)

if __name__ == '__main__':
    unittest.main()
