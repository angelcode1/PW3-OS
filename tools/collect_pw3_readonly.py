#!/usr/bin/env python3
"""Opt-in, allowlisted Kindle PW3 read-only evidence collection via SSH.

Dry run by default. Never uploads, modifies Kindle filesystem, runs boot actions,
calls LIPC, or downloads private user storage. ZIP is created on the Mac only.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

MAX_BYTES = 32768
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

def remote_ssh(host, port, script):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.:-]{0,252}", host) or host.startswith("-"):
        raise ValueError("invalid host")
    if not 1 <= port <= 65535:
        raise ValueError("invalid port")
    argv = ["ssh", "-T", "-o", "ConnectTimeout=8", "-o", "BatchMode=no",
            "-o", "StrictHostKeyChecking=ask", "-p", str(port), "root@" + host, "sh", "-s"]
    return subprocess.run(argv, input=script.encode(), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=25, check=False)

def bounded_probe(name, command):
    """Cap remote stdout using POSIX dd, supported by older BusyBox."""
    return ("set -f\ncommand -v dd >/dev/null 2>&1 || exit 127\n"
            + "( " + command + f" ) | dd bs=1 count={MAX_BYTES} 2>/dev/null\n")


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
    manifest = {"purpose":"PW3 read-only engineering evidence",
                "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "policy":"LOCAL_ONLY_NO_REMOTE_WRITES",
                "host_redacted":True, "port":args.port, "entries":[], "errors":[]}
    records = []
    for name,cmd in PROBES.items():
        result = remote_ssh(args.host,args.port, bounded_probe(name,cmd))
        data = result.stdout[:MAX_BYTES]
        if name == "library_names.txt":
            # Old BusyBox rejects grep -E. Filter library names locally.
            data = b"\n".join(line for line in data.splitlines()
                              if re.search(rb"lipc|eink|fb|power|pthread|c\.so", line))
            if data:
                data += b"\n"
        if result.returncode:
            manifest["errors"].append({"item":name,"status":result.returncode,
                         "error":result.stderr.decode("utf8","replace")[:500]})
        else:
            records.append(("diagnostics/"+name,data))
            if len(result.stdout) >= MAX_BYTES:
                manifest.setdefault("possible_truncations", []).append(name)
    if args.include_init_scripts:
        for path in OPTIONAL_FILES:
            result = remote_ssh(args.host,args.port,file_script(path))
            if result.returncode == 0 and len(result.stdout) <= MAX_BYTES:
                records.append(("optional-init"+path,result.stdout))
            else:
                manifest["errors"].append({"item":path,"status":result.returncode,
                             "reason":"missing, symlink, oversized or SSH error"})
    args.out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.out,"x",compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in records:
            z.writestr(name,data)
            manifest["entries"].append({"name":name,"bytes":len(data),
                               "sha256":hashlib.sha256(data).hexdigest()})
        z.writestr("MANIFEST.json",json.dumps(manifest,indent=2,sort_keys=True)+"\n")
        z.writestr("SAFETY.txt","READ-ONLY SSH. LOCAL ZIP ONLY. NEVER PUSH RAW CAPTURES TO PUBLIC GITHUB.\n")
    print("LOCAL_ZIP:",args.out)
    print("LOCAL_ZIP_SHA256:",hashlib.sha256(args.out.read_bytes()).hexdigest())
    print("COLLECTED:",len(records),"ERRORS:",len(manifest["errors"]))
    print("DO_NOT_UPLOAD_RAW_ARCHIVE_TO_PUBLIC_GITHUB")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host",default="192.168.8.102")
    p.add_argument("--port",type=int,default=2222)
    p.add_argument("--out",type=Path,default=Path("pw3-readonly-evidence.zip"))
    p.add_argument("--collect",action="store_true",help="explicitly opt in to SSH")
    p.add_argument("--include-init-scripts",action="store_true",
                   help="optional allowlisted init files; review locally for secrets")
    args=p.parse_args()
    if not args.collect:
        print("DRY_RUN_ONLY: No connection will be made.")
        print("Host:",args.host,"port:",args.port,"destination:",args.out)
        print("Fixed read-only probes:",len(PROBES))
        print("Optional init-file reads:",len(OPTIONAL_FILES) if args.include_init_scripts else 0)
        print("To connect: add --collect. Do not upload captures to public GitHub.")
        return 0
    try:
        collect(args)
        return 0
    except (OSError,RuntimeError,ValueError,subprocess.TimeoutExpired) as exc:
        print("COLLECTION_FAILED:",exc,file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
