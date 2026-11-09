#!/usr/bin/env python3
"""R3877.47: verify ARMv7 applets before diagnosing BusyBox help argv0.

Default: no Docker activity (HOLD). --authorize-offline-qemu first attempts an
injection into a read-only stopped guest. A writable disposable guest is NEVER
used unless the operator additionally supplies --allow-disposable-writable-layer
and the read-only copy fails with an identified read-only-rootfs error.

Research and educational only. NO KINDLE, BOOT, FLASH, HOST BINFMTS,
PRIVILEGED CONTAINERS, GUEST NETWORKING, OR HOST FILESYSTEM MOUNTS.
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

MILESTONE = 'R3877.47'
HOLD = 'NOT_BOOTABLE'
PARENT = 'pw3-r3877-signed-alpine:3.24.3-armv7-dc1ddfaf03ed'
PARENT_ID = 'sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a'
HELPER = 'tonistiigi/binfmt:qemu-v10.0.4'
HELPER_DIGEST = 'tonistiigi/binfmt@sha256:8f58e6214f4cc9dc83ce8f5acad1ece508eb6b20e696a8c1e9f274481982c541'
QEMU_SHA256 = '3347b95a4006c1eb19b93ba09469a2c42b04fe5d89a430ce96cbf2a2367cf5c1'
BUSYBOX_SHA256 = 'df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c'
HEX_ID = re.compile(r'^[0-9a-f]{64}$')
HEX_IMAGE = re.compile(r'^sha256:[0-9a-f]{64}$')
READONLY_RE = re.compile(r'(?:rootfs.{0,50}read.only|read.only.{0,50}(?:file\s*system|rootfs)|erofs)',re.I)
ECHO_MARKER = 'PW3_R3877_47_ARMV7_QEMU_OK'
KNOWN_HELP_OUTPUT = '-help: applet not found\n'
HELP_PROBES = frozenset({'busybox_default_help', 'busybox_forced_argv0_help'})
PROBES = (
    ('qemu_version', ('--version',)),
    ('busybox_true', ('/bin/busybox', 'true')),
    ('busybox_uname_machine', ('/bin/busybox', 'uname', '-m')),
    ('busybox_echo_marker', ('/bin/busybox', 'echo', ECHO_MARKER)),
    ('busybox_default_help', ('/bin/busybox', '--help')),
    # QEMU -0 forces target argv[0]; compare with unmodified invocation.
    ('busybox_forced_argv0_help', ('-0', '/bin/busybox', '/bin/busybox', '--help')),
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


def docker(argv, timeout=100, allow_nonzero=False):
    if not isinstance(argv, (list, tuple)) or not argv or not all(isinstance(x, str) for x in argv):
        raise Hold('INVALID_DOCKER_ARGV')
    try:
        result = subprocess.run(['docker', *argv], capture_output=True, text=True,
                                errors='replace', timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Hold('DOCKER_INVOCATION_FAILED_OR_TIMED_OUT:' + argv[0]) from exc
    if len(result.stdout) + len(result.stderr) > 1000000:
        raise Hold('OVERSIZE_DOCKER_OUTPUT')
    if result.returncode and not allow_nonzero:
        raise Hold('DOCKER_COMMAND_FAILED:' + argv[0])
    return result


def inspect(kind, ident):
    cp = docker([kind, 'inspect', ident])
    try:
        js = json.loads(cp.stdout)
        if not isinstance(js, list) or len(js) != 1 or not isinstance(js[0], dict):
            raise ValueError('invalid inspect response')
        return js[0]
    except (ValueError, TypeError) as exc:
        raise Hold('INSPECT_INVALID:' + kind) from exc


def image_info(ref):
    js = inspect('image', ref)
    if not isinstance(js.get('Id'), str) or not HEX_IMAGE.fullmatch(js['Id']):
        raise Hold('IMAGE_ID_INVALID')
    return js


def probe_ok(name, rc, output):
    if name == 'qemu_version':
        return rc == 0 and output.startswith('qemu-arm version 10.0.4')
    if name in HELP_PROBES:
        return rc == 0 and re.search(r'\bBusyBox v[0-9]', output) is not None
    if name == 'busybox_true':
        return rc == 0 and output == ''
    if name == 'busybox_uname_machine':
        return rc == 0 and output == 'armv7l\n'
    if name == 'busybox_echo_marker':
        return rc == 0 and output == ECHO_MARKER + '\n'
    return False


def help_diagnostic(name, rc, output):
    """Never treat an applet-dispatch error as proof of working help."""
    if name not in HELP_PROBES:
        raise ValueError('NOT_A_HELP_PROBE')
    if probe_ok(name, rc, output):
        return 'HELP_OK'
    if rc == 127 and output == KNOWN_HELP_OUTPUT:
        return 'KNOWN_BUSYBOX_APPLET_DISPATCH_ANOMALY'
    return 'HELP_UNEXPECTED_HOLD'


def classify_cp_error(cp):
    """Do not guess Docker's failure family from its generic exit code."""
    combined = cp.stdout + cp.stderr
    return {
        'classification': ('READONLY_ROOTFS_COPY_REJECTED' if cp.returncode != 0
                           and READONLY_RE.search(combined) else 'DOCKER_CP_FAILURE_UNCLASSIFIED'),
        'exit_code': cp.returncode,
        'output_sha256': hashlib.sha256(combined.encode()).hexdigest(),
        'output_bytes': len(combined.encode()),
        'raw_error_published': False,
    }


