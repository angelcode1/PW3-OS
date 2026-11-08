#!/usr/bin/env python3
"""PW3-OS R3877.60: Mac/Colima QEMU *host* syscall ENOSYS injection gate.

Research/education only. NOT_BOOTABLE immutable. No Kindle or firmware access.
A pinned freestanding AArch64 launcher adds a restrictive seccomp-BPF filter
inside the Docker container AFTER Docker's own security filters are installed.
It directly verifies host getrandom/statx return ENOSYS, then execs pinned QEMU.
QEMU 10.0.4 may turn host statx ENOSYS into guest success using fstatat.
The QEMU *guest* results are accepted only if its trace shows corresponding
ENOSYS observations and independent untraced controls pass.

This is NOT the Kindle's running vendor kernel, an application fallback proof,
a host-kernel replacement, or confirmation of musl time64 fallback.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import struct
import sys
import tempfile
import uuid

import pw3_r3877_49_3_controlled_trace as base

MILESTONE='R3877.60.4'
PASS='PASS_QEMU_HOST_GETRANDOM_STATX_ENOSYS_WITH_GUEST_STATX_EMULATION_ONLY'
BASE_SHA='5fa8ae5a386d32427ee67e068af55d4dd23a9e61b312357b00d9c0ed6d6ad659'
LAUNCHER_SHA='b9a433e2397e27c4cbdd2aade7b57cc39af4e6f36b37a4f204833b282a987b02'
ARM_SHA='b0b89626cd48482e99ea8515b4c808c378e1ff65b4ea4de05b16a4c373df18f4'
LAUNCHER=Path(__file__).resolve().parent/'pw3_r3877_60_4_aarch64_seccomp_selftest.elf'
ARM=Path(__file__).resolve().parent/'pw3_r3877_59_2_armv7_probe.elf'
GUEST_LAUNCHER='/usr/bin/pw3-r3877-60-filter'
GUEST_QEMU='/usr/bin/qemu-arm-static'
GUEST_ARM='/usr/bin/pw3-r3877-59-armv7-probe'
FILTER_MARKER=('R604_HOST_FILTER_INSTALLED\n'
               'R604_HOST_GETRANDOM_ENOSYS_VERIFIED\n'
               'R604_HOST_STATX_ENOSYS_VERIFIED\n')
ARM_EXPECTED=('R59_PASS_ARMV7_PTHREAD_TLS\n'
              'R59_OBS_GETRANDOM_ENOSYS\n'
              'R59_PASS_QEMU_ARMV7_MUSL_PROBE_ONLY\n')
PROBES=(
 ('arm_control', (GUEST_ARM,)),
 ('stat_control', ('/bin/busybox','stat','-c','%s','/bin/busybox')),
 ('arm_trace', ('-strace',GUEST_ARM)),
 ('stat_trace', ('-strace','/bin/busybox','stat','-c','%s','/bin/busybox')),
)
TRACE_PAIRS={'arm_trace':'arm_control','stat_trace':'stat_control'}
READONLY_RE=base.READONLY_RE
FILTERED_NAMES={'getrandom','statx'}
PINNED_ARCH_ARM64=183
PINNED_ARCH_ARM=40

class Hold(Exception): pass


def bounded_digest(path,lim=131072):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or not 1 <= p.stat().st_size <= lim:
        raise Hold('PINNED_LOCAL_FILE_MISSING_OR_UNSAFE')
    return hashlib.sha256(p.read_bytes()).hexdigest()


def require_executable_mode(path, role):
    """Require launchable, non-world-writable ELF mode, not just identical bytes.

    Docker cp propagates executable mode from the local file. R60.2 was
    shipped with 0644 files despite a byte-identical launcher. This could
    prevent Docker startup; the exact cause of R60.2's HOLD is unconfirmed.
    """
    if role not in ('launcher','qemu','arm_probe'):
        raise Hold('EXECUTABLE_ROLE_INVALID')
    p=Path(path)
    if p.is_symlink() or not p.is_file():
        raise Hold('EXECUTABLE_FILE_UNSAFE:'+role)
    mode=stat.S_IMODE(p.stat().st_mode)
    if (mode & 0o111) != 0o111 or (mode & 0o022):
        raise Hold('EXECUTABLE_MODE_UNVERIFIED:'+role)
    return True


def classify_start_result(name, start_result, state):
    """Safe, bounded exit-state diagnostics, no raw stdout/stderr or paths."""
    if name not in {x for x, _ in PROBES}:
        raise Hold('GUEST_PROBE_NAME_UNKNOWN')
    if not isinstance(state,dict):
        raise Hold('DOCKER_GUEST_STATE_NOT_OBJECT')
    raw=(start_result.stdout+start_result.stderr).encode('utf-8',errors='replace')
    lower=(start_result.stdout+start_result.stderr).lower()
    if 'permission denied' in lower:
        hint='DOCKER_START_PERMISSION_DENIED'
    elif 'exec format error' in lower:
        hint='DOCKER_START_EXEC_FORMAT_ERROR'
    elif 'no such file or directory' in lower:
        hint='DOCKER_START_MISSING_FILE_OR_INTERPRETER'
    elif 'operation not permitted' in lower:
        hint='DOCKER_START_OPERATION_NOT_PERMITTED'
    elif start_result.returncode != 0:
        hint='DOCKER_START_FAILED_UNCLASSIFIED'
    else:
        hint='NO_CLASSIFIED_DOCKER_START_ERROR'
    status=state.get('Status')
    return {'docker_start_exit_code':start_result.returncode,
            'docker_start_combined_output_sha256':hashlib.sha256(raw).hexdigest(),
            'docker_start_combined_output_bytes':len(raw),
            'docker_start_error_classification':hint,
            'state_status':status if status in ('created','running','exited','dead','paused','restarting','removing') else 'UNKNOWN',
            'state_running':state.get('Running') if isinstance(state.get('Running'),bool) else None,
            'state_oomkilled':state.get('OOMKilled') if isinstance(state.get('OOMKilled'),bool) else None,
            'state_exit_code':state.get('ExitCode') if type(state.get('ExitCode')) is int else None,
            'state_error_present':bool(state.get('Error')),
            'raw_output_published':False}


def verify_pins():
    if bounded_digest(base.__file__,100000)!=BASE_SHA:
        raise Hold('BASE_R49_BYTES_MISMATCH')
    if bounded_digest(LAUNCHER,16384)!=LAUNCHER_SHA:
        raise Hold('PINNED_AARCH64_FILTER_BYTES_MISMATCH')
    if bounded_digest(ARM,16384)!=ARM_SHA:
        raise Hold('PINNED_ARMV7_PROBE_BYTES_MISMATCH')
    require_executable_mode(LAUNCHER,'launcher')
    require_executable_mode(ARM,'arm_probe')
    l=LAUNCHER.read_bytes(); b=ARM.read_bytes()
    if not (l[:7]==b'\x7fELF\x02\x01\x01' and
            struct.unpack_from('<H',l,18)[0]==PINNED_ARCH_ARM64 and
            struct.unpack_from('<H',l,16)[0]==2):
        raise Hold('FILTER_ELF_NOT_AARCH64_STATIC_EXEC')
    if not (b[:7]==b'\x7fELF\x01\x01\x01' and
            struct.unpack_from('<H',b,18)[0]==PINNED_ARCH_ARM and
            struct.unpack_from('<I',b,36)[0]==0x05000400):
        raise Hold('PROBE_ELF_NOT_ARMV7_HARDFLOAT')
    if base.PARENT_ID!='sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a' or base.QEMU_SHA256!='3347b95a4006c1eb19b93ba09469a2c42b04fe5d89a430ce96cbf2a2367cf5c1':
        raise Hold('PINNED_IMAGE_OR_QEMU_CONSTANT_CHANGED')
    return True


def preflight():
    return {'milestone':MILESTONE,'result':'HOLD','hold_category':'OFFLINE_QEMU_AUTHORIZATION_REQUIRED',
        'immutable_hold':'NOT_BOOTABLE','docker_used':False,'host_seccomp_injection_performed':False,
        'arm_guest_execution_performed':False,'kindle_ssh_sessions':0,'physical_device_access_performed':False,
        'boot_performed':False,'firmware_write_performed':False,'recovery_verified':False,
        'actual_vendor_kernel_compatibility_verified':False,'runtime_musl_getentropy_enosys_fallback_verified':False,
        'target_kernel_getrandom_availability_verified':False,'target_kernel_statx_availability_verified':False,
        'target_musl_time64_fallback_verified':False,'original_patched_musl_binary_reproducibility_verified':False,
        'host_getrandom_enosys_direct_verified':False, 'host_statx_enosys_direct_verified':False,
        'qemu_guest_statx_enosys_observed':False,
        'qemu_uses_colima_host_kernel':True,'guest_network_enabled':False,'host_mounts_enabled':False,
        'host_binfmt_registration_changed':False}


def sanitized_error(cp):
    combined=cp.stdout+cp.stderr
    return {'exit_code':cp.returncode,'bytes':len(combined.encode()),
            'sha256':hashlib.sha256(combined.encode()).hexdigest(),
            'classification':('READONLY_COPY_REJECTED' if cp.returncode!=0 and READONLY_RE.search(combined)
                              else 'COPY_FAILURE_UNCLASSIFIED'),
            'raw_error_published':False}


def create_guest(guest_argv,readonly):
    argv=['create','--platform','linux/arm/v7','--pull','never','--network','none']
    if readonly:argv.append('--read-only')
    argv.extend(['--pids-limit','64','--memory','256m','--cap-drop','ALL',
                 '--security-opt','no-new-privileges','--user','65534:65534',
                 '--name','pw3-r60-'+uuid.uuid4().hex[:12],
                 '--entrypoint',GUEST_LAUNCHER,base.PARENT,GUEST_QEMU,*guest_argv])
    return argv


def validate_guest(js,guest_argv,readonly):
    st=js.get('State') or {};hc=js.get('HostConfig') or {}; cfg=js.get('Config') or {}
    if js.get('Image')!=base.PARENT_ID or st.get('Status')!='created' or st.get('Running') is not False:
        raise Hold('GUEST_STOPPED_PARENT_MISMATCH')
    if js.get('Path')!=GUEST_LAUNCHER or js.get('Args')!=[GUEST_QEMU,*guest_argv]:
        raise Hold('GUEST_ENTRYPOINT_OR_ARGS_CHANGED')
    if cfg.get('User')!='65534:65534' or cfg.get('Entrypoint')!=[GUEST_LAUNCHER]:
        raise Hold('GUEST_UNPRIVILEGED_ENTRYPOINT_MISMATCH')
    if hc.get('ReadonlyRootfs') is not readonly or hc.get('NetworkMode')!='none' or hc.get('Privileged') is not False:
        raise Hold('GUEST_READONLY_NETWORK_OR_PRIVILEGE_MISMATCH')
    if hc.get('Binds') not in (None,[]) or js.get('Mounts') not in (None,[]) or hc.get('Devices') not in (None,[]) or hc.get('DeviceRequests') not in (None,[]):
        raise Hold('GUEST_MOUNTS_OR_DEVICES_PRESENT')
    if 'ALL' not in [str(x).upper() for x in hc.get('CapDrop') or []]:
        raise Hold('GUEST_CAPABILITIES_NOT_DROPPED')
    secopt=hc.get('SecurityOpt') or []
    if 'no-new-privileges' not in secopt or any('seccomp' in str(x) for x in secopt):
        raise Hold('GUEST_SECCOMP_DEFAULT_REPLACED_OR_NNP_MISSING')
    if hc.get('PidsLimit')!=64 or hc.get('Memory')!=268435456:
        raise Hold('GUEST_RESOURCES_MISMATCH')
    return True



AUX_IDENTITY='65534:65534'
AUX_MEMORY=134217728
AUX_PIDS=32


def auxiliary_create(image, name, platform):
    """Create a stopped-only, read-only and explicitly unprivileged source guest."""
    return ['create','--platform',platform,'--pull','never',
        '--network','none','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--user',AUX_IDENTITY,
        '--pids-limit',str(AUX_PIDS),'--memory','128m',
        '--name',name,'--entrypoint','/bin/true',image]


def declared_volume_destinations(image_info):
    """Get only the pinned image's explicit VOLUME declarations; fail closed."""
    if not isinstance(image_info, dict) or not isinstance(image_info.get('Config'), dict):
        raise Hold('IMAGE_CONFIG_VOLUMES_UNVERIFIED')
    raw = image_info['Config'].get('Volumes')
    if raw is None:
        return set()
    if not isinstance(raw, dict) or len(raw) > 16:
        raise Hold('IMAGE_CONFIG_VOLUMES_INVALID')
    names = set()
    for dest in raw:
        if not isinstance(dest, str) or not dest.startswith('/') or dest == '/' or            '//' in dest or '/./' in dest or '/..' in dest or '\\' in dest or not re.fullmatch(r'/[a-zA-Z0-9_./-]{1,180}', dest):
            raise Hold('IMAGE_VOLUME_DESTINATION_UNSAFE')
        names.add(dest.rstrip('/'))
    if len(names) != len(raw):
        raise Hold('IMAGE_VOLUME_DUPLICATE_NORMALIZED_DEST')
    return names


