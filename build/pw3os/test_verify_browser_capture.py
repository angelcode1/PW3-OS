"""Host-only tests of PNG screenshots captured by NetSurf visual CI."""
import binascii
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_browser_capture import read_png, compare


def png(width, height, white_rectangle=False, proof=True):
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            if white_rectangle and proof and x < width - 20 and 20 <= y < 60:
                row.extend((204, 42, 119))
            else:
                white = white_rectangle and x < width - 20
                row.extend((255, 255, 255) if white else (0, 0, 0))
        rows.append(b"\x00" + bytes(row))
    def chunk(tag, data):
        crc = binascii.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)
    hdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", hdr)
            + chunk(b"IDAT", zlib.compress(b"".join(rows)))
            + chunk(b"IEND", b""))


class TestBrowserCapture(unittest.TestCase):
    def test_nonblank_capture_and_reject_missing_render(self):
        with tempfile.TemporaryDirectory() as td:
            baseline = Path(td) / "baseline.png"
            rendered = Path(td) / "rendered.png"
            baseline.write_bytes(png(200, 200))
            rendered.write_bytes(png(200, 200, True))
            self.assertEqual(read_png(rendered)[:2], (200, 200))
            compare(baseline, rendered)
            with self.assertRaises(ValueError):
                compare(baseline, baseline)
            # A visible blank browser window must not pass without CSS proof.
            rendered.write_bytes(png(200, 200, True, proof=False))
            with self.assertRaises(ValueError):
                compare(baseline, rendered)

    def test_corrupt_png_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.png"
            image = bytearray(png(200, 200, True))
            image[-7] ^= 0x40
            path.write_bytes(image)
            with self.assertRaises(ValueError):
                read_png(path)
            path.write_bytes(b"not a PNG")
            with self.assertRaises(ValueError):
                read_png(path)


if __name__ == "__main__":
    unittest.main()
