"""Tests for actual NetSurf SDL framebuffer BMP validation and PW3 conversion."""
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_direct_sdl import read_bmp,validate_and_convert,PGM_HEADER,PW3_W,PW3_H

def bmp(w=300,h=200,bpp=24,proof=True):
    ch=bpp//8
    rowlen=(w*ch+3)&~3
    scan=[]
    for y in reversed(range(h)):
        pixels=bytearray()
        for x in range(w):
            if y<70 and x<150 and proof:
                rgb=(204,42,119)
            elif y<70 and x>=150:
                rgb=(0,0,0)
            else:
                rgb=(255,255,255)
            pixels.extend((rgb[2],rgb[1],rgb[0]))
            if ch==4: pixels.append(0)
        pixels.extend(bytes(rowlen-len(pixels)))
        scan.append(bytes(pixels))
    bitmap=b"".join(scan)
    offset=54
    total=offset+len(bitmap)
    file_header=b"BM"+struct.pack("<IHHI",total,0,0,offset)
    dib=struct.pack("<IiiHHIIiiII",40,w,h,1,bpp,0,len(bitmap),0,0,0,0)
    return file_header+dib+bitmap

class DirectSDLTests(unittest.TestCase):
    def test_24_and_32_bit_direct_surface_conversion(self):
        with tempfile.TemporaryDirectory() as d:
            src,dst=Path(d)/"s.bmp",Path(d)/"pw3.pgm"
            for bits in (24,32):
                src.write_bytes(bmp(bpp=bits))
                self.assertEqual(read_bmp(src)[2:4],(300,200))
                gray=validate_and_convert(src,dst)
                self.assertEqual(dst.read_bytes()[:len(PGM_HEADER)],PGM_HEADER)
                self.assertEqual(len(gray),PW3_W*PW3_H)
                self.assertEqual(gray[0],255)
                self.assertEqual(gray[-1],255)
                self.assertTrue(any(v<30 for v in gray))
                self.assertTrue(any(70<=v<=95 for v in gray))

    def test_reject_blank_page_and_corrupt_bmp(self):
        with tempfile.TemporaryDirectory() as d:
            src,dst=Path(d)/"s.bmp",Path(d)/"pw3.pgm"
            src.write_bytes(bmp(proof=False))
            with self.assertRaisesRegex(ValueError,"CSS proof"):
                validate_and_convert(src,dst)
            src.write_bytes(b"not BMP")
            with self.assertRaises(ValueError):
                read_bmp(src)
            damaged=bytearray(bmp())
            struct.pack_into("<I",damaged,2,123)
            src.write_bytes(damaged)
            with self.assertRaises(ValueError):
                read_bmp(src)

if __name__=="__main__":
    unittest.main()