def image_declared_anonymous_volumes(info, image_info, protected_executable):
    """Prove no operator host mounts; only allow matching Docker-created local volumes.

    The image is separately pinned by SHA-256 and was never started. Docker
    creates anonymous volumes for image VOLUME declarations at create time.
    No bind mounts, named volumes, or overriding volume flags are accepted.
    """
    mounts = info.get('Mounts')
    if mounts in (None, []):
        return {'verified':True, 'mounts_absent':True,
                'anonymous_image_volume_count':0,'anonymous_volume_names':[],
                'reason':'NO_MOUNTS'}
    if not isinstance(mounts, list) or len(mounts)>16:
        return {'verified':False,'mounts_absent':False,
                'anonymous_image_volume_count':0,'anonymous_volume_names':[],
                'reason':'MOUNT_LIST_INVALID'}
    try:
        declared=declared_volume_destinations(image_info)
    except Hold:
        return {'verified':False,'mounts_absent':False,
                'anonymous_image_volume_count':0,'anonymous_volume_names':[],
                'reason':'IMAGE_VOLUME_DECLARATIONS_UNVERIFIED'}
    host=info.get('HostConfig') or {}
    if not isinstance(host,dict) or host.get('Binds') not in (None,[]) or        host.get('Mounts') not in (None,[]) or host.get('VolumesFrom') not in (None,[]) or        host.get('Tmpfs') not in (None,{}):
        return {'verified':False,'mounts_absent':False,
                'anonymous_image_volume_count':0,'anonymous_volume_names':[],
                'reason':'EXPLICIT_MOUNT_CONFIGURATION_PRESENT'}
    if not declared or len(declared)!=len(mounts):
        return {'verified':False,'mounts_absent':False,
                'anonymous_image_volume_count':0,'anonymous_volume_names':[],
                'reason':'MOUNT_NOT_ONE_TO_ONE_WITH_IMAGE_VOLUMES'}
    names=[];found=set()
    for m in mounts:
        if not isinstance(m,dict):
            return {'verified':False,'mounts_absent':False,'anonymous_image_volume_count':0,
                    'anonymous_volume_names':[],'reason':'MOUNT_ENTRY_INVALID'}
        name=m.get('Name');dest=m.get('Destination');source=m.get('Source')
        if m.get('Type')!='volume' or m.get('Driver')!='local':
            return {'verified':False,'mounts_absent':False,'anonymous_image_volume_count':0,
                    'anonymous_volume_names':[],'reason':'NONLOCAL_VOLUME_OR_HOST_BIND'}
        if not isinstance(name,str) or not re.fullmatch(r'[0-9a-f]{64}',name):
            return {'verified':False,'mounts_absent':False,'anonymous_image_volume_count':0,
                    'anonymous_volume_names':[],'reason':'NAMED_OR_INVALID_VOLUME'}
        if dest not in declared or dest in found:
            return {'verified':False,'mounts_absent':False,'anonymous_image_volume_count':0,
                    'anonymous_volume_names':[],'reason':'VOLUME_DESTINATION_NOT_DECLARED'}
        if not isinstance(source,str) or not source.endswith('/volumes/'+name+'/_data'):
            return {'verified':False,'mounts_absent':False,'anonymous_image_volume_count':0,
                    'anonymous_volume_names':[],'reason':'VOLUME_SOURCE_NOT_DOCKER_MANAGED'}
        if m.get('Mode') not in ('', None):
            return {'verified':False,'mounts_absent':False,'anonymous_image_volume_count':0,
                    'anonymous_volume_names':[],'reason':'VOLUME_MODE_UNEXPECTED'}
        if not isinstance(m.get('RW'),bool):
            return {'verified':False,'mounts_absent':False,'anonymous_image_volume_count':0,
                    'anonymous_volume_names':[],'reason':'VOLUME_RW_METADATA_UNVERIFIED'}
        # An image VOLUME may obscure executable bytes; do not allow it to
        # overlap the source-file path or the path's ancestor directories.
        protected=protected_executable.rstrip('/')
        if protected==dest or protected.startswith(dest.rstrip('/')+'/'):
            return {'verified':False,'mounts_absent':False,'anonymous_image_volume_count':0,
                    'anonymous_volume_names':[],'reason':'VOLUME_OBSCURES_PINNED_EXECUTABLE'}
        names.append(name);found.add(dest)
    if found!=declared or len(set(names))!=len(names):
        return {'verified':False,'mounts_absent':False,'anonymous_image_volume_count':0,
                'anonymous_volume_names':[],'reason':'VOLUME_SET_INCONSISTENT'}
    return {'verified':True,'mounts_absent':False,
            'anonymous_image_volume_count':len(names),
            'anonymous_volume_names':names,'reason':'IMAGE_DECLARED_ANONYMOUS_LOCAL_VOLUMES'}


