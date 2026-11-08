#!/usr/bin/env python3
"""R3877.59: explicit Mac/Colima-QEMU ARMv7 musl pthread + TLS runtime probe.

Research/education. Never contacts Kindle, bootloader, eMMC, or firmware.
Requires operator authorization, existing pinned cached ARMv7 Alpine and QEMU
helper images, and additionally-authorized writable disposable layer ONLY after
classified read-only docker cp refusal. Source-built ARM ELF is pinned and
injected solely into disposable guests; no image build or network access.

The musl loader comes from the pinned Alpine parent image and is NOT an
attestation of the original downstream patched musl build. QEMU's host kernel
is NOT the physical Kindle Linux 3.0.35 kernel. NOT_BOOTABLE immutable.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
from unittest.mock import patch

import pw3_r3877_49_3_controlled_trace as r49

MILESTONE = 'R3877.59'
PASS = 'PASS_PINNED_QEMU_ARMV7_MUSL_PTHREAD_TLS_AND_HOST_GETRANDOM_ONLY'
BASE_SHA256 = '5fa8ae5a386d32427ee67e068af55d4dd23a9e61b312357b00d9c0ed6d6ad659'
PROBE = Path(__file__).resolve().parent / 'pw3_r3877_59_armv7_probe.elf'
PROBE_SHA256 = '5ce343387f982330965aa1d101daf15d1d53fd38de329d8e7c14a30d6cd37085'
GUEST_PROBE = '/usr/bin/pw3-r3877-59-armv7-probe'
EXPECTED_OUTPUT = ('R59_PASS_ARMV7_PTHREAD_TLS\n'
                   'R59_OBS_GETRANDOM_SUPPORTED_BY_HOST\n'
                   'R59_OBS_GETENTROPY_SUPPORTED_BY_HOST\n'
                   'R59_PASS_QEMU_ARMV7_MUSL_PROBE_ONLY\n')
PROBES = (
    ('qemu_version', ('--version',)),
    ('busybox_true_control', ('/bin/busybox', 'true')),
    ('r59_probe_control', (GUEST_PROBE,)),
    ('r59_probe_trace', ('-strace', GUEST_PROBE)),
)
CONTROLS = frozenset({'busybox_true_control', 'r59_probe_control'})
TRACES = frozenset({'r59_probe_trace'})
TRACE_TO_CONTROL = {'r59_probe_trace':'r59_probe_control'}
ORIGINAL_PROBE_OK = r49.probe_ok

class Hold(Exception): pass


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for part in iter(lambda:f.read(1<<20),b''):
            h.update(part)
    return h.hexdigest()


def require_pinned():
    if not Path(r49.__file__).is_file() or Path(r49.__file__).is_symlink() or digest(r49.__file__) != BASE_SHA256:
        raise Hold('PINNED_R49_3_RUNNER_CHANGED')
    if not PROBE.is_file() or PROBE.is_symlink() or PROBE.stat().st_size>200000 or digest(PROBE)!=PROBE_SHA256:
        raise Hold('R59_ARMV7_PROBE_BINARY_BYTES_MISMATCH')
    b=PROBE.read_bytes()
    if len(b)<52 or b[:7]!=b'\x7fELF\x01\x01\x01':raise Hold('R59_ELF32_LE_HEADER_INVALID')
    etype,machine,version=struct.unpack_from('<HHI',b,16)
    flags=struct.unpack_from('<I',b,36)[0]
    off=struct.unpack_from('<I',b,28)[0]
    step,count=struct.unpack_from('<HH',b,42)
    if (etype,machine,version,flags)!=(3,40,1,0x05000400) or not (1<=count<=64 and step>=32 and off+step*count<=len(b)):
        raise Hold('R59_ARMV7_ELF_ABI_MISMATCH')
    tls=False;interps=[];loads=0
    for i in range(count):
        p=off+i*step
        kind,ofs=struct.unpack_from('<II',b,p)
        size=struct.unpack_from('<I',b,p+16)[0]
        if kind==1:loads+=1
        if kind==7:tls=True
        if kind==3:
            if size<2 or size>128 or ofs+size>len(b):raise Hold('R59_PT_INTERP_BOUNDS_INVALID')
            interps.append(b[ofs:ofs+size])
    if loads<1 or not tls or interps!=[b'/lib/ld-musl-armhf.so.1\0']:
        raise Hold('R59_ARMV7_TLS_OR_INTERP_MISMATCH')
    # SHA256-pinned ELF's dynamic imports already manually examined; no ELF
    # source-to-patched-musl equivalence or runtime guarantee is inferred.
    return True


def control_output_ok(name, rc, output):
    if name in ('qemu_version','busybox_true_control'):
        return ORIGINAL_PROBE_OK(name,rc,output)
    if name=='r59_probe_control':
        return rc==0 and output==EXPECTED_OUTPUT
    return False


def classify_guest_diff(cid, docker):
    cp=docker(['diff',cid])
    records=[line.strip() for line in cp.stdout.splitlines() if line.strip()]
    allowed={'A /usr/bin/qemu-arm-static','C /usr/bin/qemu-arm-static',
             'A '+GUEST_PROBE,'C '+GUEST_PROBE,'C /usr/bin','C /usr'}
    if any(x not in allowed for x in records):raise r49.Hold('R59_GUEST_WRITABLE_DIFF_UNEXPECTED')
    if not any(x.endswith(' /usr/bin/qemu-arm-static') for x in records):
        raise r49.Hold('R59_QEMU_INJECTION_DIFF_MISSING')
    if not any(x.endswith(' '+GUEST_PROBE) for x in records):
        raise r49.Hold('R59_PROBE_INJECTION_DIFF_MISSING')
    return {'allowed_changes_only':True,'reported_change_count':len(records),
            'output_sha256':hashlib.sha256(cp.stdout.encode()).hexdigest()}


def copied_probe_on_success(argv, orig_docker, **kwargs):
    """Only after successful QEMU injection, add the pinned extra ARM ELF."""
    result=orig_docker(argv,**kwargs)
    if (len(argv)==3 and argv[0]=='cp' and not argv[1].startswith('-')
        and isinstance(argv[2],str) and argv[2].endswith(':/usr/bin/qemu-arm-static')
        and result.returncode==0):
        cid=argv[2].split(':',1)[0]
        if not r49.HEX_ID.fullmatch(cid):raise r49.Hold('R59_GUEST_CONTAINER_ID_INVALID')
        orig_docker(['cp',str(PROBE),cid+':'+GUEST_PROBE])
        with tempfile.TemporaryDirectory(prefix='pw3-r59-readback-') as tmp:
            target=Path(tmp)/'probe.elf'
            orig_docker(['cp','-L',cid+':'+GUEST_PROBE,str(target)])
            if digest(target)!=PROBE_SHA256:
                raise r49.Hold('R59_GUEST_PROBE_READBACK_MISMATCH')
    return result


def preflight():
    return {'milestone':MILESTONE,'result':'HOLD','hold_category':'OFFLINE_QEMU_OPT_IN_REQUIRED',
            'immutable_hold':'NOT_BOOTABLE','docker_used':False,'arm_guest_execution_performed':False,
            'kindle_ssh_sessions':0,'physical_device_access_performed':False,
            'firmware_write_performed':False,'boot_performed':False,
            'host_binfmt_registration_changed':False,'host_mounts_enabled':False,
            'guest_network_enabled':False,'original_patched_musl_binary_reproducibility_verified':False,
            'vendor_kernel_syscall_dispatch_verified':False,'target_musl_linux_3_0_35_compatibility_verified':False,
            'runtime_getrandom_enosys_fallback_verified':False,'recovery_verified':False}


def assess(report):
    if not isinstance(report,dict) or report.get('result')!='PASS_QEMU_SYSCALL_NAMES_AND_UNTRACED_APPLET_CONTROLS_ONLY':
        raise Hold('R49_ISOLATED_QEMU_HOLD')
    if report.get('original_image_unchanged') is not True or report.get('all_created_containers_removed') is not True:
        raise Hold('R49_GUEST_CLEANUP_OR_PARENT_UNVERIFIED')
    if report.get('authorized_qemu_execution_performed') is not True or report.get('independent_untraced_controls_verified') is not True:
        raise Hold('R49_QEMU_CONTROLS_UNVERIFIED')
    if report.get('busybox_sha256')!=r49.BUSYBOX_SHA256 or report.get('qemu_binary_sha256')!=r49.QEMU_SHA256:
        raise Hold('R59_HELPER_BYTES_DIFFER')
    probes=report.get('runtime_probes')
    if not isinstance(probes,dict) or set(probes)!={k for k,_ in PROBES}:
        raise Hold('R59_PROBE_SET_INCOMPLETE')
    for control in CONTROLS:
        p=probes[control]
        if p.get('status')!='PASS' or p.get('exit_code')!=0 or p.get('expected_applet_output_matches') is not True:
            raise Hold('R59_UNTRACED_CONTROL_HOLD:'+control)
    trace=probes['r59_probe_trace']
    observation=trace.get('trace',{})
    if (trace.get('exit_code')!=0 or trace.get('untraced_control_verified') is not True
        or trace.get('control_probe')!='r59_probe_control'
        or not str(trace.get('status','')).startswith('TRACE_OBSERVED')
        or not isinstance(observation,dict) or observation.get('syscall_record_count',0)<1):
        raise Hold('R59_TRACE_CONTROL_HOLD')
    names=observation.get('syscall_names',[])
    if not isinstance(names,list) or not set(names).issuperset({'clone','getrandom'}):
        raise Hold('R59_PTHREAD_CLONE_OR_GETRANDOM_SYSCALL_UNOBSERVED')
    return {'syscall_names':names,'syscall_records':observation['syscall_record_count'],
            'clone_syscall_observed_in_qemu_trace':True,
            'getrandom_syscall_observed_in_qemu_trace':True,
            'futex_syscall_observed_in_qemu_trace':('futex' in names),
            'unknown_syscall_record_count':observation.get('trace_unknown_record_count'),
            'trace_enosys_record_count':observation.get('trace_enosys_record_count'),
            'trace_stream_attribution_verified':False,
            'guest_host_kernel_not_kindle_kernel':True}


def execute(allow_writable):
    result=preflight()
    result.update(docker_used=True,offline_qemu_authorized=True,
                  disposable_writable_layer_additional_opt_in=allow_writable)
    try:
        require_pinned()
        orig_docker=r49.docker
        with ExitStack() as patches:
            patches.enter_context(patch.object(r49,'PROBES',PROBES))
            patches.enter_context(patch.object(r49,'CONTROL_PROBES',CONTROLS))
            patches.enter_context(patch.object(r49,'TRACE_PROBES',TRACES))
            patches.enter_context(patch.object(r49,'TRACE_TO_CONTROL',TRACE_TO_CONTROL))
            patches.enter_context(patch.object(r49,'probe_ok',control_output_ok))
            patches.enter_context(patch.object(r49,'audit_diff',lambda cid:classify_guest_diff(cid,orig_docker)))
            patches.enter_context(patch.object(r49,'docker',lambda argv,**k:copied_probe_on_success(argv,orig_docker,**k)))
            underlying=r49.run(allow_writable)
        result.update(base_r49_result=underlying.get('result'),
                      base_error_category=underlying.get('error_category'),
                      read_only_copy_probe=underlying.get('read_only_copy_probe'),
                      all_created_containers_removed=underlying.get('all_created_containers_removed',False),
                      original_image_unchanged=underlying.get('original_image_unchanged',False),
                      writable_fallback_used=underlying.get('writable_fallback_used',False),
                      arm_guest_execution_performed=underlying.get('authorized_qemu_execution_performed',False))
        diag=assess(underlying)
        result.update(result=PASS,hold_category='NOT_BOOTABLE',
                      arm_pthread_and_isolated_tls_runtime_under_qemu_verified=True,
                      musl_loader_from_pinned_parent_used=True,
                      original_patched_musl_binary_reproducibility_verified=False,
                      probe_elf_sha256=PROBE_SHA256,
                      qemu_binary_sha256=r49.QEMU_SHA256,
                      busybox_sha256=r49.BUSYBOX_SHA256,
                      getrandom_and_getentropy_success_on_host_kernel=True,
                      trace_diagnostics=diag)
    except (Hold,ValueError,KeyError,TypeError,OSError) as e:
        result.update(result='HOLD',hold_category=str(e).splitlines()[0][:160])
    return result


def main(args=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--authorize-offline-qemu',action='store_true')
    p.add_argument('--allow-disposable-writable-layer',action='store_true')
    a=p.parse_args(args)
    if a.allow_disposable_writable_layer and not a.authorize_offline_qemu:
        r=preflight();r['hold_category']='WRITABLE_OPT_IN_REQUIRES_QEMU_AUTHORIZATION'
    elif a.authorize_offline_qemu:r=execute(a.allow_disposable_writable_layer)
    else:r=preflight()
    print(json.dumps(r,sort_keys=True,separators=(',',':')))
    return 0 if r['result']==PASS else 2

if __name__=='__main__':sys.exit(main())
