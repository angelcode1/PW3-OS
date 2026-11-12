#!/usr/bin/env python3
"""Check that the actual libnsfb RAM framebuffer contains browser CSS pixels.

This is distinct from the previous Xvfb SDL screenshot, and cannot be
satisfied by process liveness or a blank NetSurf window. No hardware access.
"""
from pathlib import Path
import sys

HEADER=b"P5\n600 800\n255\n"
WIDTH,HEIGHT=600,800

def validate(path):
    data=Path(path).read_bytes()
    if len(data) != len(HEADER)+WIDTH*HEIGHT or not data.startswith(HEADER):
        raise ValueError("Invalid live NSFB P5 size, geometry, or header")
    gray=memoryview(data)[len(HEADER):]
    black=sum(1 for g in gray if g<=45)
    white=sum(1 for g in gray if g>=220)
    # #cc2a77 has weighted luma about 82. May vary one or two units with
    # NetSurf's pixel packing and font anti-aliasing; require broad region.
    magenta=sum(1 for g in gray if 70<=g<=95)
    if black<1000 or white<10000 or magenta<5000:
        raise ValueError(f"Missing actual browser HTML/CSS proof: "
                         f"black={black} white={white} magenta={magenta}")
    print(f"CODEX_NSFB_LIVE_PIXEL_PASS 600x800 "
          f"black={black} white={white} css_luma={magenta}")

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: verify_nsfb_live_pgm.py /reports/codex-live-nsfb.pgm")
    try:
        validate(sys.argv[1])
    except (ValueError,OSError) as e:
        raise SystemExit("CODEX_NSFB_LIVE_PIXEL_FAIL: "+str(e))
