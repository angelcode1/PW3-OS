#!/usr/bin/env python3
"""R3877.45: fail-closed QEMU ARMv7 probe from stopped disposable containers.

No derived-image creation, commit/import, image pull, privileged operations,
binfmt registration, guest networking, host volumes, Kindle access, or firmware
writes. Explicit --authorize-offline-qemu required for Docker operations.
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

MILESTONE = 'R3877.45'
HOLD = 'NOT_BOOTABLE'
PARENT = 'pw3-r3877-signed-alpine:3.24.3-armv7-dc1ddfaf03ed'
HELPER = 'tonistiigi/binfmt:qemu-v10.0.4'
HELPER_DIGEST = 'tonistiigi/binfmt@sha256:8f58e6214f4cc9dc83ce8f5acad1ece508eb6b20e696a8c1e9f274481982c541'
QEMU_ARM_SHA256 = '3347b95a4006c1eb19b93ba09469a2c42b04fe5d89a430ce96cbf2a2367cf5c1'
BUSYBOX_SHA256 = 'df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c'
HEX_SHA = re.compile(r'sha256:[0-9a-f]{64}\Z')
HEX_CID = re.compile(r'[0-9a-f]{64}\Z')

PROBES = (
    ('qemu_version', ('--version',)),
    ('busybox_double_dash_help', ('/bin/busybox', '--help')),
    ('busybox_true', ('/bin/busybox', 'true')),
    ('busybox_uname_machine', ('/bin/busybox', 'uname', '-m')),
)

class Hold(Exception):
    pass


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def elf_summary(path):
    b = Path(path).read_bytes()[:64]
    if len(b) < 52 or b[:4] != b'\x7fELF' or b[5] != 1 or b[4] not in (1, 2):
        raise Hold('ELF_HEADER_INVALID')
    bits = 32 if b[4] == 1 else 64
    return {'bits': bits, 'machine': struct.unpack_from('<H', b, 18)[0],
            'e_flags': f'0x{struct.unpack_from("<I", b, 36 if bits == 32 else 48)[0]:08x}'}


def docker(args, timeout=100, allow_nonzero=False):
    if not isinstance(args, (list, tuple)) or not args or not all(isinstance(x, str) for x in args):
        raise Hold('INVALID_DOCKER_ARGV')
    try:
        cp = subprocess.run(['docker', *args], capture_output=True, text=True,
                            errors='replace', timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as ex:
        raise Hold('DOCKER_INVOCATION_FAILED_OR_TIMED_OUT:' + args[0]) from ex
    if len(cp.stdout) + len(cp.stderr) > 1_000_000:
        raise Hold('DOCKER_OUTPUT_LIMIT_EXCEEDED')
    if cp.returncode != 0 and not allow_nonzero:
        raise Hold('DOCKER_COMMAND_FAILED:' + args[0])
    return cp


def inspect_json(kind, ref):
    cp = docker([kind, 'inspect', ref])
    try:
        objects = json.loads(cp.stdout)
        if not isinstance(objects, list) or len(objects) != 1 or not isinstance(objects[0], dict):
            raise ValueError('Invalid inspect array')
        return objects[0]
    except (ValueError, TypeError) as ex:
        raise Hold('INSPECT_JSON_INVALID:' + kind) from ex


def image_info(ref):
    x = inspect_json('image', ref)
    if not isinstance(x.get('Id'), str) or not HEX_SHA.fullmatch(x['Id']):
        raise Hold('IMAGE_ID_INVALID')
    return x


def summarized_platform(x):
    return {'os': x.get('Os'), 'architecture': x.get('Architecture'),
            'variant': x.get('Variant') or ''}


def validate_guest(x, parent_id, argv):
    """Inspect enforcement, never infer from the Docker CLI alone."""
    h = x.get('HostConfig') or {}
    c = x.get('Config') or {}
    st = x.get('State') or {}
    expected = list(argv)
    if x.get('Image') != parent_id:
        raise Hold('GUEST_PARENT_IMAGE_ID_MISMATCH')
    if st.get('Status') != 'created' or st.get('Running'):
        raise Hold('GUEST_NOT_STOPPED_BEFORE_INJECTION')
    if x.get('Path') != '/usr/bin/qemu-arm-static' or x.get('Args') != expected:
        raise Hold('GUEST_EXEC_ARGV_MISMATCH')
    if c.get('User') != '65534:65534' or c.get('Entrypoint') != ['/usr/bin/qemu-arm-static']:
        raise Hold('GUEST_USER_OR_ENTRYPOINT_MISMATCH')
    if h.get('ReadonlyRootfs') is not True or h.get('NetworkMode') != 'none':
        raise Hold('GUEST_READONLY_OR_NETWORK_MISMATCH')
    if h.get('Privileged') is not False or h.get('Binds') not in (None, []):
        raise Hold('GUEST_PRIVILEGED_OR_BIND_MISMATCH')
    if x.get('Mounts') not in (None, []):
        raise Hold('GUEST_HOST_MOUNT_PRESENT')
    if h.get('Devices') not in (None, []) or h.get('DeviceRequests') not in (None, []):
        raise Hold('GUEST_DEVICE_MOUNT_PRESENT')
    if 'ALL' not in [v.upper() for v in (h.get('CapDrop') or [])]:
        raise Hold('GUEST_CAPABILITIES_NOT_DROPPED')
    if 'no-new-privileges' not in (h.get('SecurityOpt') or []):
        raise Hold('GUEST_NO_NEW_PRIVILEGES_NOT_SET')
    if h.get('PidsLimit') != 64 or h.get('Memory') != 268435456:
        raise Hold('GUEST_RESOURCE_LIMITS_NOT_SET')
    return True


def probe_status(name, rc, output):
    if name == 'qemu_version':
        return rc == 0 and output.startswith('qemu-arm version 10.0.4')
    if name == 'busybox_double_dash_help':
        return rc == 0 and re.search(r'\bBusyBox v[0-9]', output) is not None
    if name == 'busybox_true':
        return rc == 0 and output == ''
    if name == 'busybox_uname_machine':
        return rc == 0 and output.strip() == 'armv7l'
    return False


def preflight():
    return dict(milestone=MILESTONE, result='HOLD',
                diagnostic='R3877_45_OFFLINE_NO_DOCKER_PREFLIGHT',
                immutable_hold=HOLD, authorized_qemu_execution_performed=False,
                physical_device_access_performed=False, firmware_write_performed=False,
                boot_performed=False, derived_image_created=False,
                original_image_modified=False, binfmt_registration_changed=False)


def run():
    r = preflight()
    r.update(diagnostic='R3877_45_DIRECT_STOPPED_GUEST_ATTEMPTED',
             offline_qemu_authorized=True, docker_server_architecture=None,
             original_image_unchanged=False, all_created_containers_removed=False,
             no_guest_network_or_host_mounts=False, privileged_container_invoked=False,
             derived_image_created=False, runtime_probes={}, guest_containers_created=0,
             error_category=None)
    created = []
    parent_id = None
    cleanup_ok = True
    try:
        cp = docker(['version', '--format', '{{json .Server}}'])
        obj = json.loads(cp.stdout)
        if not isinstance(obj, dict) or str(obj.get('Arch', obj.get('Architecture', ''))).lower() not in ('arm64', 'aarch64'):
            raise Hold('DOCKER_SERVER_NOT_ARM64')
        r['docker_server_architecture'] = str(obj.get('Arch', obj.get('Architecture', '')))
        parent = image_info(PARENT)
        parent_id = parent['Id']
        r['original_image_id_sha256'] = parent_id
        r['parent_platform'] = summarized_platform(parent)
        if parent.get('Os') != 'linux' or parent.get('Architecture') != 'arm' or parent.get('Variant') not in ('v7', '7'):
            raise Hold('PARENT_NOT_EXACT_LINUX_ARMV7')
        helper = image_info(HELPER)
        if helper.get('Os') != 'linux' or helper.get('Architecture') not in ('arm64', 'aarch64'):
            raise Hold('HELPER_NOT_ARM64')
        if HELPER_DIGEST not in (helper.get('RepoDigests') or []):
            raise Hold('HELPER_DIGEST_MISMATCH')
        r['helper_image_id_sha256'] = helper['Id']
        with tempfile.TemporaryDirectory(prefix='pw3-r45-') as d:
            qemu = Path(d) / 'qemu-arm-static'
            busybox = Path(d) / 'busybox'
            helper_cid = docker(['create', '--platform', 'linux/arm64', '--pull', 'never',
                                 '--network', 'none', '--name', 'pw3-r45-helper-' + uuid.uuid4().hex[:12],
                                 '--entrypoint', '/bin/true', HELPER]).stdout.strip()
            if not HEX_CID.fullmatch(helper_cid):
                raise Hold('HELPER_CONTAINER_ID_INVALID')
            created.append(helper_cid)
            docker(['cp', '-L', helper_cid + ':/usr/bin/qemu-arm', str(qemu)])
            if sha256_file(qemu) != QEMU_ARM_SHA256 or elf_summary(qemu)['bits'] != 64 or elf_summary(qemu)['machine'] != 183:
                raise Hold('QEMU_PIN_OR_ELF_INVALID')
            r['qemu_binary_sha256'] = QEMU_ARM_SHA256

            prep_cid = docker(['create', '--platform', 'linux/arm/v7', '--pull', 'never',
                               '--network', 'none', '--name', 'pw3-r45-prep-' + uuid.uuid4().hex[:12],
                               '--entrypoint', '/bin/true', PARENT]).stdout.strip()
            if not HEX_CID.fullmatch(prep_cid):
                raise Hold('PREP_CONTAINER_ID_INVALID')
            created.append(prep_cid)
            prep = inspect_json('container', prep_cid)
            if prep.get('Image') != parent_id or (prep.get('State') or {}).get('Status') != 'created':
                raise Hold('PREP_PARENT_OR_STOPPED_MISMATCH')
            docker(['cp', '-L', prep_cid + ':/bin/busybox', str(busybox)])
            elf = elf_summary(busybox)
            if elf['bits'] != 32 or elf['machine'] != 40 or elf['e_flags'] != '0x05000400' or sha256_file(busybox) != BUSYBOX_SHA256:
                raise Hold('BUSYBOX_PIN_OR_ELF_INVALID')
            r['busybox_elf'] = elf
            r['busybox_sha256'] = BUSYBOX_SHA256

            r['no_guest_network_or_host_mounts'] = True
            for name, args in PROBES:
                cid = docker(['create', '--platform', 'linux/arm/v7', '--pull', 'never',
                              '--network', 'none', '--read-only', '--pids-limit', '64', '--memory', '256m',
                              '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                              '--user', '65534:65534', '--name', 'pw3-r45-guest-' + uuid.uuid4().hex[:12],
                              '--entrypoint', '/usr/bin/qemu-arm-static', PARENT, *args]).stdout.strip()
                if not HEX_CID.fullmatch(cid):
                    raise Hold('GUEST_CONTAINER_ID_INVALID')
                created.append(cid)
                r['guest_containers_created'] += 1
                before = inspect_json('container', cid)
                validate_guest(before, parent_id, args)
                docker(['cp', str(qemu), cid + ':/usr/bin/qemu-arm-static'])
                after = inspect_json('container', cid)
                validate_guest(after, parent_id, args)
                # Verify exactly the pinned executable resides in the stopped guest.
                roundtrip = Path(d) / ('roundtrip-' + name)
                docker(['cp', '-L', cid + ':/usr/bin/qemu-arm-static', str(roundtrip)])
                if sha256_file(roundtrip) != QEMU_ARM_SHA256:
                    raise Hold('GUEST_QEMU_COPY_READBACK_MISMATCH:' + name)
                r['authorized_qemu_execution_performed'] = True
                started = docker(['start', '--attach', cid], timeout=110, allow_nonzero=True)
                state = (inspect_json('container', cid).get('State') or {})
                if state.get('Status') != 'exited' or state.get('Running') or not isinstance(state.get('ExitCode'), int):
                    raise Hold('GUEST_STOP_STATE_UNVERIFIED:' + name)
                if state.get('OOMKilled') is not False:
                    raise Hold('GUEST_KILLED_OR_UNKNOWN:' + name)
                out = started.stdout + started.stderr
                ok = probe_status(name, state['ExitCode'], out)
                r['runtime_probes'][name] = dict(status='PASS' if ok else 'HOLD', exit_code=state['ExitCode'],
                                                docker_start_exit_code=started.returncode,
                                                output_sha256=hashlib.sha256(out.encode()).hexdigest(),
                                                output_prefix=out[:220] if name != 'busybox_true' else '')
                if not ok:
                    raise Hold('GUEST_PROBE_FAILED:' + name)
            r['result'] = 'PASS_ARM32_BUSYBOX_QEMU_ONLY'
            r['diagnostic'] = 'R3877_45_DIRECT_STOPPED_GUEST_PROBES_PASSED_NOT_BOOTABLE'
    except (Hold, ValueError, TypeError, KeyError) as ex:
        r['error_category'] = str(ex).splitlines()[0][:128]
    finally:
        for cid in reversed(created):
            try:
                rc = docker(['rm', '-f', cid], timeout=35, allow_nonzero=True)
                cleanup_ok = cleanup_ok and rc.returncode == 0
            except Hold:
                cleanup_ok = False
        r['all_created_containers_removed'] = cleanup_ok and bool(created)
        if not cleanup_ok:
            r['container_ids_requiring_manual_review'] = created
        if parent_id:
            try:
                r['original_image_unchanged'] = image_info(PARENT)['Id'] == parent_id
            except Hold:
                pass
        if not r['all_created_containers_removed'] or not r['original_image_unchanged']:
            if r['result'].startswith('PASS'):
                r['result'] = 'HOLD_CLEANUP_OR_PARENT_IMAGE_UNVERIFIED'
            if not r['error_category']:
                r['error_category'] = 'CLEANUP_OR_PARENT_IMAGE_NOT_VERIFIED'
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--authorize-offline-qemu', action='store_true',
                    help='Explicitly authorize offline QEMU execution only in disposable stopped-then-started containers')
    args = ap.parse_args(argv)
    r = run() if args.authorize_offline_qemu else preflight()
    print(json.dumps(r, sort_keys=True, separators=(',', ':')))
    return 0 if r['result'] == 'PASS_ARM32_BUSYBOX_QEMU_ONLY' else 2


if __name__ == '__main__':
    sys.exit(main())
