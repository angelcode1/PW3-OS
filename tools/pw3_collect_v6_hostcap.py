#!/usr/bin/env python3
"""PW3 fixed-allowlist read-only SSH collection; bounds stdout on the Mac.

No Kindle writes, temp files, hardware IOCTLs, boot actions, or uploads.
Dry-run is default. Works without remote head, grep, dd, sed or awk.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import sys
import time
import zipfile
from dataclasses import dataclass

COLLECTOR_REV = "PW3-V6-HOSTCAP-20261101"
MAX_BYTES = 32768
MAX_STDERR = 1024
TIMEOUT = 25

PROBES = {
    "kernel_version.txt": "uname -a",
    "kernel_release.txt": "uname -r",
    "system_mounts.txt": "cat /proc/mounts",
    "filesystem_types.txt": "cat /proc/filesystems",
    "modules.txt": "cat /proc/modules",
    "mtd_table.txt": "cat /proc/mtd 2>/dev/null || true",
    "input_devices.txt": "cat /proc/bus/input/devices 2>/dev/null || true",
    "framebuffer_list.txt": "cat /proc/fb 2>/dev/null || true",
    "input_nodes.txt": "ls -ld /dev/input /dev/input/event* 2>/dev/null || true",
    "framebuffer_nodes.txt": "ls -ld /dev/fb* 2>/dev/null || true",
    "sysfs_framebuffer.txt": "ls -l /sys/class/graphics/ 2>/dev/null || true",
    "sysfs_backlight.txt": "ls -l /sys/class/backlight/ 2>/dev/null || true",
    "sysfs_power_supply.txt": "ls -l /sys/class/power_supply/ 2>/dev/null || true",
    "init_locations.txt": "ls -ld /etc/upstart /etc/init /etc/init.d /sbin/init /etc/inittab 2>/dev/null || true",
    "upstart_names.txt": "ls -1 /etc/upstart/ 2>/dev/null || true",
    "init_names.txt": "ls -1 /etc/init.d/ 2>/dev/null || true",
    "library_names.txt": "ls -1 /lib/ /usr/lib/ 2>/dev/null || true",
}
OPTIONAL_FILES = (
    "/etc/fstab", "/etc/inittab", "/etc/os-release",
    "/etc/upstart/boot.conf", "/etc/upstart/dbus.conf",
    "/etc/upstart/framework.conf", "/etc/init.d/rcS",
)

@dataclass
class Result:
    returncode: int
    stdout: bytes
    stderr: bytes
    over_limit: bool = False


def run_bounded(argv, script, timeout=TIMEOUT, max_bytes=MAX_BYTES):
    """Read SSH output incrementally and kill connection if stdout exceeds limit.

    Remote command receives only its fixed script over stdin, and never creates
    files on Kindle.  No unbounded subprocess.run(capture_output=True) buffer.
    """
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    chunks = bytearray()
    errors = bytearray()
    too_big = False
    deadline = time.monotonic() + timeout
    try:
        proc.stdin.write(script.encode("utf-8"))
        proc.stdin.close()
        for name, stream in (("out", proc.stdout), ("err", proc.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("SSH command exceeded timeout")
            for key, _ in selector.select(min(remaining, 0.5)):
                try:
                    data = os.read(key.fileobj.fileno(), 4096)
                except BlockingIOError:
                    continue
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                if key.data == "out":
                    new_bytes = min(len(data), max(0, max_bytes - len(chunks)))
                    chunks.extend(data[:new_bytes])
                    if new_bytes < len(data):
                        too_big = True
                        proc.kill()
                        break
                else:
                    errors.extend(data[:max(0, MAX_STDERR-len(errors))])
            if too_big:
                break
        remaining = max(0, deadline - time.monotonic())
        try:
            status = proc.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            raise TimeoutError("SSH command exceeded timeout")
        return Result(status, bytes(chunks), bytes(errors), too_big)
    finally:
        selector.close()
        if proc.poll() is None:
            proc.kill()
            proc.wait()
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            if stream and not stream.closed:
                stream.close()


def remote_ssh(host, port, script):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.:-]{0,252}", host) or host.startswith("-"):
        raise ValueError("invalid host")
    if not 1 <= port <= 65535:
        raise ValueError("invalid port")
    argv = ["ssh", "-T", "-o", "ConnectTimeout=8", "-o", "BatchMode=no",
            "-o", "StrictHostKeyChecking=ask", "-p", str(port),
            "root@" + host, "sh", "-s"]
    return run_bounded(argv, script)


def probe_script(name):
    # Constant, vetted commands; preserve globbing for /dev/input/event*.
    return PROBES[name] + "\n"


def file_script(path):
    assert path in OPTIONAL_FILES
    return (f'p="{path}"\n'
            'if [ -L "$p" ] || [ ! -f "$p" ]; then exit 21; fi\n'
            'n=$(wc -c < "$p") || exit 22\n'
            f'if [ "$n" -gt {MAX_BYTES} ]; then exit 23; fi\n'
            'cat "$p"\n')


def collect(args):
    if not shutil.which("ssh"):
        raise RuntimeError("ssh executable unavailable")
    if args.out.exists():
        raise FileExistsError("refusing to overwrite " + str(args.out))
    manifest = {
        "collector_revision": COLLECTOR_REV,
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "purpose": "PW3 read-only engineering evidence",
        "policy": "LOCAL_ONLY_NO_REMOTE_WRITES",
        "host_redacted": True, "port": args.port,
        "read_only": True, "no_remote_temp_files": True,
        "host_stdout_cap_bytes": MAX_BYTES, "entries": [], "errors": []
    }
    records = []
    for name in PROBES:
        try:
            result = remote_ssh(args.host, args.port, probe_script(name))
        except TimeoutError:
            manifest["errors"].append({"item": name, "reason": "SSH timeout"})
            continue
        if result.over_limit:
            manifest["errors"].append({"item": name, "reason": "host byte limit exceeded; discarded"})
            continue
        if result.returncode:
            manifest["errors"].append({"item": name, "status": result.returncode,
                                        "error": result.stderr.decode("utf-8", "replace")[:500]})
            continue
        data = result.stdout
        if name == "library_names.txt":
            data = b"\n".join(line for line in data.splitlines()
                              if re.search(rb"lipc|eink|fb|power|pthread|c\.so", line))
            if data:
                data += b"\n"
        records.append(("diagnostics/" + name, data))
    if args.include_init_scripts:
        for path in OPTIONAL_FILES:
            try:
                result = remote_ssh(args.host, args.port, file_script(path))
                if result.returncode == 0 and not result.over_limit:
                    records.append(("optional-init" + path, result.stdout))
                else:
                    manifest["errors"].append({"item": path, "reason": "missing, symlink, oversized or SSH error"})
            except TimeoutError:
                manifest["errors"].append({"item": path, "reason": "SSH timeout"})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.out, "x", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in records:
            z.writestr(name, data)
            manifest["entries"].append({"name": name, "bytes": len(data),
                                         "sha256": hashlib.sha256(data).hexdigest()})
        z.writestr("MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        z.writestr("SAFETY.txt", "Read-only SSH diagnostics; no remote writes. Local ZIP only.\n"
                   "Review for identifying information before sharing; never commit captures to public GitHub.\n")
    print("COLLECTOR_REV:", COLLECTOR_REV)
    print("LOCAL_ZIP:", args.out)
    print("LOCAL_ZIP_SHA256:", hashlib.sha256(args.out.read_bytes()).hexdigest())
    print("COLLECTED:", len(records), "ERRORS:", len(manifest["errors"]))
    print("DO_NOT_UPLOAD_RAW_ARCHIVE_TO_PUBLIC_GITHUB")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=COLLECTOR_REV)
    parser.add_argument("--host", default="192.168.8.102")
    parser.add_argument("--port", type=int, default=2222)
    parser.add_argument("--out", type=Path, default=Path("pw3-readonly-evidence-v6.zip"))
    parser.add_argument("--collect", action="store_true", help="explicit opt in to SSH collection")
    parser.add_argument("--include-init-scripts", action="store_true", help="add optional init text files; may contain secrets")
    args = parser.parse_args()
    if not args.collect:
        print("COLLECTOR_REV:", COLLECTOR_REV)
        print("DRY_RUN_ONLY: No connection will be made.")
        print("Host:", args.host, "port:", args.port, "destination:", args.out)
        print("Fixed read-only probes:", len(PROBES))
        print("Optional init files:", len(OPTIONAL_FILES) if args.include_init_scripts else 0)
        print("To connect: add --collect. Never publish raw captures.")
        return 0
    try:
        collect(args)
    except (ValueError, OSError, RuntimeError, FileExistsError) as exc:
        print("COLLECTION_FAILED:", exc, file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
