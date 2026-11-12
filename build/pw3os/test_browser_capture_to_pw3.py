"""Browser screenshot -> PW3 PGM conversion regression. No hardware access."""
import binascii
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_capture_to_pw3 import convert_rgb_png, PGM_HEADER, PW3_H, PW3_W


def make_png(w, h):
    # Four quadrants: black, white, green, magenta. Test channels/luma.
    rows = []
    for y in range(h):
        row = bytearray(b"\x00")
        for x in range(w):
            value = ((0, 0, 0) if x < w // 2 and y < h // 2 else
                     (255, 255, 255) if x >= w // 2 and y < h // 2 else
                     (0, 255, 0) if x < w // 2 else (204, 42, 119))
            row.extend(value)
        rows.append(bytes(row))
    def chunk(name, data):
        return (struct.pack(">I", len(data)) + name + data +
                struct.pack(">I", binascii.crc32(name + data) & 0xffffffff))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(b"".join(rows))) +
            chunk(b"IEND", b""))


class BrowserPW3Conversion(unittest.TestCase):
    def test_aspect_and_color_conversion(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / "s.png", Path(d) / "out.pgm"
            src.write_bytes(make_png(200, 100))
            gray = convert_rgb_png(src, dst)
            self.assertEqual(len(gray), PW3_W * PW3_H)
            self.assertEqual(dst.read_bytes()[:len(PGM_HEADER)], PGM_HEADER)
            self.assertEqual(dst.stat().st_size, PW3_W * PW3_H + len(PGM_HEADER))
            # Panel letterbox regions remain white.
            self.assertEqual(gray[0], 255)
            self.assertEqual(gray[-1], 255)
            top = (PW3_H - (100 * PW3_W // 200)) // 2
            self.assertEqual(gray[(top + 30) * PW3_W + 100], 0)
            self.assertEqual(gray[(top + 30) * PW3_W + 900], 255)
            self.assertGreater(gray[(top + 350) * PW3_W + 100], 150)
            magenta = gray[(top + 350) * PW3_W + 900]
            self.assertTrue(60 < magenta < 170, magenta)

    def test_reject_bad_file(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / "s.png", Path(d) / "out.pgm"
            src.write_bytes(b"bad")
            with self.assertRaises(ValueError):
                convert_rgb_png(src, dst)


if __name__ == "__main__":
    unittest.main()
