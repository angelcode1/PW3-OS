#!/usr/bin/env python3
"""Decode and compare untrusted-sized PNG screenshots with Python stdlib only.

Checks NetSurf changed an actual X11 pixel surface, not merely process liveness.
This cannot assert successful HTTPS or true Kindle rendering.
"""
import binascii
import pathlib
import struct
import sys
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def read_png(path):
    blob = pathlib.Path(path).read_bytes()
    if not blob.startswith(SIGNATURE):
        raise ValueError("not PNG")
    offset = 8
    chunks = []
    header = None
    while offset + 12 <= len(blob):
        size = struct.unpack_from(">I", blob, offset)[0]
        if size > 64 * 1024 * 1024 or offset + 12 + size > len(blob):
            raise ValueError("invalid PNG chunk size")
        kind = blob[offset + 4:offset + 8]
        data = blob[offset + 8:offset + 8 + size]
        crc = struct.unpack_from(">I", blob, offset + 8 + size)[0]
        if (binascii.crc32(kind + data) & 0xFFFFFFFF) != crc:
            raise ValueError("PNG CRC mismatch")
        offset += 12 + size
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", data)
        if kind == b"IDAT":
            chunks.append(data)
        if kind == b"IEND":
            break
    if header is None or not chunks:
        raise ValueError("PNG missing image or data")
    w, h, depth, color, comp, filt, interlace = header
    if not (100 <= w <= 2048 and 100 <= h <= 2048) or w * h > 2097152:
        raise ValueError("PNG dimensions outside bounded test")
    if depth != 8 or color not in (2, 6) or comp or filt or interlace:
        raise ValueError("Unsupported PNG pixel format (expect RGB/RGBA 8-bit)")
    channels = 3 if color == 2 else 4
    pitch = w * channels
    compressed = b"".join(chunks)
    inflated = zlib.decompressobj()
    expected = (pitch + 1) * h
    raw = inflated.decompress(compressed, expected + 1)
    raw += inflated.flush()
    if not inflated.eof or len(raw) != expected:
        raise ValueError("Truncated/oversized PNG data")
    decoded = bytearray(pitch * h)
    previous = bytearray(pitch)
    for row in range(h):
        off = row * (pitch + 1)
        method = raw[off]
        src = raw[off + 1:off + 1 + pitch]
        scan = bytearray(pitch)
        for i, v in enumerate(src):
            left = scan[i - channels] if i >= channels else 0
            up = previous[i]
            above_left = previous[i - channels] if i >= channels else 0
            if method == 0: predictor = 0
            elif method == 1: predictor = left
            elif method == 2: predictor = up
            elif method == 3: predictor = (left + up) // 2
            elif method == 4:
                p = left + up - above_left
                a, b, c = abs(p - left), abs(p - up), abs(p - above_left)
                predictor = left if a <= b and a <= c else up if b <= c else above_left
            else: raise ValueError("Unsupported PNG row filter")
            scan[i] = (v + predictor) & 255
        decoded[row * pitch:(row + 1) * pitch] = scan
        previous = scan
    return w, h, channels, decoded


def compare(baseline, rendered):
    aw, ah, ac, a = read_png(baseline)
    bw, bh, bc, b = read_png(rendered)
    if (aw, ah) != (bw, bh):
        raise ValueError("Screenshot canvas dimensions changed")
    changed = 0
    bright = 0
    dark = 0
    proof_magenta = 0
    for i in range(aw * ah):
        ar, ag, ab = a[i * ac:i * ac + 3]
        br, bg, bb = b[i * bc:i * bc + 3]
        if max(abs(br - ar), abs(bg - ag), abs(bb - ab)) >= 30:
            changed += 1
        if min(br, bg, bb) >= 220:
            bright += 1
        if max(br, bg, bb) <= 50:
            dark += 1
        # The local fixture contains a large #cc2a77 CSS panel. This proves
        # page content and stylesheet rendering, not just an SDL window.
        if br >= 145 and 20 <= bg <= 105 and 80 <= bb <= 185:
            proof_magenta += 1
    # A cursor flash can only change dozens of pixels; reject false pass.
    if changed < 15000 or bright < 10000 or dark < 1000 or proof_magenta < 2000:
        raise ValueError(
            f"Insufficient browser page pixels: changed={changed}, "
            f"bright={bright}, dark={dark}, proof_magenta={proof_magenta}")
    print(f"CODEX_BROWSER_VISUAL_PIXEL_PASS {aw}x{ah} "
          f"changed={changed} bright={bright} dark={dark} "
          f"proof_magenta={proof_magenta}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: verify_browser_capture.py baseline.png rendered.png")
    try:
        compare(sys.argv[1], sys.argv[2])
    except (ValueError, OSError, zlib.error) as error:
        raise SystemExit("CODEX_BROWSER_VISUAL_PIXEL_FAIL: " + str(error))
