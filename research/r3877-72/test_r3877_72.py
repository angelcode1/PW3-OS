"""Synthetic, offline regressions for PW3 R3877.72."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zlib

import pw3_r3877_72_boot_chain_preflight as m


def make_uboot():
    return (b'U-Boot 2009.08-lab126\0'
            b'bootcmd=bootm 0x41000\0'
            b'bootcmd_diags=bootm 0xE41000\0'
            b'baudrate=115200\0'
            b'bootdelay=1\0bootdelay=0\0')


def make_kernel(f, offset, data=b'A'*512):
    h = bytearray(64)
    struct.pack_into('>7I4B32s', h, 0, 0x27051956, 0, 0, len(data),
                     0x80008000, 0x80008000, zlib.crc32(data),
                     5, 2, 2, 0, b'Linux-3.0.35-lab126')
    struct.pack_into('>I', h, 4, zlib.crc32(h))
    f.seek(offset)
    f.write(h)
    f.write(data)


class Tests(unittest.TestCase):
    def test_01_expected_commands(self):
        b = make_uboot()
        r = m.markers(b)
        self.assertEqual(r['serial_baudrate_marker'], 115200)
        self.assertEqual(r['bootdelay_values_observed'], [0, 1])
        self.assertFalse(r['embedded_strings_are_live_environment_proof'])

    def test_02_missing_diags(self):
        with self.assertRaises(m.Hold):
            m.markers(make_uboot().replace(b'bootcmd_diags=', b'diags_command='))

    def test_03_bad_baudrate(self):
        with self.assertRaises(m.Hold):
            m.markers(make_uboot().replace(b'baudrate=115200', b'baudrate=9600'))

    def test_04_no_boot_delay(self):
        with self.assertRaises(m.Hold):
            m.markers(make_uboot().replace(b'bootdelay=', b'someother='))

    def test_05_kernel_good(self):
        f = io.BytesIO(bytearray(0x41000+1024))
        make_kernel(f, 0x41000)
        self.assertTrue(m.kernel_header(f, 0x41000)['payload_crc_verified'])

    def test_06_corrupt_payload(self):
        f = io.BytesIO(bytearray(0x41000+1024))
        make_kernel(f, 0x41000)
        f.seek(0x41000+64)
        f.write(b'Z')
        with self.assertRaises(m.Hold):
            m.kernel_header(f, 0x41000)

    def test_07_corrupt_header(self):
        f = io.BytesIO(bytearray(0x41000+1024))
        make_kernel(f, 0x41000)
        f.seek(0x41000+8)
        f.write(b'Q')
        with self.assertRaises(m.Hold):
            m.kernel_header(f, 0x41000)

    def test_08_missing_optin_never_reads(self):
        with patch.object(m, 'inspect', side_effect=AssertionError('no scan')):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main(['--image-dir', '/tmp']), 2)
        report = json.loads(out.getvalue())
        self.assertEqual(report['hold_category'], 'EXPLICIT_OFFLINE_IMAGE_OPT_IN_REQUIRED')

    def test_09_all_good_still_hold(self):
        with patch.object(m, 'inspect', return_value={'status': 'OFFLINE_ONLY'}):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main(['--image-dir', '/tmp',
                    '--acknowledge-readonly-offline-boot-chain']), 2)
        report = json.loads(out.getvalue())
        self.assertEqual(report['result'], 'HOLD')
        self.assertEqual(report['immutable_hold'], 'NOT_BOOTABLE')
        self.assertFalse(report['recovery_verified'])

    def test_10_symlink_image_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'other').write_bytes(b'123')
            (root / 'mmcblk0boot0.img').symlink_to('other')
            with self.assertRaises(m.Hold):
                m.open_fixed(root, 'mmcblk0boot0.img', m.SIZE_BOOT0)

    def test_11_missing_image_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(OSError):
                m.open_fixed(tmp, 'mmcblk0boot0.img', m.SIZE_BOOT0)

    def test_12_no_raw_environment_output(self):
        r = m.markers(make_uboot())
        self.assertNotIn('bootcmd=', json.dumps(r))
        self.assertNotIn('ssid', json.dumps(r))

if __name__ == '__main__':
    unittest.main()
