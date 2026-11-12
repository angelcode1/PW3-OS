"""Host proof: live PGM conversion must match PW3 framebuffer geometry."""
import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location("codex_live_frames",
    HERE/"codex-browser-live-frames.py")
live=importlib.util.module_from_spec(spec)
spec.loader.exec_module(live)


class LiveFramesTests(unittest.TestCase):
    def test_real_sdl_frame_conversion(self):
        w,h=600,800
        row=bytes((0x77,0x2a,0xcc))*w  # BGR = CSS proof colour
        pixels=row*h
        header=bytearray(54)
        header[0:2]=b"BM"
        struct.pack_into("<I",header,2,len(header)+len(pixels))
        struct.pack_into("<I",header,10,54)
        struct.pack_into("<I",header,14,40)
        struct.pack_into("<ii",header,18,w,h)
        struct.pack_into("<HH",header,26,1,24)
        struct.pack_into("<I",header,34,len(pixels))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"frame.bmp"
            p.write_bytes(header+pixels)
            converted=live.convert_frame(p)
            self.assertTrue(converted.startswith(live.PGM_HEADER))
            self.assertEqual(len(converted),len(live.PGM_HEADER)+1072*1448)
            buffer=converted[len(live.PGM_HEADER):]
            self.assertEqual(buffer[0],255)
            self.assertEqual(buffer[9*1072],int((2126*0xcc+7152*0x2a+722*0x77+5000)//10000))
            self.assertEqual(buffer[(1448-1)*1072],255)
            bad=bytearray(header+pixels)
            struct.pack_into("<i",bad,18,601)
            p.write_bytes(bad)
            with self.assertRaises(ValueError):
                live.convert_frame(p)

    def test_hardware_trial_is_never_unattended(self):
        src=(HERE/"codex-browser-live-trial.sh").read_text()
        for required in (
            "CODEX_BROWSER_LIVE_TRIAL=EXPLICIT",
            "[ -t 0 ]",
            "--follow-seconds 33",
            "--follow-pgm",
            "CODEX_SDL_INPUT_ENABLE=PW3_ATTENDED",
            'kill -CONT "$home_pid"',
            'kill -TERM "$home_pid"',
            'trap cleanup EXIT',
            '"file://$HTML"',
        ):
            self.assertIn(required,src)
        self.assertNotIn("https://",src)


if __name__=="__main__":
    unittest.main()
