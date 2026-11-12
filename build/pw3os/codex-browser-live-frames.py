#!/usr/bin/env python3
"""Bounded, pure-software NetSurf BMP -> PW3 PGM bridge.

Only reads the atomic SDL BMP written by the existing verified capture
interposer and atomically publishes a portrait P5 grayscale frame. The
independent C presenter owns the only /dev/fb0 access and restores it.
No URLs, evdev, SDL injection, display ioctls, or persistent files here.
"""
import argparse
import hashlib
import os
from pathlib import Path
import signal
import time

from verify_direct_sdl import read_bmp, PW3_W, PW3_H, PGM_HEADER

BMP = Path("/run/codex-browser/codex-live-sdl.bmp")
PGM = Path("/run/codex-browser/codex-browser-live-stream.pgm")
stop = False


def stop_now(_sig, _frame):
    global stop
    stop = True


def convert_frame(source: Path) -> bytes:
    b, offset, w, h, ch, stride, bottom_up = read_bmp(source)
    # This exact live trial is deliberately pinned to the validated NetSurf
    # dummy SDL size. Any surprise surface ABI change fails closed.
    if (w, h) != (600, 800):
        raise ValueError("Not the validated 600x800 NetSurf SDL surface")
    if PW3_W * h <= PW3_H * w:
        dw, dh = PW3_W, max(1, h * PW3_W // w)
    else:
        dh, dw = PW3_H, max(1, w * PW3_H // h)
    left, top = (PW3_W - dw) // 2, (PW3_H - dh) // 2
    out = bytearray(b"\xff" * (PW3_W * PW3_H))
    for y in range(dh):
        sy = y * h // dh
        base = offset + (h - 1 - sy if bottom_up else sy) * stride
        dest = (y + top) * PW3_W + left
        for x in range(dw):
            sx = x * w // dw
            i = base + sx * ch
            blue, green, red = b[i], b[i+1], b[i+2]
            out[dest + x] = (2126 * red + 7152 * green + 722 * blue + 5000) // 10000
    return PGM_HEADER + out


def follow(seconds: int = 33):
    if (os.environ.get("CODEX_BROWSER_LIVE_TRIAL") != "EXPLICIT" or
            str(BMP.parent) != "/run/codex-browser"):
        raise ValueError("Codex live conversion requires explicit gate")
    PGM.parent.mkdir(parents=True, exist_ok=True)
    # Reject stale captures from a previous trial.
    PGM.unlink(missing_ok=True)
    previous = None
    previous_digest = None
    count = 0
    deadline = time.monotonic() + seconds
    last_publish = -1000.0
    while not stop and time.monotonic() < deadline:
        try:
            st = BMP.stat()
            sig = (st.st_dev, st.st_ino, st.st_mtime_ns, st.st_size)
            if sig != previous and time.monotonic() - last_publish >= 1.9:
                previous = sig
                frame = convert_frame(BMP)
                digest = hashlib.blake2s(frame).digest()
                if digest != previous_digest:
                    tmp = PGM.parent / ".codex-browser-stream.pgm.tmp"
                    with tmp.open("wb") as f:
                        f.write(frame)
                    os.replace(tmp, PGM)
                    previous_digest = digest
                    last_publish = time.monotonic()
                    count += 1
                    print(f"CODEX_BROWSER_LIVE_PGM_PUBLISHED frame={count}", flush=True)
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as err:
            # Incomplete/unexpected image should not crash the other process.
            # Keep previous valid frame; never publish malformed data.
            print(f"CODEX_BROWSER_LIVE_FRAME_REJECTED {err}", flush=True)
        time.sleep(.18)
    print(f"CODEX_BROWSER_LIVE_CONVERTER_END frames={count}", flush=True)
    return 0 if count else 4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--follow-seconds", type=int)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        # One exact copy of verified 600x800 BMP frame should yield an
        # intact 1072x1448 PGM, with immutable header and letterboxing.
        if not BMP.is_file():
            print("CODEX_BROWSER_LIVE_SELFTEST_SKIPPED_NO_BMP")
            return 0
        frame = convert_frame(BMP)
        assert frame.startswith(PGM_HEADER)
        assert len(frame) == len(PGM_HEADER) + PW3_W * PW3_H
        print("CODEX_BROWSER_LIVE_SOFTWARE_SELFTEST_PASS")
        return 0
    if args.follow_seconds != 33:
        parser.error("only the bounded 33-second attended follow is allowed")
    if os.environ.get("CODEX_BROWSER_LIVE_TRIAL") != "EXPLICIT":
        parser.error("explicit browser trial environment gate required")
    signal.signal(signal.SIGINT, stop_now)
    signal.signal(signal.SIGTERM, stop_now)
    signal.signal(signal.SIGHUP, stop_now)
    return follow(args.follow_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
