#!/usr/bin/env python3
"""Turn validated NetSurf Xvfb screenshot into a PW3 8bpp P5 image.

Pure CPU conversion, no Kindle framebuffer access. Keeps aspect ratio and
letterboxes, with fixed output 1072x1448. Nearest-neighbour retains readable
high-contrast text. No Pillow/host system dependencies.
"""
from pathlib import Path
import sys
from verify_browser_capture import read_png

PW3_W, PW3_H = 1072, 1448
PGM_HEADER = b"P5\n1072 1448\n255\n"


def convert_rgb_png(input_file, output_file):
    w, h, channels, pixels = read_png(input_file)
    if not (100 <= w <= 2048 and 100 <= h <= 2048):
        raise ValueError("Invalid browser screenshot dimensions")
    # Integer-rational fit, without increasing either axis beyond panel.
    if PW3_W * h <= PW3_H * w:
        dst_w, dst_h = PW3_W, max(1, h * PW3_W // w)
    else:
        dst_h, dst_w = PW3_H, max(1, w * PW3_H // h)
    left = (PW3_W - dst_w) // 2
    top = (PW3_H - dst_h) // 2
    gray = bytearray(b"\xff" * (PW3_W * PW3_H))
    for y in range(dst_h):
        sy = y * h // dst_h
        dst = (y + top) * PW3_W + left
        for x in range(dst_w):
            sx = x * w // dst_w
            i = (sy * w + sx) * channels
            red, green, blue = pixels[i], pixels[i + 1], pixels[i + 2]
            gray[dst + x] = (2126 * red + 7152 * green + 722 * blue + 5000) // 10000
    out = Path(output_file)
    out.write_bytes(PGM_HEADER + gray)
    print(f"CODEX_PW3_BROWSER_PREVIEW_PGM_PASS "
          f"{w}x{h} -> {PW3_W}x{PW3_H} ({dst_w}x{dst_h} letterboxed)")
    return bytes(gray)


def main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: browser_capture_to_pw3.py input.png output.pgm")
    try:
        convert_rgb_png(argv[1], argv[2])
    except (OSError, ValueError) as e:
        raise SystemExit(f"CODEX_PW3_PGM_FAIL: {e}")


if __name__ == "__main__":
    main(sys.argv)
