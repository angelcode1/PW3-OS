#!/usr/bin/env python3
"""Optional Bluetooth-only audio playback for the PW3 Bible reader.

Requires BlueZ hci, connected PulseAudio-compatible BlueZ sink, mpv, Python 3.
URLs are supplied by the owner in audio-links.tsv. Never discovers, guesses,
scrapes or downloads protected recordings. No non-Bluetooth output fallback.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import stat
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
MANIFEST = BASE / "audio-links.tsv"
EDITION = {"kjv", "csb", "breathe"}
BLUEZ_SINK = re.compile(r"^bluez_output\.[A-Za-z0-9_.-]+$")


def runtime_dir():
    path = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / ("pw3-bible-audio-" + str(os.getuid()))
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    st = path.lstat()
    if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.getuid() or (st.st_mode & 0o077):
        raise RuntimeError("unsafe audio runtime directory")
    return path


def sink():
    """Select a connected BlueZ audio sink, never the host's default speaker."""
    try:
        if not any(name.startswith("hci") for name in os.listdir("/sys/class/bluetooth")):
            return None
        check = subprocess.run(["pactl", "list", "short", "sinks"],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, timeout=3, check=False)
        if check.returncode:
            return None
        for line in check.stdout.splitlines():
            columns = line.split()
            if len(columns) > 1 and BLUEZ_SINK.fullmatch(columns[1]):
                return columns[1]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def ready():
    return sink() is not None and shutil.which("mpv") is not None


def approved_media(value):
    # Disallow mpv special protocols and shell/playlist substitutions.
    if value.startswith(("https://", "http://")):
        return len(value) <= 4096 and not any(c.isspace() or ord(c) < 32 for c in value)
    if value.startswith("./audio/") and ".." not in Path(value).parts:
        resolved = (BASE / value).resolve()
        directory = (BASE / "audio").resolve()
        try:
            resolved.relative_to(directory)
        except ValueError:
            return False
        return resolved.is_file()
    return False


def find_audio(edition, book, chapter):
    if edition not in EDITION or not 1 <= book <= 73 or not 1 <= chapter <= 150:
        return None
    if edition == "breathe" and book < 47:
        return None
    if not MANIFEST.is_file():
        return None
    with MANIFEST.open(encoding="utf-8") as src:
        for line in src:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            cols = line.rstrip("\n\r").split("\t")
            if len(cols) == 4 and cols[:3] == [edition, str(book), str(chapter)]:
                return cols[3] if approved_media(cols[3]) else None
    return None


def state_path(root):
    return root / "state.json"


def load_state(root):
    try:
        return json.loads(state_path(root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def active(state, root):
    """Require our IPC path in the PID's command line before signalling it."""
    pid = state.get("pid")
    if not isinstance(pid, int) or pid <= 1:
        return False
    try:
        if str(root / "mpv.sock").encode() not in Path(f"/proc/{pid}/cmdline").read_bytes():
            return False
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def ipc(root, command):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            sock.connect(str(root / "mpv.sock"))
            sock.sendall(json.dumps({"command": command}).encode() + b"\n")
            data = bytearray()
            for _ in range(8):
                chunk = sock.recv(2048)
                if not chunk:
                    break
                data.extend(chunk)
                for line in data.split(b"\n"):
                    compact = line.replace(b" ", b"")
                    if b'"error":"success"' in compact:
                        return True
                    if b'"error":' in compact:
                        return False
            return False
    except OSError:
        return False


def stop(root, state):
    if active(state, root):
        ipc(root, ["quit"])
        if active(state, root):
            try:
                os.kill(state["pid"], signal.SIGTERM)
            except OSError:
                pass
    state_path(root).unlink(missing_ok=True)
    (root / "mpv.sock").unlink(missing_ok=True)


def start(root, state, edition, book, chapter):
    output = sink()
    if not output or not shutil.which("mpv"):
        print("Bluetooth audio output unavailable", file=sys.stderr)
        return 1
    media = find_audio(edition, book, chapter)
    if not media:
        print("No authorised playable source configured for this chapter", file=sys.stderr)
        return 2
    stop(root, state)
    cmd = ["mpv", "--no-config", "--no-video", "--no-terminal",
           "--audio-device=pulse/" + output, "--audio-fallback-to-null=no",
           "--input-ipc-server=" + str(root / "mpv.sock"), "--", media]
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            start_new_session=True, cwd=BASE)
    state_path(root).write_text(json.dumps({"pid": proc.pid, "edition": edition,
                                           "book": book, "chapter": chapter,
                                           "paused": False}), encoding="utf-8")
    for _ in range(12):
        if proc.poll() is not None:
            stop(root, load_state(root))
            return 3
        if (root / "mpv.sock").exists():
            return 0
        time.sleep(0.1)
    stop(root, load_state(root))
    return 3


def command(args):
    if args.action == "ready":
        return 0 if ready() else 1
    root = runtime_dir()
    with (root / "lock").open("a+") as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        state = load_state(root)
        if args.action == "stop":
            stop(root, state)
            return 0
        if args.action == "status":
            if not ready() or not active(state, root):
                return 1
            print("paused" if state.get("paused") else "playing")
            return 0
        if args.action == "play":
            return start(root, state, args.edition, args.book, args.chapter)
        if args.action in ("pause", "resume"):
            if not active(state, root) or not ready():
                return 1
            paused = args.action == "pause"
            if not ipc(root, ["set_property", "pause", paused]):
                return 1
            state["paused"] = paused
            state_path(root).write_text(json.dumps(state), encoding="utf-8")
            return 0
    return 2


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("ready", "play", "pause", "resume", "stop", "status"))
    p.add_argument("edition", nargs="?", choices=sorted(EDITION))
    p.add_argument("book", nargs="?", type=int)
    p.add_argument("chapter", nargs="?", type=int)
    args = p.parse_args()
    if args.action == "play" and (args.edition is None or args.book is None or args.chapter is None):
        p.error("play requires edition, book, chapter")
    try:
        return command(args)
    except (OSError, RuntimeError, ValueError) as e:
        print("Audio unavailable:", type(e).__name__, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