def auxiliary_attestation(info, expected_image_id, image_info=None, protected_executable=None):
    """Sanitized isolation evidence, with strict, transparent volume classification."""
    if not isinstance(info,dict):
        raise Hold('AUXILIARY_CONTAINER_INSPECT_INVALID')
    state=info.get('State') if isinstance(info.get('State'),dict) else {}
    host=info.get('HostConfig') if isinstance(info.get('HostConfig'),dict) else {}
    config=info.get('Config') if isinstance(info.get('Config'),dict) else {}
    opts=host.get('SecurityOpt')
    opts=opts if isinstance(opts,list) else []
    caps=host.get('CapDrop')
    caps=caps if isinstance(caps,list) else []
    volume = image_declared_anonymous_volumes(info,image_info,protected_executable) if         image_info is not None and protected_executable else         {'verified':info.get('Mounts') in (None,[]),
         'mounts_absent':info.get('Mounts') in (None,[]),
         'anonymous_image_volume_count':0,'anonymous_volume_names':[],
         'reason':'NO_MOUNTS' if info.get('Mounts') in (None,[]) else 'IMAGE_VOLUME_POLICY_MISSING'}
    checks={
        'image_id_matches_pin': info.get('Image')==expected_image_id,
        'status_is_created': state.get('Status')=='created',
        'running_is_false': state.get('Running') is False,
        'entrypoint_is_bin_true': info.get('Path')=='/bin/true' and config.get('Entrypoint')==['/bin/true'],
        'user_is_unprivileged': config.get('User')==AUX_IDENTITY,
        'network_is_none': host.get('NetworkMode')=='none',
        'privileged_is_false': host.get('Privileged') is False,
        'rootfs_is_readonly': host.get('ReadonlyRootfs') is True,
        'binds_absent': host.get('Binds') in (None,[]),
        'mounts_satisfy_strict_anonymous_image_volume_policy':volume['verified'],
        'devices_absent': host.get('Devices') in (None,[]),
        'device_requests_absent': host.get('DeviceRequests') in (None,[]),
        'all_capabilities_dropped': 'ALL' in [str(x).upper() for x in caps],
        'no_new_privileges': 'no-new-privileges' in opts,
        'default_seccomp_not_overridden': not any('seccomp' in str(x).lower() for x in opts),
        'pids_limit_32': host.get('PidsLimit')==AUX_PIDS,
        'memory_limit_128m': host.get('Memory')==AUX_MEMORY,
    }
    failed=sorted(k for k,v in checks.items() if v is not True)
    # Never publish raw paths, volume names, IDs, or inspect responses.
    return {'all_verified':not failed, 'checks':checks,'failed_checks':failed,
            'mounts_absent':volume['mounts_absent'],
            'anonymous_image_declared_volume_count':volume['anonymous_image_volume_count'],
            'mount_classification':volume['reason'],
            'raw_inspect_metadata_published':False}


