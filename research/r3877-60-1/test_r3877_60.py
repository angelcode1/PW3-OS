"""R3877.60 synthetic host-only regression tests: zero Docker, no ARM run."""
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import pw3_r3877_60_qemu_enosys as m


def guest_info(args,readonly):
    return {
        'Image':m.base.PARENT_ID,'State':{'Status':'created','Running':False},
        'Path':m.GUEST_LAUNCHER,'Args':[m.GUEST_QEMU,*args],
        'Config':{'User':'65534:65534','Entrypoint':[m.GUEST_LAUNCHER]},
        'HostConfig':{'ReadonlyRootfs':readonly,'NetworkMode':'none','Privileged':False,
            'Binds':None,'Devices':None,'DeviceRequests':None,'CapDrop':['ALL'],
            'SecurityOpt':['no-new-privileges'],'PidsLimit':64,'Memory':268435456},
        'Mounts':[],
    }

class OfflineTests(unittest.TestCase):
    def bad(self,func,msg):
        with self.assertRaisesRegex(m.Hold,msg):func()

    def test_01_default_no_docker(self):
        with patch.object(m.base,'docker',side_effect=AssertionError('Docker forbidden')):
            stream=io.StringIO()
            with redirect_stdout(stream):self.assertEqual(m.main([]),2)
            data=json.loads(stream.getvalue())
            self.assertEqual(data['result'],'HOLD');self.assertFalse(data['docker_used'])
            self.assertEqual(data['immutable_hold'],'NOT_BOOTABLE')

    def test_02_writable_only_no_docker(self):
        with patch.object(m.base,'docker',side_effect=AssertionError('Docker forbidden')):
            stream=io.StringIO()
            with redirect_stdout(stream):self.assertEqual(m.main(['--allow-disposable-writable-layer']),2)
            self.assertIn('WRITABLE_OPT_IN',stream.getvalue())

    def test_03_explicit_authorized_mode(self):
        with patch.object(m,'run',return_value={'result':m.PASS}) as r:
            with redirect_stdout(io.StringIO()):self.assertEqual(m.main(['--authorize-offline-qemu']),0)
            r.assert_called_once_with(False)

    def test_04_writable_opt_in_explicit(self):
        with patch.object(m,'run',return_value={'result':'HOLD'}) as r:
            with redirect_stdout(io.StringIO()):self.assertEqual(m.main(['--authorize-offline-qemu','--allow-disposable-writable-layer']),2)
            r.assert_called_once_with(True)

    def test_05_pins(self):self.assertTrue(m.verify_pins())
    def test_06_probe_paths(self):
        self.assertEqual(m.PROBES[0][0],'arm_control')
        self.assertEqual(m.PROBES[0][1],(m.GUEST_ARM,))
        self.assertEqual(set(m.TRACE_PAIRS),{'arm_trace','stat_trace'})

    def test_07_launcher_static_aarch64(self):
        b=m.LAUNCHER.read_bytes()
        self.assertEqual(b[:7],b'\x7fELF\x02\x01\x01')
        self.assertEqual(struct.unpack_from('<H',b,16)[0],2)
        self.assertEqual(struct.unpack_from('<H',b,18)[0],183)
        self.assertEqual(hashlib.sha256(b).hexdigest(),m.LAUNCHER_SHA)

    def test_08_launcher_has_no_interp(self):
        b=m.LAUNCHER.read_bytes();off=struct.unpack_from('<Q',b,32)[0];stride,num=struct.unpack_from('<HH',b,54)
        self.assertFalse(any(struct.unpack_from('<I',b,off+i*stride)[0]==3 for i in range(num)))

    def test_09_launcher_has_filter_install_marker(self):
        self.assertIn(m.FILTER_MARKER.encode(),m.LAUNCHER.read_bytes())

    def test_10_launcher_source_has_two_target_calls(self):
        s=(Path(__file__).parent/'pw3_r3877_60_aarch64_seccomp_launcher.c').read_text()
        for t in ('GUEST_FILTERED_GETRANDOM_NR 278','GUEST_FILTERED_STATX_NR 291','PR_SET_NO_NEW_PRIVS','PR_SET_SECCOMP','SECCOMP_RET_ERRNO','NR_EXECVE'):
            self.assertIn(t,s)
        self.assertNotIn('SCMP_ACT_ALLOW',s)

    def test_11_guest_hardened(self):self.assertTrue(m.validate_guest(guest_info(['-strace','/bin/busybox','stat'],False),['-strace','/bin/busybox','stat'],False))
    def test_12_guest_readonly(self):self.assertTrue(m.validate_guest(guest_info(['/bin/busybox','true'],True),['/bin/busybox','true'],True))
    def test_13_wrong_argv(self):self.bad(lambda:m.validate_guest(guest_info(['true'],True),['false'],True),'ARGS')
    def test_14_wrong_image(self):
        g=guest_info(['true'],True);g['Image']='sha256:'+'f'*64
        self.bad(lambda:m.validate_guest(g,['true'],True),'PARENT')
    def test_15_running_guest(self):
        g=guest_info(['true'],True);g['State']['Running']=True
        self.bad(lambda:m.validate_guest(g,['true'],True),'PARENT')
    def test_16_wrong_user(self):
        g=guest_info(['true'],True);g['Config']['User']='0:0'
        self.bad(lambda:m.validate_guest(g,['true'],True),'UNPRIVILEGED')
    def test_17_host_mount_rejected(self):
        g=guest_info(['true'],True);g['Mounts']=[{'Source':'/private'}]
        self.bad(lambda:m.validate_guest(g,['true'],True),'MOUNTS')
    def test_18_seccomp_replacement_rejected(self):
        g=guest_info(['true'],True);g['HostConfig']['SecurityOpt'].append('seccomp=unconfined')
        self.bad(lambda:m.validate_guest(g,['true'],True),'SECCOMP')
    def test_19_missing_no_new_privileges(self):
        g=guest_info(['true'],True);g['HostConfig']['SecurityOpt']=[]
        self.bad(lambda:m.validate_guest(g,['true'],True),'NNP')
    def test_20_privilege_rejected(self):
        g=guest_info(['true'],True);g['HostConfig']['Privileged']=True
        self.bad(lambda:m.validate_guest(g,['true'],True),'PRIVILEGE')
    def test_21_network_rejected(self):
        g=guest_info(['true'],True);g['HostConfig']['NetworkMode']='bridge'
        self.bad(lambda:m.validate_guest(g,['true'],True),'NETWORK')
    def test_22_resource_rejected(self):
        g=guest_info(['true'],True);g['HostConfig']['Memory']=0
        self.bad(lambda:m.validate_guest(g,['true'],True),'RESOURCES')
    def test_23_capabilities_rejected(self):
        g=guest_info(['true'],True);g['HostConfig']['CapDrop']=[]
        self.bad(lambda:m.validate_guest(g,['true'],True),'CAPABILITIES')
    def test_24_wrong_readonly_policy(self):
        self.bad(lambda:m.validate_guest(guest_info(['true'],False),['true'],True),'READONLY')
    def test_25_create_guest_has_no_host_mount_or_network(self):
        argv=m.create_guest(['/bin/busybox','true'],True)
        self.assertIn('--read-only',argv);self.assertIn('none',argv)
        self.assertNotIn('--mount',argv);self.assertNotIn('--privileged',argv)
        self.assertEqual(argv[-3:],[m.GUEST_QEMU,'/bin/busybox','true'])
    def test_26_writable_create_missing_readonly(self):
        argv=m.create_guest(['/bin/busybox','true'],False)
        self.assertNotIn('--read-only',argv)
        self.assertEqual(argv[-3:],[m.GUEST_QEMU,'/bin/busybox','true'])
    def test_27_marker_stripped(self):
        self.assertEqual(m.extract_filter_marker('ok\n',m.FILTER_MARKER),'ok\n')
    def test_28_marker_in_stdout(self):
        self.assertEqual(m.extract_filter_marker(m.FILTER_MARKER+'ok\n',''),'ok\n')
    def test_29_missing_marker_hold(self):self.bad(lambda:m.extract_filter_marker('ok\n',''),'MARKER')
    def test_30_duplicate_marker_hold(self):self.bad(lambda:m.extract_filter_marker(m.FILTER_MARKER*2,''),'MARKER')
    def test_31_arm_control_exact(self):self.assertTrue(m.direct_control_ok('arm_control',0,m.ARM_EXPECTED,123))
    def test_32_arm_control_wrong_marker(self):self.assertFalse(m.direct_control_ok('arm_control',0,m.ARM_EXPECTED.replace('ENOSYS','SUPPORTED_BY_HOST'),123))
    def test_33_arm_control_exit_fail(self):self.assertFalse(m.direct_control_ok('arm_control',1,m.ARM_EXPECTED,123))
    def test_34_stat_control_exact(self):self.assertTrue(m.direct_control_ok('stat_control',0,'123\n',123))
    def test_35_stat_control_wrong_size(self):self.assertFalse(m.direct_control_ok('stat_control',0,'124\n',123))
    def test_36_trace_getrandom_enosys(self):
        log=m.FILTER_MARKER+'123 getrandom(0,16,0) = -1 errno=38 (Function not implemented)\n'
        t=m.parse_trace('arm_trace',log,'')
        self.assertEqual(t['target_guest_enosys_count'],1)
        self.assertEqual(t['target_guest_call_count'],1)
    def test_37_trace_statx_enosys(self):
        log=m.FILTER_MARKER+'123 statx(0,0,0,0,0) = -1 errno=38 (Function not implemented)\n'
        t=m.parse_trace('stat_trace',log,'')
        self.assertEqual(t['target_guest_enosys_count'],1)
    def test_38_trace_success_no_enosys(self):
        log=m.FILTER_MARKER+'123 getrandom(0,16,0) = 16\n'
        t=m.parse_trace('arm_trace',log,'')
        self.assertEqual(t['target_guest_enosys_count'],0)
    def test_39_wrong_trace_syscall_doesnt_count(self):
        log=m.FILTER_MARKER+'123 statx(0,0,0,0,0) = -1 errno=38 (Function not implemented)\n'
        t=m.parse_trace('arm_trace',log,'')
        self.assertEqual(t['target_guest_enosys_count'],0)
    def test_40_unclassified_trace_not_suppressed(self):
        log=m.FILTER_MARKER+'APP UNKNOWN\n123 getrandom(0,16,0) = -1 errno=38 (Function not implemented)\n'
        t=m.parse_trace('arm_trace',log,'')
        self.assertEqual(t['trace_unclassified_line_count'],1)
        self.assertTrue(t['raw_trace_published'] is False)
    def test_41_readonly_copy_classified(self):
        cp=subprocess.CompletedProcess([],1,'','Error: read-only file system')
        self.assertEqual(m.sanitized_error(cp)['classification'],'READONLY_COPY_REJECTED')
    def test_42_copy_error_other_not_recognized(self):
        cp=subprocess.CompletedProcess([],1,'','permission denied')
        self.assertEqual(m.sanitized_error(cp)['classification'],'COPY_FAILURE_UNCLASSIFIED')
    def test_43_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            real=Path(d)/'real';real.write_bytes(b'x');alias=Path(d)/'alias';alias.symlink_to(real)
            self.bad(lambda:m.bounded_digest(alias),'UNSAFE')
    def test_44_large_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'big';path.write_bytes(b'x'*100)
            self.bad(lambda:m.bounded_digest(path,10),'UNSAFE')
    def test_45_default_safety_flags(self):
        r=m.preflight()
        for key in ('boot_performed','physical_device_access_performed','firmware_write_performed','recovery_verified','runtime_musl_getentropy_enosys_fallback_verified','actual_vendor_kernel_compatibility_verified'):
            self.assertFalse(r[key],key)

if __name__=='__main__':unittest.main()
