"""Pinned NetSurf Framebuffer package and safe staged-binary verification.

This module never starts a browser and never opens a physical framebuffer.
"""
from pathlib import Path
import struct

NETSURF_PACKAGE = "netsurf-framebuffer"
NETSURF_VERSION = "3.11-r1"
NETSURF_EXECUTABLE = "usr/bin/netsurf-fb"


def _packages(index_paths):
    for path in map(Path, index_paths):
        if not path.is_file():
            raise FileNotFoundError(f"APKINDEX missing: {path}")
        for entry in path.read_text(encoding="utf-8").split("\n\n"):
            fields = {}
            for line in entry.splitlines():
                if len(line) >= 3 and line[1] == ":":
                    fields.setdefault(line[0], line[2:])
            if "P" in fields:
                yield fields


def find_package(index_paths, name):
    for entry in _packages(index_paths):
        if entry["P"] == name:
            return {"name": name, "version": entry.get("V", "unknown"),
                    "state": "available-not-installed"}
    return None


def require_netsurf(index_paths):
    entry = find_package(index_paths, NETSURF_PACKAGE)
    if entry is None:
        raise RuntimeError("Alpine ARMv7 NetSurf framebuffer package missing")
    if entry["version"] != NETSURF_VERSION:
        raise RuntimeError(
            f"NetSurf version changed: {entry['version']} != {NETSURF_VERSION}")
    return entry


def verify_browser_staged(root, packages):
    """Check installed ARM ELF, resource directory, and package manifest.

    Static checks do NOT establish runtime, Linux 3.0.35, EPDC or input support.
    """
    root = Path(root)
    expected = "community/" + NETSURF_PACKAGE + "-" + NETSURF_VERSION
    if expected not in packages:
        raise RuntimeError("NetSurf missing from resolved package closure")
    executable = root / NETSURF_EXECUTABLE
    if not executable.is_file():
        raise RuntimeError("NetSurf ARMv7 executable absent from rootfs")
    with executable.open("rb") as f:
        eh = f.read(52)
    if (len(eh) < 52 or eh[:4] != b"\x7fELF" or eh[4] != 1
            or eh[5] != 1 or struct.unpack_from("<H", eh, 18)[0] != 40):
        raise RuntimeError("NetSurf executable is not ELF32 little-endian ARM")
    if not (root / "usr/share/netsurf").is_dir():
        raise RuntimeError("NetSurf runtime resources missing")
    return {"name": NETSURF_PACKAGE, "version": NETSURF_VERSION,
            "binary": "/" + NETSURF_EXECUTABLE,
            "state": "staged-unverified",
            "arm_elf_verified": True,
            "runtime_verified": False,
            "epdc_verified": False,
            "input_verified": False}
