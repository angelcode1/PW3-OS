"""Host-only synthetic R3877.73 fail-closed parser tests."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import pw3_r3877_73_analyze as m

GOOD = '''R3877_73_BEGIN
kernel=3.0.35-lab126
machine=armv7l
cmdline_console_count=1
cmdline_console_class=IMX_UART0_115200
active_console_imx0=1
active_console_imx1=0
active_console_other_count=1
sysfs_tty_ttymxc0_present=1
sysfs_tty_ttymxc1_present=0
boot_mmcblk0boot0_force_ro=1
boot_mmcblk0boot0_ro=1
boot_mmcblk0boot1_force_ro=1
boot_mmcblk0boot1_ro=1
R3877_73_END
'''

class Tests(unittest.TestCase):
    def test_01_success_is_hold(self):
        x = m.analyze(GOOD)
        self.assertEqual(x['result'], 'HOLD')
        self.assertEqual(x['immutable_hold'], 'NOT_BOOTABLE')
        self.assertTrue(x['review']['kernel_console_metadata_parsed'])

    def test_02_no_serial_access_claim(self):
        self.assertFalse(m.analyze(GOOD)['review']['physical_uart_connection_verified'])

    def test_03_missing_sentinels(self):
        self.assertNotIn('review', m.analyze(GOOD.replace('R3877_73_END', '')))

    def test_04_duplicate_sentinels(self):
        self.assertNotIn('review', m.analyze(GOOD + 'R3877_73_END\n'))

    def test_05_duplicate_key(self):
        self.assertNotIn('review', m.analyze(GOOD.replace('kernel=', 'kernel=3.0.35-lab126\nkernel=')))

    def test_06_private_field_refused(self):
        self.assertNotIn('review', m.analyze(GOOD.replace('machine=', 'serial=ABCDEF\nmachine=')))

    def test_07_other_kernel(self):
        self.assertNotIn('review', m.analyze(GOOD.replace('3.0.35-lab126', '4.0')))

    def test_08_bad_console(self):
        self.assertNotIn('review', m.analyze(GOOD.replace('IMX_UART0_115200', '/dev/ttyUSB0')))

    def test_09_multiple_console(self):
        s = GOOD.replace('cmdline_console_count=1', 'cmdline_console_count=2').replace('IMX_UART0_115200', 'MULTIPLE_REDACTED')
        self.assertEqual(m.analyze(s)['review']['cmdline_console_count'], '2')

    def test_10_multiple_console_wrong_class(self):
        self.assertNotIn('review', m.analyze(GOOD.replace('cmdline_console_count=1', 'cmdline_console_count=2')))

    def test_11_console_unavailable(self):
        s = GOOD.replace('cmdline_console_count=1', 'cmdline_console_count=UNAVAILABLE').replace('IMX_UART0_115200', 'UNAVAILABLE')
        self.assertIn('review', m.analyze(s))

    def test_12_ro_unavailable(self):
        self.assertIn('review', m.analyze(GOOD.replace('boot_mmcblk0boot0_ro=1', 'boot_mmcblk0boot0_ro=UNAVAILABLE')))

    def test_13_invalid_ro_flag(self):
        self.assertNotIn('review', m.analyze(GOOD.replace('boot_mmcblk0boot0_ro=1', 'boot_mmcblk0boot0_ro=2')))

    def test_14_tty_missing(self):
        self.assertIn('review', m.analyze(GOOD.replace('sysfs_tty_ttymxc0_present=1', 'sysfs_tty_ttymxc0_present=0')))

    def test_15_input_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'in.txt'
            p.write_text(GOOD)
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                self.assertEqual(m.main([str(p)]), 2)
            j = json.loads(buf.getvalue())
            self.assertIn('review', j)

    def test_16_no_input(self):
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            self.assertEqual(m.main([]), 2)
        self.assertEqual(json.loads(buf.getvalue())['result'], 'HOLD')

    def test_17_overlarge(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'in.txt'
            p.write_text('A' * 20000)
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                m.main([str(p)])
            self.assertNotIn('review', json.loads(buf.getvalue()))

    def test_18_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'in.txt'
            p.write_text(GOOD)
            link = Path(d) / 'link'
            link.symlink_to(p)
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                m.main([str(link)])
            self.assertNotIn('review', json.loads(buf.getvalue()))

    def test_19_no_private_marker(self):
        self.assertNotIn('serial=', json.dumps(m.analyze(GOOD)))

if __name__ == '__main__':
    unittest.main()