def require_auxiliary_attestation(report, label, data, expected_id, image_info=None,
                                  protected_executable=None):
    if label not in ('helper','preparation'):
        raise Hold('AUXILIARY_LABEL_INVALID')
    att=auxiliary_attestation(data,expected_id,image_info,protected_executable)
    report['auxiliary_container_isolation'][label]=att
    if not att['all_verified']:
        raise Hold(('HELPER' if label=='helper' else 'PREPARATION') + '_CONTAINER_ISOLATION_UNVERIFIED')
    return True


def extract_filter_marker(stdout,stderr):
    # Filter output is never reused as proof of application behavior.
    combined=stdout+stderr
    if combined.count(FILTER_MARKER)!=1:
        raise Hold('HOST_SECCOMP_FILTER_INSTALLATION_MARKER_MISSING_OR_DUPLICATE')
    return combined.replace(FILTER_MARKER,'',1)


def direct_control_ok(name,rc,out,expected_busybox_size):
    if rc!=0:return False
    if name=='arm_control':return out==ARM_EXPECTED
    if name=='stat_control':return out==str(expected_busybox_size)+'\n'
    return False


def parse_trace(name,stdout,stderr):
    # Treat opaque lines as unattributed; never put raw QEMU addresses/args in JSON.
    output=extract_filter_marker(stdout,stderr)
    t=base.parse_qemu_trace(output,'')
    target='getrandom' if name=='arm_trace' else 'statx'
    hits=[]
    for ln in output.splitlines():
        m=base.SYSCALL_LINE.match(ln)
        if m and m.group(1)==target:
            hits.append({'enosys':bool(base.ENOSYS_TEXT.search(ln))})
    return {
      'target_guest_syscall_name':target,
      'target_guest_call_count':len(hits),
      'target_guest_enosys_count':sum(1 for h in hits if h['enosys']),
      'syscall_record_count':t['syscall_record_count'],
      'trace_unknown_record_count':t['trace_unknown_record_count'],
      'trace_unclassified_line_count':t['unclassified_line_count'],
      'trace_output_attribution':'UNVERIFIED_IF_ANY_UNCLASSIFIED_LINES',
      'trace_guest_syscall_names':t['syscall_names'],
      'raw_trace_published':False,
    }