def validate_guest(js, argv, readonly):
    st = js.get('State') or {}
    hc = js.get('HostConfig') or {}
    cfg = js.get('Config') or {}
    if js.get('Image') != PARENT_ID:
        raise Hold('GUEST_IMAGE_ID_MISMATCH')
    if st.get('Status') != 'created' or st.get('Running') is not False:
        raise Hold('GUEST_NOT_STOPPED')
    if js.get('Path') != '/usr/bin/qemu-arm-static' or js.get('Args') != list(argv):
        raise Hold('GUEST_ARGV_MISMATCH')
    if cfg.get('User') != '65534:65534' or cfg.get('Entrypoint') != ['/usr/bin/qemu-arm-static']:
        raise Hold('GUEST_UNPRIVILEGED_IDENTITY_MISMATCH')
    if hc.get('ReadonlyRootfs') is not readonly:
        raise Hold('GUEST_ROOTFS_POLICY_MISMATCH')
    if hc.get('NetworkMode') != 'none' or hc.get('Privileged') is not False:
        raise Hold('GUEST_NETWORK_OR_PRIVILEGE_MISMATCH')
    if hc.get('Binds') not in (None, []) or js.get('Mounts') not in (None, []):
        raise Hold('GUEST_HOST_MOUNT_PRESENT')
    if hc.get('Devices') not in (None, []) or hc.get('DeviceRequests') not in (None, []):
        raise Hold('GUEST_DEVICE_PRESENT')
    if 'ALL' not in [str(x).upper() for x in hc.get('CapDrop') or []]:
        raise Hold('GUEST_CAPABILITIES_NOT_DROPPED')
    if 'no-new-privileges' not in (hc.get('SecurityOpt') or []):
        raise Hold('GUEST_NO_NEW_PRIVILEGES_MISSING')
    if hc.get('PidsLimit') != 64 or hc.get('Memory') != 268435456:
        raise Hold('GUEST_RESOURCE_LIMITS_MISMATCH')
    return True


def guest_create(argv, readonly):
    args = ['create', '--platform', 'linux/arm/v7', '--pull', 'never', '--network', 'none']
    if readonly:
        args.append('--read-only')
    args.extend(['--pids-limit', '64', '--memory', '256m', '--cap-drop', 'ALL',
                 '--security-opt', 'no-new-privileges', '--user', '65534:65534',
                 '--name', 'pw3-r47-guest-' + uuid.uuid4().hex[:12],
                 '--entrypoint', '/usr/bin/qemu-arm-static', PARENT, *argv])
    return args


