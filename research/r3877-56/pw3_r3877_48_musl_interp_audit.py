#!/usr/bin/env python3
"""R3877.48: verify PT_INTERP and cached musl loader in a stopped ARMv7 image.

Research only. NOT_BOOTABLE. Default invokes NO Docker. Authorized mode only
inspects a pinned cached image, copies two files from a STOPPED container,
then removes it. No ARM code execution, network, mounts, Kindle or image write.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import uuid

MILESTONE = 'R3877.48'
PARENT = 'pw3-r3877-signed-alpine:3.24.3-armv7-dc1ddfaf03ed'
PARENT_ID = 'sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a'
BUSYBOX_SHA256 = 'df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c'
LOADER_SHA256 = '2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990'
INTERP = '/lib/ld-musl-armhf.so.1'
SHA_ID = re.compile(r'^sha256:[0-9a-f]{64}$')
CID_RE = re.compile(r'^[0-9a-f]{64}$')

class Hold(Exception):
    pass


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def elf32_arm(path):
    """Bounded, strict ELF32 ARM program-header audit, not a full ELF loader."""
    p = Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size > (24 << 20):
        raise Hold('ELF_UNSAFE_OR_OVERSIZE')
    b = p.read_bytes()
    if len(b) < 52 or b[:7] != b'\x7fELF\x01\x01\x01':
        raise Hold('ELF32_LE_HEADER_INVALID')
    etype, machine, version = struct.unpack_from('<HHI', b, 16)
    flags = struct.unpack_from('<I', b, 36)[0]
    phoff = struct.unpack_from('<I', b, 28)[0]
    phentsize, phnum = struct.unpack_from('<HH', b, 42)
    if machine != 40 or version != 1 or etype not in (2, 3):
        raise Hold('ELF_MACHINE_OR_TYPE_INVALID')
    if flags != 0x05000400:
        raise Hold('ELF_EABI_HARDFLOAT_MISMATCH')
    if not (1 <= phnum <= 128) or not (32 <= phentsize <= 128):
        raise Hold('ELF_PROGRAM_HEADER_COUNT_OR_STRIDE_INVALID')
    if phoff < 52 or phoff + phnum * phentsize > len(b):
        raise Hold('ELF_PROGRAM_HEADERS_OUT_OF_BOUNDS')
    interps = []
    dynamic = 0
    loads = 0
    for i in range(phnum):
        off = phoff + i * phentsize
        kind, payload_off = struct.unpack_from('<II', b, off)
        payload_len = struct.unpack_from('<I', b, off + 16)[0]
        if kind == 1:
            loads += 1
        if kind == 2:
            dynamic += 1
        if kind == 3:
            if payload_len < 2 or payload_len > 256 or payload_off + payload_len > len(b):
                raise Hold('ELF_INTERPRETER_OUT_OF_BOUNDS')
            raw = b[payload_off:payload_off + payload_len]
            if not raw.endswith(b'\0') or b'\0' in raw[:-1]:
                raise Hold('ELF_INTERPRETER_TERMINATION_INVALID')
            try:
                s = raw[:-1].decode('ascii')
            except UnicodeDecodeError as exc:
                raise Hold('ELF_INTERPRETER_NONASCII') from exc
            if not s.startswith('/') or '\\' in s or '..' in s or any(ord(c) < 32 for c in s):
                raise Hold('ELF_INTERPRETER_UNSAFE')
            interps.append(s)
    if not loads or len(interps) > 1 or dynamic > 1:
        raise Hold('ELF_PROGRAM_HEADER_SEMANTICS_INVALID')
    return {
        'type': 'ET_DYN' if etype == 3 else 'ET_EXEC',
        'machine': machine,
        'e_flags': f'0x{flags:08x}',
        'pt_interp': interps[0] if interps else None,
        'pt_dynamic_present': dynamic == 1,
        'pt_load_count': loads,
    }


def validate_linkage(busybox, loader):
    if digest(busybox) != BUSYBOX_SHA256:
        raise Hold('BUSYBOX_BYTES_DIFFER_FROM_R47')
    if digest(loader) != LOADER_SHA256:
        raise Hold('LOADER_BYTES_DIFFER_FROM_R24_SIGNED_APK_MATCH')
    a, b = elf32_arm(busybox), elf32_arm(loader)
    if a['pt_interp'] is None:
        raise Hold('BUSYBOX_NO_PT_INTERP_NO_DYNAMIC_LOADER_PROOF')
    if a['pt_interp'] != INTERP:
        raise Hold('BUSYBOX_PT_INTERP_UNEXPECTED')
    if not a['pt_dynamic_present']:
        raise Hold('BUSYBOX_PT_DYNAMIC_ABSENT')
    if b['type'] != 'ET_DYN' or b['pt_interp'] is not None:
        raise Hold('MUSL_LOADER_ELF_UNEXPECTED')
    return {'busybox': a, 'loader': b,
            'busybox_sha256': BUSYBOX_SHA256,
            'loader_sha256': LOADER_SHA256,
            'interpreter_path_matches_pinned_loader': True}


def docker(argv, *, allow_nonzero=False):
    if not isinstance(argv, (list, tuple)) or not argv or not all(isinstance(x, str) for x in argv):
        raise Hold('INVALID_DOCKER_ARGV')
    try:
        p = subprocess.run(['docker', *argv], capture_output=True, text=True,
                           errors='replace', timeout=50, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Hold('DOCKER_UNAVAILABLE_OR_TIMED_OUT:' + argv[0]) from exc
    if len(p.stdout) + len(p.stderr) > (1 << 20):
        raise Hold('DOCKER_OUTPUT_OVERSIZE')
    if p.returncode != 0 and not allow_nonzero:
        raise Hold('DOCKER_COMMAND_FAILED:' + argv[0])
    return p


def inspect_image():
    try:
        j = json.loads(docker(['image', 'inspect', PARENT]).stdout)
        x = j[0]
        if len(j) != 1 or x.get('Id') != PARENT_ID or not SHA_ID.fullmatch(x.get('Id', '')):
            raise ValueError()
        if x.get('Os') != 'linux' or x.get('Architecture') != 'arm' or x.get('Variant') not in ('v7', '7'):
            raise ValueError()
        return x
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise Hold('PARENT_IMAGE_PIN_OR_PLATFORM_MISMATCH') from exc


def inspect_stopped(cid):
    try:
        j = json.loads(docker(['container', 'inspect', cid]).stdout)
        if len(j) != 1:
            raise ValueError()
        x = j[0]
        hc = x['HostConfig']
        st = x['State']
        if x.get('Image') != PARENT_ID or st.get('Status') != 'created' or st.get('Running') is not False:
            raise ValueError()
        if hc.get('NetworkMode') != 'none' or hc.get('Privileged') is not False:
            raise ValueError()
        if hc.get('Binds') not in (None, []) or x.get('Mounts') not in (None, []):
            raise ValueError()
        if hc.get('Devices') not in (None, []) or hc.get('DeviceRequests') not in (None, []):
            raise ValueError()
        if x.get('Path') != '/bin/true':
            raise ValueError()
    except (ValueError, TypeError, KeyError, IndexError) as exc:
        raise Hold('STOPPED_CONTAINER_ISOLATION_UNVERIFIED') from exc


def preflight():
    return dict(milestone=MILESTONE, result='HOLD', immutable_hold='NOT_BOOTABLE',
                diagnostic='R3877_48_NO_DOCKER_PREFLIGHT',
                stopped_image_access_authorized=False,
                arm_binary_execution_performed=False,
                kindle_ssh_sessions=0, physical_device_access_performed=False,
                boot_performed=False, firmware_write_performed=False,
                kernel_3_0_35_compatibility_verified=False,
                recovery_verified=False)


def run():
    r = preflight()
    r.update(diagnostic='R3877_48_STOPPED_IMAGE_ELF_AUDIT',
             stopped_image_access_authorized=True,
             original_image_unchanged=False, stopped_container_removed=False,
             error_category=None)
    cid = None
    baseline_known = False
    cleanup_ok = False
    try:
        inspect_image()
        baseline_known = True
        with tempfile.TemporaryDirectory(prefix='pw3-r48-') as folder:
            create = docker(['create', '--platform', 'linux/arm/v7', '--pull', 'never',
                             '--network', 'none', '--name', 'pw3-r48-static-' + uuid.uuid4().hex[:12],
                             '--entrypoint', '/bin/true', PARENT])
            cid = create.stdout.strip()
            if not CID_RE.fullmatch(cid):
                raise Hold('CREATED_CONTAINER_ID_INVALID')
            inspect_stopped(cid)
            bb = Path(folder) / 'busybox'
            ld = Path(folder) / 'loader'
            docker(['cp', '-L', cid + ':/bin/busybox', str(bb)])
            docker(['cp', '-L', cid + ':' + INTERP, str(ld)])
            inspect_stopped(cid)
            r['linkage'] = validate_linkage(bb, ld)
            r['result'] = 'PASS_PINNED_BUSYBOX_MUSL_PT_INTERP_LINKAGE_ONLY'
    except (Hold, OSError, ValueError, TypeError, KeyError) as exc:
        r['error_category'] = (str(exc).splitlines() or ['UNKNOWN'])[0][:128]
    finally:
        if cid is not None:
            try:
                gone = docker(['rm', '-f', cid], allow_nonzero=True)
                check = docker(['container', 'inspect', cid], allow_nonzero=True)
                cleanup_ok = gone.returncode == 0 and check.returncode != 0 and bool(re.search('No such (?:container|object)', check.stderr, re.I))
            except Hold:
                cleanup_ok = False
        r['stopped_container_removed'] = cleanup_ok
        if baseline_known:
            try:
                inspect_image()
                r['original_image_unchanged'] = True
            except Hold:
                r['original_image_unchanged'] = False
        if r['result'].startswith('PASS') and (not cleanup_ok or not r['original_image_unchanged']):
            r['result'] = 'HOLD'
            r['error_category'] = 'CLEANUP_OR_PARENT_UNVERIFIED'
        if not cleanup_ok and not r.get('error_category'):
            r['error_category'] = 'CONTAINER_CLEANUP_UNVERIFIED'
    return r


def main(args=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--authorize-stopped-image-audit', action='store_true')
    opts = ap.parse_args(args)
    r = run() if opts.authorize_stopped_image_audit else preflight()
    print(json.dumps(r, sort_keys=True, separators=(',', ':')))
    return 0 if r['result'] == 'PASS_PINNED_BUSYBOX_MUSL_PT_INTERP_LINKAGE_ONLY' else 2

if __name__ == '__main__':
    sys.exit(main())
