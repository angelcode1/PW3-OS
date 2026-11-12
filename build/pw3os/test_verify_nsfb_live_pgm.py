"""Regression checks for real libnsfb RAM-canvas capture validator."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_nsfb_live_pgm import validate, HEADER, WIDTH, HEIGHT

class NSFBLiveCaptureTests(unittest.TestCase):
    def test_real_canvas_color_proof(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"capture.pgm"
            img=bytearray(b"\xff"*(WIDTH*HEIGHT))
            for y in range(75,225):
                for x in range(50,550):
                    img[y*WIDTH+x]=82
            for y in range(15,32):
                for x in range(40,480):
                    img[y*WIDTH+x]=0
            p.write_bytes(HEADER+img)
            validate(p)
            img[:]=b"\xff"*len(img)
            p.write_bytes(HEADER+img)
            with self.assertRaisesRegex(ValueError,"Missing actual browser"):
                validate(p)

    def test_reject_short_or_wrong_geometry(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"capture.pgm"
            p.write_bytes(HEADER+b"x")
            with self.assertRaises(ValueError): validate(p)
            p.write_bytes(b"P5\n320 480\n255\n"+b"\xff"*(WIDTH*HEIGHT))
            with self.assertRaises(ValueError): validate(p)

if __name__=="__main__":
    unittest.main()