def audit_diff(cid):
    """For the writable fallback, allow only the known emulator injection.

    Docker diff reports A/C/D paths. No guest-created or altered files other
    than the preloaded QEMU executable and its two ancestor directories.
    """
    cp = docker(['diff', cid])
    observed = [line.strip() for line in cp.stdout.splitlines() if line.strip()]
    allowed = {'A /usr/bin/qemu-arm-static', 'C /usr/bin/qemu-arm-static',
               'C /usr/bin', 'C /usr'}
    if any(line not in allowed for line in observed) or not any(
            line.endswith(' /usr/bin/qemu-arm-static') for line in observed):
        raise Hold('WRITABLE_GUEST_UNEXPECTED_FILESYSTEM_DIFF')
    return {'allowed_changes_only': True, 'reported_change_count': len(observed),
            'output_sha256': hashlib.sha256(cp.stdout.encode()).hexdigest()}


def preflight():
    return {'milestone': MILESTONE, 'result': 'HOLD', 'immutable_hold': HOLD,
            'diagnostic': 'R3877_47_PREFLIGHT_ZERO_DOCKER',
            'authorized_qemu_execution_performed': False,
            'physical_device_access_performed': False,
            'firmware_write_performed': False, 'boot_performed': False,
            'derived_image_created': False, 'original_image_modified': False,
            'privileged_container_invoked': False, 'host_mounts_or_guest_network_enabled': False,
            'binfmt_registration_changed': False}


