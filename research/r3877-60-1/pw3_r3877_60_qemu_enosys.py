#!/usr/bin/env python3
"""PW3-OS R3877.60: Mac/Colima QEMU *host* syscall ENOSYS injection gate.

Research/education only. NOT_BOOTABLE immutable. No Kindle or firmware access.
A pinned freestanding AArch64 launcher adds a restrictive seccomp-BPF filter
inside the Docker container AFTER Docker's own security filters are installed.
It denies HOST getrandom/statx with errno=ENOSYS and then execs pinned QEMU.
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
import struct
import sys
import tempfile
import uuid

import pw3_r3877_49_3_controlled_trace as base

MILESTONE='R3877.60'
PASS='PASS_QEMU_ARMV7_HOST_SECCOMP_GETRANDOM_STATX_ENOSYS_ONLY'
BASE_SHA='5fa8ae5a386d32427ee67e068af55d4dd23a9e61b312357b00d9c0ed6d6ad659'
LAUNCHER_SHA='66252ad8f424e8b902e8bb7c68021f9b367d962b02b926a818fda18af3fe49a4'
ARM_SHA='b0b89626cd48482e99ea8515b4c808c378e1ff65b4ea4de05b16a4c373df18f4'
LAUNCHER=Path(__file__).resolve().parent/'pw3_r3877_60_aarch64_seccomp_launcher.elf'
ARM=Path(__file__).resolve().parent/'pw3_r3877_59_2_armv7_probe.elf'
GUEST_LAUNCHER='/usr/bin/pw3-r3877-60-filter'
GUEST_QEMU='/usr/bin/qemu-arm-static'
GUEST_ARM='/usr/bin/pw3-r3877-59-armv7-probe'
FILTER_MARKER='R60_HOST_FILTER_INSTALLED\n'
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


def verify_pins():
    if bounded_digest(base.__file__,100000)!=BASE_SHA:
        raise Hold('BASE_R49_BYTES_MISMATCH')
    if bounded_digest(LAUNCHER,16384)!=LAUNCHER_SHA:
        raise Hold('PINNED_AARCH64_FILTER_BYTES_MISMATCH')
    if bounded_digest(ARM,16384)!=ARM_SHA:
        raise Hold('PINNED_ARMV7_PROBE_BYTES_MISMATCH')
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
        runtime_probes={})
    created=[];parent_known=False;cleanup_ok=True
    try:
        verify_pins()
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
            helper_cid=base.docker(['create','--platform','linux/arm64','--pull','never',
                '--network','none','--name','pw3-r60-helper-'+uuid.uuid4().hex[:12],
                '--entrypoint','/bin/true',base.HELPER]).stdout.strip()
            if not base.HEX_ID.fullmatch(helper_cid):raise Hold('HELPER_CONTAINER_ID_INVALID')
            created.append(helper_cid)
            hi=base.inspect('container',helper_cid)
            if (hi.get('Image')!=helper['Id'] or hi.get('State',{}).get('Status')!='created'
                or hi.get('State',{}).get('Running') is not False or hi.get('HostConfig',{}).get('Privileged') is not False
                or hi.get('Mounts') not in (None,[]) or hi.get('HostConfig',{}).get('Binds') not in (None,[])
                or hi.get('HostConfig',{}).get('NetworkMode')!='none'):
                raise Hold('HELPER_CONTAINER_ISOLATION_UNVERIFIED')
            base.docker(['cp','-L',helper_cid+':/usr/bin/qemu-arm',str(qemu)])
            if bounded_digest(qemu,40*1024*1024)!=base.QEMU_SHA256 or base.elf_summary(qemu)['bits']!=64 or base.elf_summary(qemu)['machine']!=183:
                raise Hold('QEMU_EXECUTABLE_IDENTITY_MISMATCH')
            prep_cid=base.docker(['create','--platform','linux/arm/v7','--pull','never',
                '--network','none','--name','pw3-r60-prep-'+uuid.uuid4().hex[:12],
                '--entrypoint','/bin/true',base.PARENT]).stdout.strip()
            if not base.HEX_ID.fullmatch(prep_cid):raise Hold('PREP_CONTAINER_ID_INVALID')
            created.append(prep_cid)
            prep=base.inspect('container',prep_cid)
            if prep.get('Image')!=base.PARENT_ID or prep.get('State',{}).get('Status')!='created':
                raise Hold('PREP_CONTAINER_UNEXPECTED_STATE')
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
                    validate_guest(base.inspect('container',cid),guest_argv,readonly)
                readback=Path(tmp)/('readback-'+name+'-launcher')
                base.docker(['cp','-L',cid+':'+GUEST_LAUNCHER,str(readback)])
                if bounded_digest(readback,16384)!=LAUNCHER_SHA:raise Hold('SECCOMP_LAUNCHER_READBACK_MISMATCH')
                if not readonly:audit_diff(cid)
                before=base.inspect('container',cid)
                validate_guest(before,guest_argv,readonly)
                cp=base.docker(['start','--attach',cid],timeout=110,allow_nonzero=True)
                state=(base.inspect('container',cid).get('State') or {})
                if state.get('Status')!='exited' or state.get('Running') is not False or state.get('OOMKilled') is not False:
                    raise Hold('GUEST_EXIT_OOM_STATE_UNVERIFIED:'+name)
                if not isinstance(state.get('ExitCode'),int):raise Hold('GUEST_EXIT_CODE_MISSING:'+name)
                rc=state['ExitCode']
                r['arm_guest_execution_performed']=True
                sanitized=extract_filter_marker(cp.stdout,cp.stderr)
                r['host_seccomp_injection_performed']=True
                record={'guest_exit_code':rc,'host_filter_installed_marker_present':True,
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
            for name in TRACE_PAIRS:
                t=r['runtime_probes'][name]['trace']
                if t['target_guest_call_count']<1 or t['target_guest_enosys_count']<1:
                    raise Hold('TARGETED_GUEST_ENOSYS_NOT_OBSERVED:'+name)
            r.update(result=PASS,hold_category='NOT_BOOTABLE',host_seccomp_injection_performed=True,
                enosys_simulation_under_qemu_verified=True,
                qemu_pthread_tls_with_guest_getrandom_enosys_control_verified=True,
                qemu_busybox_stat_with_guest_statx_enosys_control_verified=True)
    except (Hold,base.Hold,ValueError,TypeError,KeyError,OSError,UnicodeError) as exc:
        r.update(result='HOLD',hold_category=str(exc).splitlines()[0][:150])
    finally:
        for cid in reversed(created):
            try:
                rm=base.docker(['rm','-f',cid],timeout=35,allow_nonzero=True)
                check=base.docker(['container','inspect',cid],timeout=35,allow_nonzero=True)
                if rm.returncode!=0 or check.returncode==0 or not re.search(r'No such (?:container|object)',check.stderr,re.I):
                    cleanup_ok=False
            except base.Hold:cleanup_ok=False
        r['all_created_containers_removed']=cleanup_ok and bool(created)
        if not cleanup_ok:r['container_cleanup_requires_review']=True
        if parent_known:
            try:r['original_image_unchanged']=base.image_info(base.PARENT)['Id']==base.PARENT_ID
            except base.Hold:r['original_image_unchanged']=False
        if r['result']==PASS and not (r['all_created_containers_removed'] and r.get('original_image_unchanged')):
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
