"""Synthetic, host-only regressions for R3877.71."""
import io
import json
import struct
import unittest
import zlib
from unittest.mock import patch
from contextlib import redirect_stdout

import pw3_r3877_71_offline_verify as m

class Tests(unittest.TestCase):
    def test_geometry(self):
        b = bytearray(512)
        b[510:512] = b'\x55\xaa'
        for i, (typ, boot, start, length) in enumerate(m.GEOMETRY):
            off = 446 + i * 16
            b[off] = 0x80 if boot else 0
            b[off+4] = typ
            struct.pack_into('<II', b, off+8, start, length)
        self.assertEqual(m.mbr_entries(bytes(b)), list(m.GEOMETRY))

    def test_geometry_wrong(self):
        with self.assertRaises(m.Hold):
            m.mbr_entries(bytes(512))

    def test_wrong_partition(self):
        b = bytearray(512)
        b[510:512] = b'\x55\xaa'
        with self.assertRaises(m.Hold):
            m.mbr_entries(bytes(b))

    def test_uimage_good(self):
        payload = b'abc123' * 10
        h = bytearray(64)
        struct.pack_into('>7I4B32s', h, 0, 0x27051956, 0, 0, len(payload),
                         0x80008000, 0x80008000, zlib.crc32(payload), 5, 2, 2, 0,
                         b'Linux-3.0.35-lab126')
        struct.pack_into('>I', h, 4, zlib.crc32(h))
        with patch.object(m, 'read_at', return_value=bytes(h)), \
             patch.object(m, 'crc_file_range', return_value=zlib.crc32(payload)):
            self.assertTrue(m.uimage(None, 0x41000)['payload_crc_valid'])

    def test_uimage_corrupt_header(self):
        with patch.object(m, 'read_at', return_value=bytes(64)):
            with self.assertRaises(m.Hold):
                m.uimage(None, 0x41000)

    def test_uimage_corrupt_payload(self):
        payload = b'A' * 10
        h = bytearray(64)
        struct.pack_into('>7I4B32s', h, 0, 0x27051956, 0, 0, len(payload),
                         0x80008000, 0x80008000, 100, 5, 2, 2, 0,
                         b'Linux-3.0.35-lab126')
        struct.pack_into('>I', h, 4, zlib.crc32(h))
        with patch.object(m, 'read_at', return_value=bytes(h)), \
             patch.object(m, 'crc_file_range', return_value=101):
            with self.assertRaises(m.Hold):
                m.uimage(None, 0x41000)

    def test_ext3_journal(self):
        with patch.object(m, 'read_at', side_effect=[b'\x53\xef', struct.pack('<I', 4)]):
            self.assertTrue(m.ext3_magic(None))

    def test_ext3_without_journal(self):
        with patch.object(m, 'read_at', side_effect=[b'\x53\xef', struct.pack('<I', 0)]):
            with self.assertRaises(m.Hold):
                m.ext3_magic(None)

    def test_no_opt_in(self):
        with patch.object(m, 'inspect', side_effect=AssertionError('must not read')):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main(['--image-dir', '/tmp']), 2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],
                         'EXPLICIT_OFFLINE_IMAGE_ACCESS_REQUIRED')

    def test_success_still_holds(self):
        with patch.object(m, 'inspect', return_value={'image_count': 5}):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main(['--image-dir', '/tmp',
                    '--acknowledge-readonly-offline-images']), 2)
        j = json.loads(out.getvalue())
        self.assertEqual(j['result'], 'HOLD')
        self.assertEqual(j['immutable_hold'], 'NOT_BOOTABLE')
        self.assertNotIn('sha256', out.getvalue())

if __name__ == '__main__':
    unittest.main()
