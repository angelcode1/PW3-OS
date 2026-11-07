"""R3877.19.1 regression tests: boot area names, malformed records, safe metadata limits."""
import unittest
from pathlib import Path
from pw3_r3877_19_analyze import analyze, block_device_kind

RAW=Path(__file__).with_name('R3877_19_USER_MAC_STORAGE_RAW.txt').read_text()

class R3877191(unittest.TestCase):
    def test_exact_user_inventory_passes(self):
        result=analyze(RAW)
        self.assertEqual(result['result'],'PASS_STORAGE_METADATA_ONLY')
        self.assertEqual(result['milestone'],'R3877.19.1')
        self.assertEqual(result['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(result['recovery_verified'])
        self.assertFalse(result['rootfs_backup_verified'])
        self.assertFalse(result['bootloader_verified'])
        self.assertFalse(result['root_backing_partition_verified'])
        self.assertFalse(result['bootloader_location_verified'])
        self.assertFalse(result['emmc_boot_area_contents_read'])
        self.assertFalse(result['raw_block_or_mtd_data_read'])
    def test_emmc_areas_not_classified_as_user_partitions(self):
        parts=analyze(RAW)['inventory']['partitions']
        boot={p['name']:p for p in parts if p['kind']=='EMMC_BOOT_AREA'}
        self.assertEqual(set(boot), {'mmcblk0boot0','mmcblk0boot1'})
        self.assertEqual([v['size_1k_blocks'] for v in boot.values()], [4096,4096])
    def test_known_partition_sizes(self):
        p={x['name']: x for x in analyze(RAW)['inventory']['partitions']}
        self.assertEqual(len(p),7)
        self.assertEqual(p['mmcblk0']['size_1k_blocks'],3817472)
        self.assertEqual(p['mmcblk0p4']['size_1k_blocks'],3192832)
        self.assertEqual(p['mmcblk0p1']['kind'],'EMMC_USER_AREA_PARTITION')
    def test_rootfs_does_not_infer_root_partition(self):
        d=analyze(RAW)
        self.assertTrue(d['inventory']['root_block_device_not_identified_from_rootfs'])
        self.assertEqual(d['inventory']['root_device'],'rootfs')
        self.assertEqual(d['inventory']['root_fstype'],'rootfs')
        self.assertFalse(d['inventory']['root_mount_read_only'])
        self.assertFalse(d['root_backing_partition_verified'])
    def test_both_boot_areas_reported(self):
        d=analyze(RAW)
        self.assertEqual(d['inventory']['emmc_boot_area_names'],['mmcblk0boot0','mmcblk0boot1'])
    def test_boot2_disallowed(self):
        self.assertEqual(analyze(RAW.replace('mmcblk0boot1','mmcblk0boot2'))['hold_category'],'INVALID_PARTITION_RECORD')
    def test_rpmb_disallowed(self):
        self.assertEqual(analyze(RAW.replace('mmcblk0boot1','mmcblk0rpmb'))['hold_category'],'INVALID_PARTITION_RECORD')
    def test_malformed_major_disallowed(self):
        self.assertEqual(analyze(RAW.replace('mmcblk0boot1,179,16','mmcblk0boot1,abc,16'))['hold_category'],'INVALID_PARTITION_RECORD')
    def test_missing_boot_area_not_required_for_pass(self):
        d=analyze(RAW.replace('partition=mmcblk0boot1,179,16,4096\n',''))
        self.assertEqual(d['result'],'PASS_STORAGE_METADATA_ONLY')
        self.assertEqual(d['inventory']['emmc_boot_area_names'],['mmcblk0boot0'])
    def test_duplicate_boot_area_rejected(self):
        extra='partition=mmcblk0boot0,179,8,4096\n'
        d=analyze(RAW.replace('mtd_status=NOT_EXPOSED',extra+'mtd_status=NOT_EXPOSED'))
        self.assertEqual(d['hold_category'],'DUPLICATE_PARTITION_NAME')
    def test_clearly_wrong_root_not_hardcoded(self):
        d=analyze(RAW.replace('root_device=rootfs','root_device=/dev/mmcblk0p1').replace('root_fstype=rootfs','root_fstype=ext3'))
        self.assertEqual(d['result'],'PASS_STORAGE_METADATA_ONLY')
        self.assertFalse(d['inventory']['root_block_device_not_identified_from_rootfs'])
    def test_sentinel_loss_still_hold(self):
        self.assertEqual(analyze(RAW.replace('R3877_19_READ_ONLY_STORAGE_COMPLETE',''))['result'],'HOLD')
    def test_fail_closed_wrong_kernel(self):
        self.assertEqual(analyze(RAW.replace('3.0.35-lab126','6.6.0'))['result'],'HOLD')
    def test_kind_function(self):
        self.assertEqual(block_device_kind('mmcblk1boot0'),'EMMC_BOOT_AREA')
        self.assertEqual(block_device_kind('mmcblk0'),'EMMC_USER_AREA_DEVICE')
        self.assertEqual(block_device_kind('sda3'),'OTHER_BLOCK_DEVICE')

if __name__=='__main__': unittest.main()
