"""Offline regression tests. No connection to a Kindle, no filesystem writes."""
import unittest
from pathlib import Path
from pw3_r3877_20_analyze import analyze, base

ROOTFS='''R3877_20_MOUNT_MAPPING_BEGIN
kernel_release=3.0.35-lab126
machine=armv7l
boot_root_hint=/dev/mmcblk0p1
boot_root_hint_count=1
proc_mount_root=rootfs|rootfs|rw
proc_mount_root_count=1
mountinfo_root=0:1|rootfs|rootfs|/|rw
selected_mount=/mnt/us|179:4|vfat|/dev/mmcblk0p4
mountinfo_root_count=1
selected_mount_count=1
sysfs_map=mmcblk0p1|179:1
sysfs_map=mmcblk0p2|179:2
sysfs_map=mmcblk0p3|179:3
sysfs_map=mmcblk0p4|179:4
R3877_20_MOUNT_MAPPING_COMPLETE
'''
PHYSICAL = ROOTFS.replace('rootfs|rootfs|rw','/dev/mmcblk0p1|ext3|ro').replace('0:1|rootfs|rootfs|/|rw','179:1|ext3|/dev/mmcblk0p1|/|ro')

class MountMappingTests(unittest.TestCase):
    def test_rootfs_pass_but_unverified(self):
        d=analyze(ROOTFS)
        self.assertEqual(d['result'],'PASS_MOUNT_MAPPING_METADATA_ONLY')
        self.assertEqual(d['hold_category'],'NOT_BOOTABLE')
        self.assertFalse(d['root_backing_partition_verified'])
        self.assertIsNone(d['inventory']['root_partition_supported_by_direct_live_mount_metadata'])
        self.assertTrue(d['inventory']['rootfs_pseudo_mount_prevents_partition_inference'])
    def test_root_cmdline_not_proof(self):
        self.assertFalse(analyze(ROOTFS)['inventory']['boot_root_hint_is_runtime_proof'])
    def test_expected_kernel_only(self):
        self.assertEqual(analyze(ROOTFS.replace('3.0.35-lab126','6.6.0'))['hold_category'],'WRONG_TARGET')
    def test_valid_physical_crosscheck(self):
        d=analyze(PHYSICAL)
        self.assertTrue(d['root_backing_partition_verified'])
        self.assertEqual(d['inventory']['root_partition_supported_by_direct_live_mount_metadata'],'mmcblk0p1')
        self.assertFalse(d['bootloader_location_verified'])
        self.assertFalse(d['recovery_verified'])
    def test_physical_mismatch_sysfs(self):
        d=analyze(PHYSICAL.replace('sysfs_map=mmcblk0p1|179:1\n',''))
        self.assertFalse(d['root_backing_partition_verified'])
    def test_physical_mismatch_proc(self):
        d=analyze(PHYSICAL.replace('proc_mount_root=/dev/mmcblk0p1|ext3|ro','proc_mount_root=rootfs|rootfs|rw'))
        self.assertFalse(d['root_backing_partition_verified'])
    def test_physical_mismatch_mountinfo_source(self):
        d=analyze(PHYSICAL.replace('179:1|ext3|/dev/mmcblk0p1|/|ro','179:1|ext3|rootfs|/|ro'))
        self.assertFalse(d['root_backing_partition_verified'])
    def test_physical_mismatch_mount_ro(self):
        d=analyze(PHYSICAL.replace('179:1|ext3|/dev/mmcblk0p1|/|ro','179:1|ext3|/dev/mmcblk0p1|/|rw'))
        self.assertFalse(d['root_backing_partition_verified'])
    def test_more_than_one_root_prevents_inference(self):
        d=analyze(PHYSICAL.replace('mountinfo_root_count=1', 'mountinfo_root=0:1|rootfs|rootfs|/|rw\nmountinfo_root_count=2'))
        self.assertFalse(d['root_backing_partition_verified'])
        self.assertTrue(d['inventory']['root_metadata_ambiguous'])
    def test_missing_mountinfo_root_not_pass_proof(self):
        s=ROOTFS.replace('mountinfo_root=0:1|rootfs|rootfs|/|rw\n','').replace('mountinfo_root_count=1','mountinfo_root_count=0')
        d=analyze(s)
        self.assertEqual(d['result'],'PASS_MOUNT_MAPPING_METADATA_ONLY')
        self.assertFalse(d['root_backing_partition_verified'])
    def test_duplicate_key(self):
        d=analyze(ROOTFS.replace('machine=armv7l','machine=armv7l\nmachine=armv7l'))
        self.assertEqual(d['hold_category'],'DUPLICATE_SCALAR')
    def test_bad_source_redacted(self):
        d=analyze(ROOTFS.replace('rootfs|rootfs|rw','/dev/mapper/private|rootfs|rw'))
        self.assertEqual(d['hold_category'],'INVALID_ROOT_PROC_MOUNT')
    def test_arbitrary_mountpoint_rejected(self):
        d=analyze(ROOTFS.replace('/mnt/us','/home/secret'))
        self.assertEqual(d['hold_category'],'INVALID_SELECTED_MOUNT')
    def test_cmdline_whole_rejected(self):
        d=analyze(ROOTFS.replace('boot_root_hint=/dev/mmcblk0p1','boot_root_hint=console=ttymxc0 password=XYZ'))
        self.assertEqual(d['hold_category'],'UNREDACTED_CMDLINE_TOKEN')
    def test_duplicate_root_hints_rejected(self):
        d=analyze(ROOTFS.replace('boot_root_hint_count=1','boot_root_hint_count=2'))
        self.assertEqual(d['hold_category'],'INCONSISTENT_HINT_COUNT')
    def test_multiple_root_hints_redacted(self):
        d=analyze(ROOTFS.replace('boot_root_hint=/dev/mmcblk0p1','boot_root_hint=MULTIPLE_REDACTED').replace('boot_root_hint_count=1','boot_root_hint_count=2'))
        self.assertEqual(d['result'],'PASS_MOUNT_MAPPING_METADATA_ONLY')
        self.assertFalse(d['root_backing_partition_verified'])
    def test_bad_sysfs_mapping(self):
        d=analyze(ROOTFS.replace('sysfs_map=mmcblk0p1|179:1','sysfs_map=mmcblk0p1|179:5'))
        self.assertEqual(d['hold_category'],'UNEXPECTED_SYSFS_MAJOR_MINOR')
    def test_duplicate_sysfs_mapping(self):
        d=analyze(ROOTFS.replace('sysfs_map=mmcblk0p1|179:1','sysfs_map=mmcblk0p1|179:1\nsysfs_map=mmcblk0p1|179:1'))
        self.assertEqual(d['hold_category'],'INVALID_SYSFS_MAPPING')
    def test_missing_sentinel(self):
        self.assertEqual(analyze(ROOTFS.replace('R3877_20_MOUNT_MAPPING_COMPLETE',''))['result'],'HOLD')
    def test_duplicate_sentinel(self):
        self.assertEqual(analyze(ROOTFS+ROOTFS)['result'],'HOLD')
    def test_extra_binary(self):
        self.assertEqual(analyze(ROOTFS+'\x00')['hold_category'],'EXCESS_OR_BINARY_INPUT')
    def test_extra_long(self):
        self.assertEqual(analyze(ROOTFS+'a'*65536)['hold_category'],'EXCESS_OR_BINARY_INPUT')
    def test_count_consistency(self):
        d=analyze(ROOTFS.replace('selected_mount_count=1','selected_mount_count=2'))
        self.assertEqual(d['hold_category'],'INCONSISTENT_MOUNT_COUNT')
    def test_unknown_record(self):
        d=analyze(ROOTFS.replace('kernel_release=','bad=value\nkernel_release='))
        self.assertEqual(d['hold_category'],'UNKNOWN_RECORD')
    def test_no_root_records(self):
        d=analyze(ROOTFS.replace('proc_mount_root=rootfs|rootfs|rw\n','').replace('proc_mount_root_count=1','proc_mount_root_count=0').replace('mountinfo_root=0:1|rootfs|rootfs|/|rw\n','').replace('mountinfo_root_count=1','mountinfo_root_count=0'))
        self.assertEqual(d['hold_category'],'ROOT_METADATA_NOT_PRESENT')
    def test_user_baseline_roots_are_not_resolved(self):
        # Mirrors observed R3877.19.1 rootfs; no inference from partitions.
        d=analyze(ROOTFS)
        self.assertFalse(d['rootfs_backup_verified'])
        self.assertFalse(d['bootloader_verified'])
        self.assertFalse(d['alpine_runtime_verified'])
        self.assertFalse(d['kernel_syscall_compatibility_verified'])
    def test_verifier_does_not_decode_boot_partition(self):
        d=analyze(PHYSICAL)
        self.assertFalse(d['raw_block_data_read'])
        self.assertFalse(d['device_files_written'])
        self.assertFalse(d['firmware_write_performed'])
        self.assertFalse(d['boot_performed'])
    def test_fixture_types(self):
        self.assertEqual(base()['immutable_hold'],'NOT_BOOTABLE')
        self.assertEqual(len([x for x in ROOTFS.splitlines() if x.startswith('sysfs_map=')]),4)

if __name__=='__main__':
    unittest.main()
