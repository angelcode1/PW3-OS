import unittest
from pw3_r3877_19_analyze import analyze

GOOD='''R3877_19_READ_ONLY_STORAGE_BEGIN
kernel_release=3.0.35-lab126
machine=armv7l
root_device=/dev/mmcblk0p1
root_fstype=ext3
root_mount_read_only=true
partitions_status=AVAILABLE
partition=mmcblk0,179,0,4096000
partition=mmcblk0p1,179,1,128000
mtd_status=NOT_EXPOSED
block_readonly=mmcblk0,0
R3877_19_READ_ONLY_STORAGE_COMPLETE
'''
class T(unittest.TestCase):
    def test_pass(self):
        x=analyze(GOOD);self.assertEqual(x['result'],'PASS_STORAGE_METADATA_ONLY')
        self.assertFalse(x['recovery_verified']);self.assertEqual(x['immutable_hold'],'NOT_BOOTABLE')
    def test_missing_sentinels(self):self.assertEqual(analyze(GOOD.replace('R3877_19_READ_ONLY_STORAGE_COMPLETE',''))['result'],'HOLD')
    def test_duplicate_sentinels(self):self.assertEqual(analyze(GOOD+GOOD)['result'],'HOLD')
    def test_wrong_kernel(self):self.assertEqual(analyze(GOOD.replace('3.0.35-lab126','6.1.0'))['result'],'HOLD')
    def test_missing_root(self):self.assertEqual(analyze(GOOD.replace('root_fstype=ext3',''))['result'],'HOLD')
    def test_missing_partitions(self):
        x=GOOD.replace('partition=mmcblk0,179,0,4096000','').replace('partition=mmcblk0p1,179,1,128000','')
        self.assertEqual(analyze(x)['result'],'HOLD')
    def test_duplicate_partition(self):
        x=GOOD.replace('mtd_status=NOT_EXPOSED','partition=mmcblk0p1,179,1,128000\nmtd_status=NOT_EXPOSED')
        self.assertEqual(analyze(x)['result'],'HOLD')
    def test_invalid_partition(self):self.assertEqual(analyze(GOOD.replace('mmcblk0p1,179,1,128000','bad;cmd,179,1,128000'))['result'],'HOLD')
    def test_mtd_parsing(self):
        x=GOOD.replace('mtd_status=NOT_EXPOSED','mtd_status=AVAILABLE\nmtd=mtd0,00010000,00002000')
        self.assertEqual(analyze(x)['inventory']['mtd'][0]['size_bytes'],65536)
    def test_readonly_property(self):self.assertFalse(analyze(GOOD)['inventory']['block_readonly'][0]['read_only'])
    def test_duplicate_key(self):self.assertEqual(analyze(GOOD.replace('machine=armv7l','machine=armv7l\nmachine=armv7l'))['result'],'HOLD')
    def test_header_forbidden_labels(self):self.assertNotIn('serial',str(analyze(GOOD)).lower())
if __name__=='__main__':unittest.main()