def run(allow_writable=False):
    r = preflight()
    r.update(diagnostic='R3877_47_OFFLINE_QEMU_READONLY_COPY_GATE',
             offline_qemu_authorized=True,
             writable_disposable_layer_authorized=bool(allow_writable),
             writable_fallback_used=False,
             read_only_copy_probe=None,
             error_category=None,
             original_image_unchanged=False,
             all_created_containers_removed=False,
             runtime_probes={}, guest_containers_created=0,
             positive_arm32_applets_verified=False,
             help_diagnostics={}, argv0_override_changes_help_result=None)
    created = []
    cleanup_ok = True
    parent_known = False
    try:
        v = json.loads(docker(['version', '--format', '{{json .Server}}']).stdout)
        if not isinstance(v, dict) or str(v.get('Arch', v.get('Architecture',''))).lower() not in ('arm64','aarch64'):
            raise Hold('DOCKER_SERVER_NOT_ARM64')
        r['docker_server_architecture'] = v.get('Arch', v.get('Architecture'))
        parent = image_info(PARENT)
        if parent['Id'] != PARENT_ID or parent.get('Os') != 'linux' or parent.get('Architecture') != 'arm' or parent.get('Variant') not in ('v7', '7'):
            raise Hold('PARENT_ID_OR_PLATFORM_MISMATCH')
        parent_known = True
        r['original_image_id_sha256'] = parent['Id']
        helper = image_info(HELPER)
        if (helper.get('Os'), helper.get('Architecture')) not in (('linux','arm64'), ('linux','aarch64')):
            raise Hold('HELPER_PLATFORM_MISMATCH')
        if HELPER_DIGEST not in helper.get('RepoDigests', []):
            raise Hold('HELPER_DIGEST_MISMATCH')
        r['helper_image_id_sha256'] = helper['Id']

        with tempfile.TemporaryDirectory(prefix='pw3-r47-') as tmp:
            qemu = Path(tmp) / 'qemu-arm-static'
            busybox = Path(tmp) / 'busybox'
            helper_cid = docker(['create', '--platform', 'linux/arm64', '--pull', 'never',
                                 '--network', 'none', '--name', 'pw3-r47-helper-' + uuid.uuid4().hex[:12],
                                 '--entrypoint', '/bin/true', HELPER]).stdout.strip()
            if not HEX_ID.fullmatch(helper_cid):
                raise Hold('HELPER_CID_INVALID')
            created.append(helper_cid)
            docker(['cp', '-L', helper_cid + ':/usr/bin/qemu-arm', str(qemu)])
            if sha256_file(qemu) != QEMU_SHA256 or elf_summary(qemu)['bits'] != 64 or elf_summary(qemu)['machine'] != 183:
                raise Hold('QEMU_BINARY_PIN_INVALID')
            r['qemu_binary_sha256'] = QEMU_SHA256

            prep_cid = docker(['create', '--platform', 'linux/arm/v7', '--pull', 'never',
                               '--network', 'none', '--name', 'pw3-r47-prep-' + uuid.uuid4().hex[:12],
                               '--entrypoint', '/bin/true', PARENT]).stdout.strip()
            if not HEX_ID.fullmatch(prep_cid):
                raise Hold('PREP_CID_INVALID')
            created.append(prep_cid)
            prep = inspect('container', prep_cid)
            if prep.get('Image') != PARENT_ID or (prep.get('State') or {}).get('Status') != 'created':
                raise Hold('PREP_NOT_STOPPED_OR_WRONG_IMAGE')
            docker(['cp', '-L', prep_cid + ':/bin/busybox', str(busybox)])
            if sha256_file(busybox) != BUSYBOX_SHA256 or elf_summary(busybox) != {
                    'bits': 32, 'machine': 40, 'e_flags': '0x05000400'}:
                raise Hold('BUSYBOX_BINARY_PIN_INVALID')
            r['busybox_sha256'] = BUSYBOX_SHA256
            r['busybox_elf'] = elf_summary(busybox)

            # Default read-only path. A failed copy is classified using actual
            # command stderr (hashed in report, not published raw).
            def execute_one(name, argv, readonly, already_created=None, copied=False):
                if already_created is None:
                    cid = docker(guest_create(argv, readonly)).stdout.strip()
                    if not HEX_ID.fullmatch(cid):
                        raise Hold('GUEST_CID_INVALID')
                    created.append(cid)
                    r['guest_containers_created'] += 1
                else:
                    cid = already_created
                validate_guest(inspect('container', cid), argv, readonly)
                if not copied:
                    cp = docker(['cp', str(qemu), cid + ':/usr/bin/qemu-arm-static'], allow_nonzero=True)
                    if cp.returncode != 0:
                        return (False, cid, classify_cp_error(cp))
                validate_guest(inspect('container', cid), argv, readonly)
                readback = Path(tmp) / ('readback-' + name + ('-ro' if readonly else '-rw'))
                docker(['cp','-L',cid+':/usr/bin/qemu-arm-static',str(readback)])
                if sha256_file(readback) != QEMU_SHA256:
                    raise Hold('GUEST_QEMU_READBACK_PIN_MISMATCH')
                if not readonly:
                    audit_diff(cid)
                # Every guest is still stopped until all policies/readback pass.
                started = docker(['start','--attach',cid], timeout=110, allow_nonzero=True)
                state = (inspect('container', cid).get('State') or {})
                if state.get('Status') != 'exited' or state.get('Running') is not False or state.get('OOMKilled') is not False:
                    raise Hold('GUEST_STOP_OR_OOM_UNVERIFIED:' + name)
                exit_code = state.get('ExitCode')
                if not isinstance(exit_code, int):
                    raise Hold('GUEST_EXIT_CODE_INVALID:' + name)
                r['authorized_qemu_execution_performed'] = True
                output = started.stdout + started.stderr
                success = probe_ok(name, exit_code, output)
                classification = help_diagnostic(name, exit_code, output) if name in HELP_PROBES else None
                accepted_known_help_anomaly = classification == 'KNOWN_BUSYBOX_APPLET_DISPATCH_ANOMALY'
                r['runtime_probes'][name] = {
                    'status': 'PASS' if success else ('DIAGNOSTIC_ANOMALY' if accepted_known_help_anomaly else 'HOLD'),
                    'exit_code': exit_code,
                    'output_sha256': hashlib.sha256(output.encode()).hexdigest(),
                    'output_prefix': output[:180] if name != 'busybox_true' else '',
                    'guest_argv_verified_by_inspect': True,
                }
                if classification:
                    r['runtime_probes'][name]['help_classification'] = classification
                    r['help_diagnostics'][name] = classification
                if not readonly:
                    r['runtime_probes'][name]['writable_diff'] = audit_diff(cid)
                if not success and not accepted_known_help_anomaly:
                    raise Hold('GUEST_PROBE_FAILED:' + name)
                if name == 'busybox_echo_marker':
                    # Tests were intentionally ordered: true, uname, echo must
                    # all pass before this flag can be asserted.
                    if not all(r['runtime_probes'].get(n, {}).get('status') == 'PASS'
                               for n in ('busybox_true', 'busybox_uname_machine', 'busybox_echo_marker')):
                        raise Hold('ARM32_APPLET_PROOF_INCOMPLETE')
                    r['positive_arm32_applets_verified'] = True
                return (True, cid, None)

            name, argv = PROBES[0]
            ro_result = execute_one(name, argv, readonly=True)
            if not ro_result[0]:
                r['read_only_copy_probe'] = ro_result[2]
                if ro_result[2]['classification'] != 'READONLY_ROOTFS_COPY_REJECTED':
                    raise Hold('READONLY_GUEST_COPY_FAILED_UNCLASSIFIED')
                if not allow_writable:
                    raise Hold('READONLY_COPY_REJECTED_WRITABLE_FALLBACK_NOT_AUTHORIZED')
                r['writable_fallback_used'] = True
                r['diagnostic'] = 'R3877_47_EXPLICIT_DISPOSABLE_WRITABLE_GUEST_ATTEMPTED'
                for name, argv in PROBES:
                    succeeded, _, failure = execute_one(name, argv, readonly=False)
                    if not succeeded:
                        r['writable_copy_error'] = failure
                        raise Hold('WRITABLE_GUEST_COPY_REJECTED')
            else:
                r['read_only_copy_probe'] = {'classification':'READONLY_COPY_ACCEPTED', 'exit_code':0}
                for name, argv in PROBES[1:]:
                    succeeded, _, failure = execute_one(name, argv, readonly=True)
                    if not succeeded:
                        r['read_only_copy_error'] = failure
                        raise Hold('READONLY_GUEST_COPY_REJECTED_LATER')
            if not r['positive_arm32_applets_verified']:
                raise Hold('ARM32_APPLET_PROOF_INCOMPLETE')
            a = r['help_diagnostics']
            if set(a) != HELP_PROBES:
                raise Hold('HELP_DIAGNOSTIC_INCOMPLETE')
            r['argv0_override_changes_help_result'] = a['busybox_default_help'] != a['busybox_forced_argv0_help']
            # Applets are the gate. Help is intentionally separate and retains
            # the observed abnormal outcome; it cannot counterfeit a help PASS.
            r['result'] = 'PASS_ARM32_BUSYBOX_APPLETS_QEMU_ONLY'
            r['diagnostic'] = 'R3877_47_QEMU_APPLET_PROBES_PASS_NOT_BOOTABLE'
    except (Hold, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        r['error_category'] = str(exc).splitlines()[0][:128]
    finally:
        for cid in reversed(created):
            try:
                cp = docker(['rm','-f',cid],timeout=35,allow_nonzero=True)
                if cp.returncode != 0:
                    cleanup_ok = False
                    continue
                check = docker(['container','inspect',cid],timeout=35,allow_nonzero=True)
                if check.returncode == 0 or not re.search('No such (?:container|object)',check.stderr,re.I):
                    cleanup_ok = False
            except Hold:
                cleanup_ok = False
        r['all_created_containers_removed'] = cleanup_ok and bool(created)
        if not cleanup_ok:
            r['container_ids_requiring_manual_review'] = created
        if parent_known:
            try:
                r['original_image_unchanged'] = image_info(PARENT)['Id'] == PARENT_ID
            except Hold:
                r['original_image_unchanged'] = False
        if r['result'].startswith('PASS') and (not r['all_created_containers_removed'] or not r['original_image_unchanged']):
            r['result'] = 'HOLD'
            r['error_category'] = 'CLEANUP_OR_PARENT_UNVERIFIED'
        if not r['all_created_containers_removed'] and not r['error_category']:
            r['error_category'] = 'CLEANUP_UNVERIFIED'
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--authorize-offline-qemu', action='store_true')
    ap.add_argument('--allow-disposable-writable-layer', action='store_true',
                    help='Additional opt-in: ONLY after read-only docker cp failure is confirmed')
    a = ap.parse_args(argv)
    if a.allow_disposable_writable_layer and not a.authorize_offline_qemu:
        r = preflight()
        r['error_category'] = 'WRITABLE_OPT_IN_REQUIRES_QEMU_AUTHORIZATION'
    else:
        r = run(a.allow_disposable_writable_layer) if a.authorize_offline_qemu else preflight()
    print(json.dumps(r,sort_keys=True,separators=(',',':')))
    return 0 if r['result'] == 'PASS_ARM32_BUSYBOX_APPLETS_QEMU_ONLY' else 2

if __name__ == '__main__':
    sys.exit(main())