def audit_diff(cid):
    lines=base.docker(['diff',cid]).stdout.splitlines()
    paths={GUEST_LAUNCHER,GUEST_QEMU,GUEST_ARM}
    allowed={kind+' '+p for kind in ('A','C') for p in paths}|{'C /usr','C /usr/bin'}
    if any(x.strip() not in allowed for x in lines if x.strip()):
        raise Hold('GUEST_WRITABLE_DIFF_UNEXPECTED')
    if not all(any(x.endswith(' '+p) for x in lines) for p in paths):
        raise Hold('GUEST_WRITABLE_DIFF_REQUIRED_INJECTED_FILES_MISSING')
    return {'only_three_pinned_injected_files_plus_ancestors':True,
            'reported_changes_count':len(lines)}


def run(allow_writable=False):
    r=preflight();r.update(docker_used=True,offline_qemu_authorized=True,
        disposable_writable_layer_additional_opt_in=bool(allow_writable),
        original_image_unchanged=False,all_created_containers_removed=False,
        expected_error_injection={'host_getrandom_enosys':True,'host_statx_enosys':True},
        runtime_probes={},auxiliary_container_isolation={},guest_start_diagnostics={},
        launcher_execute_mode_verified=False)
    created=[];parent_known=False;cleanup_ok=True
    anonymous_volumes_to_verify=[];volume_cleanup_verified=True
    try:
        verify_pins()
        r['launcher_execute_mode_verified']=True
        j=json.loads(base.docker(['version','--format','{{json .Server}}']).stdout)
        if not isinstance(j,dict) or str(j.get('Arch',j.get('Architecture',''))).lower() not in ('arm64','aarch64'):
            raise Hold('DOCKER_SERVER_NOT_ARM64')
        sec=json.loads(base.docker(['info','--format','{{json .SecurityOptions}}']).stdout)
        if not isinstance(sec,list) or not any('seccomp' in str(x).lower() and 'profile=builtin' in str(x).lower() for x in sec):
            raise Hold('DOCKER_BUILTIN_SECCOMP_DEFAULT_NOT_ATTESTED')
        r['docker_builtin_seccomp_profile_attested']=True
        parent=base.image_info(base.PARENT)
        if parent.get('Id')!=base.PARENT_ID or parent.get('Architecture')!='arm' or parent.get('Os')!='linux' or parent.get('Variant') not in ('v7','7'):
            raise Hold('PARENT_IMAGE_ID_OR_PLATFORM_MISMATCH')
        parent_known=True
        helper=base.image_info(base.HELPER)
        if helper.get('RepoDigests') is None or base.HELPER_DIGEST not in helper['RepoDigests'] or helper.get('Architecture') not in ('arm64','aarch64'):
            raise Hold('PINNED_QEMU_HELPER_IMAGE_MISMATCH')
        with tempfile.TemporaryDirectory(prefix='pw3-r60-') as tmp:
            qemu=Path(tmp)/'qemu-arm-static'
            busybox=Path(tmp)/'busybox'
            helper_cid=base.docker(auxiliary_create(base.HELPER,
                'pw3-r601-helper-'+uuid.uuid4().hex[:12],'linux/arm64')).stdout.strip()
            if not base.HEX_ID.fullmatch(helper_cid):raise Hold('HELPER_CONTAINER_ID_INVALID')
            created.append(helper_cid)
            helper_info=base.inspect('container',helper_cid)
            require_auxiliary_attestation(r,'helper',helper_info,helper['Id'],helper,'/usr/bin/qemu-arm')
            hp=image_declared_anonymous_volumes(helper_info,helper,'/usr/bin/qemu-arm')
            anonymous_volumes_to_verify.extend(hp['anonymous_volume_names'])
            base.docker(['cp','-L',helper_cid+':/usr/bin/qemu-arm',str(qemu)])
            if bounded_digest(qemu,40*1024*1024)!=base.QEMU_SHA256 or base.elf_summary(qemu)['bits']!=64 or base.elf_summary(qemu)['machine']!=183:
                raise Hold('QEMU_EXECUTABLE_IDENTITY_MISMATCH')
            require_executable_mode(qemu,'qemu')
            prep_cid=base.docker(auxiliary_create(base.PARENT,
                'pw3-r601-prep-'+uuid.uuid4().hex[:12],'linux/arm/v7')).stdout.strip()
            if not base.HEX_ID.fullmatch(prep_cid):raise Hold('PREP_CONTAINER_ID_INVALID')
            created.append(prep_cid)
            prep_info=base.inspect('container',prep_cid)
            require_auxiliary_attestation(r,'preparation',prep_info,base.PARENT_ID,parent,'/bin/busybox')
            pp=image_declared_anonymous_volumes(prep_info,parent,'/bin/busybox')
            anonymous_volumes_to_verify.extend(pp['anonymous_volume_names'])
            base.docker(['cp','-L',prep_cid+':/bin/busybox',str(busybox)])
            if bounded_digest(busybox,30*1024*1024)!=base.BUSYBOX_SHA256:
                raise Hold('BUSYBOX_IDENTITY_MISMATCH')
            expected_busybox_size=busybox.stat().st_size

            def execute_one(name,guest_argv,readonly):
                cid=base.docker(create_guest(guest_argv,readonly)).stdout.strip()
                if not base.HEX_ID.fullmatch(cid):raise Hold('GUEST_CONTAINER_ID_INVALID')
                created.append(cid)
                validate_guest(base.inspect('container',cid),guest_argv,readonly)
                first=base.docker(['cp',str(LAUNCHER),cid+':'+GUEST_LAUNCHER],allow_nonzero=True)
                if first.returncode!=0:
                    return (False,sanitized_error(first))
                for local,remote,sha in ((qemu,GUEST_QEMU,base.QEMU_SHA256),(ARM,GUEST_ARM,ARM_SHA)):
                    base.docker(['cp',str(local),cid+':'+remote])
                    readback=Path(tmp)/('readback-'+name+'-'+remote.rsplit('/',1)[-1])
                    base.docker(['cp','-L',cid+':'+remote,str(readback)])
                    if bounded_digest(readback,40*1024*1024)!=sha:
                        raise Hold('INJECTED_EXECUTABLE_READBACK_MISMATCH')
                    require_executable_mode(readback,'qemu' if remote==GUEST_QEMU else 'arm_probe')
                    validate_guest(base.inspect('container',cid),guest_argv,readonly)
                readback=Path(tmp)/('readback-'+name+'-launcher')
                base.docker(['cp','-L',cid+':'+GUEST_LAUNCHER,str(readback)])
                if bounded_digest(readback,16384)!=LAUNCHER_SHA:raise Hold('SECCOMP_LAUNCHER_READBACK_MISMATCH')
                require_executable_mode(readback,'launcher')
                if not readonly:audit_diff(cid)
                before=base.inspect('container',cid)
                validate_guest(before,guest_argv,readonly)
                cp=base.docker(['start','--attach',cid],timeout=110,allow_nonzero=True)
                state=(base.inspect('container',cid).get('State') or {})
                r.setdefault('guest_start_diagnostics',{})[name]=classify_start_result(name,cp,state)
                if state.get('Status')!='exited' or state.get('Running') is not False or state.get('OOMKilled') is not False:
                    raise Hold('GUEST_EXIT_OOM_STATE_UNVERIFIED:'+name)
                if not isinstance(state.get('ExitCode'),int):raise Hold('GUEST_EXIT_CODE_MISSING:'+name)
                rc=state['ExitCode']
                r['arm_guest_execution_performed']=True
                sanitized=extract_filter_marker(cp.stdout,cp.stderr)
                r['host_seccomp_injection_performed']=True
                record={'guest_exit_code':rc,'host_filter_installed_marker_present':True,
                        'host_filter_getrandom_enosys_selftest_marker_present':True,
                        'host_filter_statx_enosys_selftest_marker_present':True,
                        'raw_guest_output_published':False,
                        'combined_output_sha256':hashlib.sha256((cp.stdout+cp.stderr).encode()).hexdigest()}
                if name in TRACE_PAIRS:
                    t=parse_trace(name,cp.stdout,cp.stderr)
                    record.update(trace=t)
                    ctrl=r['runtime_probes'].get(TRACE_PAIRS[name],{})
                    if ctrl.get('untraced_control_status')!='PASS':
                        raise Hold('INDEPENDENT_UNTRACED_CONTROL_MISSING:'+name)
                    if rc!=0 or t['syscall_record_count']<1:
                        raise Hold('GUEST_TRACE_FAILED:'+name)
                    record['trace_status']='OBSERVED'
                else:
                    passed=direct_control_ok(name,rc,sanitized,expected_busybox_size)
                    record['untraced_control_status']='PASS' if passed else 'HOLD'
                    record['expected_output_exact_match']=passed
                r['runtime_probes'][name]=record
                if not readonly:audit_diff(cid)
                if name not in TRACE_PAIRS and not passed:raise Hold('GUEST_CONTROL_FAILED:'+name)
                return (True,None)

            # First deliberate read-only copy gate. Writable retry is only
            # authorized after a positively classified read-only EROFS refusal.
            name,argv=PROBES[0]
            success,err=execute_one(name,argv,readonly=True)
            if not success:
                r['readonly_copy_probe']=err
                if err['classification']!='READONLY_COPY_REJECTED':
                    raise Hold('READONLY_COPY_FAILED_UNCLASSIFIED')
                if not allow_writable:
                    raise Hold('READONLY_COPY_REJECTED_WRITABLE_LAYER_NOT_AUTHORIZED')
                r['writable_fallback_used']=True
                for name,argv in PROBES:
                    success,err=execute_one(name,argv,readonly=False)
                    if not success:raise Hold('WRITABLE_COPY_REJECTED')
            else:
                r['readonly_copy_probe']={'classification':'READONLY_COPY_SUCCEEDED','exit_code':0}
                r['writable_fallback_used']=False
                for name,argv in PROBES[1:]:
                    success,err=execute_one(name,argv,readonly=True)
                    if not success:raise Hold('LATER_READONLY_COPY_REJECTED')
            if set(r['runtime_probes'])!={n for n,_ in PROBES}:
                raise Hold('PROBE_SET_INCOMPLETE')
            # Host ENOSYS is directly attested by the launcher before QEMU.
            # QEMU v10.0.4 translates host statx ENOSYS to fstatat rather
            # than forwarding guest ENOSYS (pinned syscall.c source).
            for name in TRACE_PAIRS:
                t=r['runtime_probes'][name]['trace']
                if t['target_guest_call_count']!=1:
                    raise Hold('TARGETED_GUEST_SYSCALL_COUNT_UNEXPECTED:'+name)
                wanted=1 if name=='arm_trace' else 0
                if t['target_guest_enosys_count']!=wanted:
                    raise Hold('TARGETED_GUEST_RETURN_MISMATCH:'+name)
            r.update(result=PASS,hold_category='NOT_BOOTABLE',host_seccomp_injection_performed=True,
                host_getrandom_enosys_direct_verified=True,
                host_statx_enosys_direct_verified=True,
                qemu_pthread_tls_with_guest_getrandom_enosys_control_verified=True,
                qemu_guest_statx_success_consistent_with_qemu_internal_fstatat_fallback=True,
                qemu_guest_statx_enosys_observed=False,
                vendor_kernel_syscall_dispatch_verified=False)
    except (Hold,base.Hold,ValueError,TypeError,KeyError,OSError,UnicodeError) as exc:
        r.update(result='HOLD',hold_category=str(exc).splitlines()[0][:150])
    finally:
        for cid in reversed(created):
            try:
                rm=base.docker(['rm','-f','-v',cid],timeout=35,allow_nonzero=True)
                check=base.docker(['container','inspect',cid],timeout=35,allow_nonzero=True)
                if rm.returncode!=0 or check.returncode==0 or not re.search(r'No such (?:container|object)',check.stderr,re.I):
                    cleanup_ok=False
            except base.Hold:cleanup_ok=False
        for name in sorted(set(anonymous_volumes_to_verify)):
            try:
                v=base.docker(['volume','inspect',name],timeout=35,allow_nonzero=True)
                if v.returncode==0 or not re.search(r'No such volume',v.stderr,re.I):
                    volume_cleanup_verified=False
            except base.Hold:
                volume_cleanup_verified=False
        unclassified_mounts=any(
            x.get('mounts_absent') is False and x.get('all_verified') is False
            for x in r['auxiliary_container_isolation'].values()
            if isinstance(x,dict))
        if unclassified_mounts:
            # No volume name can safely be considered owned by this run.
            # We removed the stopped container with -v, but do not claim
            # anonymous-volume cleanup of unclassified mounts.
            volume_cleanup_verified=False
        r['image_declared_anonymous_volume_count']=len(set(anonymous_volumes_to_verify))
        r['anonymous_volume_cleanup_verified']=volume_cleanup_verified
        r['unclassified_mounts_require_manual_review']=unclassified_mounts
        r['all_created_containers_removed']=cleanup_ok and bool(created)
        if not cleanup_ok:r['container_cleanup_requires_review']=True
        if parent_known:
            try:r['original_image_unchanged']=base.image_info(base.PARENT)['Id']==base.PARENT_ID
            except base.Hold:r['original_image_unchanged']=False
        if r['result']==PASS and not (r['all_created_containers_removed'] and r['anonymous_volume_cleanup_verified'] and r.get('original_image_unchanged')):
            r.update(result='HOLD',hold_category='CLEANUP_OR_PINNED_PARENT_UNVERIFIED')
    return r


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--authorize-offline-qemu',action='store_true')
    p.add_argument('--allow-disposable-writable-layer',action='store_true')
    a=p.parse_args(argv)
    if a.allow_disposable_writable_layer and not a.authorize_offline_qemu:
        r=preflight();r['hold_category']='WRITABLE_OPT_IN_REQUIRES_OFFLINE_QEMU_AUTHORIZATION'
    else:r=run(a.allow_disposable_writable_layer) if a.authorize_offline_qemu else preflight()
    print(json.dumps(r,sort_keys=True,separators=(',',':')))
    return 0 if r['result']==PASS else 2

if __name__=='__main__':sys.exit(main())
