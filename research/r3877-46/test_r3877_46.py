#!/usr/bin/env python3
"""Host-only synthetic R3877.46 tests; no Docker daemon or Kindle operations."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r46', HERE / 'pw3_r3877_46_readonly_cp_gate.py')
r46 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r46)

PARENT_ID = r46.PARENT_ID


def guest_info(argv, readonly=True):
    return {
        'Image': PARENT_ID, 'State': {'Status':'created','Running':False},
        'Path':'/usr/bin/qemu-arm-static', 'Args':list(argv),
        'Config': {'User':'65534:65534','Entrypoint':['/usr/bin/qemu-arm-static']},
        'HostConfig': {'ReadonlyRootfs':readonly,'NetworkMode':'none','Privileged':False,
                       'Binds':None,'Devices':None,'DeviceRequests':None,
                       'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],
                       'PidsLimit':64,'Memory':268435456}, 'Mounts': []}


class UnitTests(unittest.TestCase):
    def test_default_preflight_zero_docker(self):
        with patch.object(r46,'docker',side_effect=AssertionError('No Docker permitted')):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r46.main([]),2)
            self.assertEqual(r46.preflight()['result'],'HOLD')
    def test_writable_flag_alone_refuses_without_docker(self):
        with patch.object(r46,'docker',side_effect=AssertionError('No Docker permitted')):
            stream=io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(r46.main(['--allow-disposable-writable-layer']),2)
            self.assertEqual(json.loads(stream.getvalue())['error_category'], 'WRITABLE_OPT_IN_REQUIRES_QEMU_AUTHORIZATION')
    def test_explicit_authorized_arg(self):
        with patch.object(r46,'run',return_value={'result':'PASS_ARM32_BUSYBOX_QEMU_ONLY'}) as method:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r46.main(['--authorize-offline-qemu']),0)
            method.assert_called_once_with(False)
    def test_explicit_writable_opt_in_arg(self):
        with patch.object(r46,'run',return_value={'result':'HOLD'}) as method:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r46.main(['--authorize-offline-qemu','--allow-disposable-writable-layer']),2)
            method.assert_called_once_with(True)
    def test_header_and_pins(self):
        self.assertTrue(r46.HEX_IMAGE.fullmatch(r46.PARENT_ID))
        self.assertEqual(len(r46.QEMU_SHA256),64)
        self.assertEqual(len(r46.BUSYBOX_SHA256),64)
        self.assertEqual(len(r46.PROBES),4)
        self.assertEqual(r46.PROBES[1][1],('/bin/busybox','--help'))
    def test_strict_guest_default_policy(self):
        self.assertTrue(r46.validate_guest(guest_info(['--version']), ('--version',), True))
    def test_writable_mode_requires_writable_inspect(self):
        with self.assertRaisesRegex(r46.Hold,'ROOTFS_POLICY'):
            r46.validate_guest(guest_info(['--version']), ('--version',), False)
    def test_readonly_mode_requires_readonly_inspect(self):
        with self.assertRaisesRegex(r46.Hold,'ROOTFS_POLICY'):
            r46.validate_guest(guest_info(['--version'],False), ('--version',), True)
    def test_network_denied(self):
        g=guest_info(['--version']);g['HostConfig']['NetworkMode']='bridge'
        with self.assertRaisesRegex(r46.Hold,'NETWORK'):
            r46.validate_guest(g,('--version',),True)
    def test_privileged_denied(self):
        g=guest_info(['--version']);g['HostConfig']['Privileged']=True
        with self.assertRaisesRegex(r46.Hold,'PRIVILEGE'):
            r46.validate_guest(g,('--version',),True)
    def test_capabilities_denied(self):
        g=guest_info(['--version']);g['HostConfig']['CapDrop']=[]
        with self.assertRaisesRegex(r46.Hold,'CAPABILITIES'):
            r46.validate_guest(g,('--version',),True)
    def test_bind_denied(self):
        g=guest_info(['--version']);g['HostConfig']['Binds']=['/host:/target']
        with self.assertRaisesRegex(r46.Hold,'MOUNT'):
            r46.validate_guest(g,('--version',),True)
    def test_devices_denied(self):
        g=guest_info(['--version']);g['HostConfig']['Devices']=[{'PathOnHost':'/dev/disk'}]
        with self.assertRaisesRegex(r46.Hold,'DEVICE'):
            r46.validate_guest(g,('--version',),True)
    def test_uid_denied(self):
        g=guest_info(['--version']);g['Config']['User']='0'
        with self.assertRaisesRegex(r46.Hold,'IDENTITY'):
            r46.validate_guest(g,('--version',),True)
    def test_resource_limits_denied(self):
        g=guest_info(['--version']);g['HostConfig']['Memory']=0
        with self.assertRaisesRegex(r46.Hold,'RESOURCE_LIMIT'):
            r46.validate_guest(g,('--version',),True)
    def test_stopped_required(self):
        g=guest_info(['--version']);g['State']['Status']='running'
        with self.assertRaisesRegex(r46.Hold,'STOPPED'):
            r46.validate_guest(g,('--version',),True)
    def test_arg_exact_required(self):
        g=guest_info(['-help'])
        with self.assertRaisesRegex(r46.Hold,'ARGV'):
            r46.validate_guest(g,('--help',),True)
    def test_cp_readonly_classification(self):
        e=r46.classify_cp_error(subprocess.CompletedProcess([],1,'','Error response from daemon: container rootfs is marked read-only\n'))
        self.assertEqual(e['classification'],'READONLY_ROOTFS_COPY_REJECTED')
        self.assertNotIn('Error response',json.dumps(e))
        self.assertFalse(e['raw_error_published'])
    def test_cp_ro_filesystem_alternative(self):
        e=r46.classify_cp_error(subprocess.CompletedProcess([],1,'','read-only file system'))
        self.assertEqual(e['classification'],'READONLY_ROOTFS_COPY_REJECTED')
    def test_cp_unknown_failure_not_relaxed(self):
        e=r46.classify_cp_error(subprocess.CompletedProcess([],1,'','permission denied'))
        self.assertEqual(e['classification'],'DOCKER_CP_FAILURE_UNCLASSIFIED')
    def test_cp_no_error_not_classified_ro(self):
        e=r46.classify_cp_error(subprocess.CompletedProcess([],0,'',''))
        self.assertEqual(e['classification'],'DOCKER_CP_FAILURE_UNCLASSIFIED')
    def test_diff_pin_accepts_only_emulator_and_ancestors(self):
        with patch.object(r46,'docker',return_value=subprocess.CompletedProcess([],0,'C /usr/bin\nA /usr/bin/qemu-arm-static\n','')):
            self.assertTrue(r46.audit_diff('a'*64)['allowed_changes_only'])
    def test_diff_rejects_file_written_by_guest(self):
        with patch.object(r46,'docker',return_value=subprocess.CompletedProcess([],0,'A /usr/bin/qemu-arm-static\nA /etc/pwned\n','')):
            with self.assertRaisesRegex(r46.Hold,'UNEXPECTED_FILESYSTEM'):
                r46.audit_diff('a'*64)
    def test_diff_rejects_absent_emulator(self):
        with patch.object(r46,'docker',return_value=subprocess.CompletedProcess([],0,'','')):
            with self.assertRaisesRegex(r46.Hold,'UNEXPECTED_FILESYSTEM'):
                r46.audit_diff('a'*64)
    def test_guest_create_writable_and_readonly_separated(self):
        self.assertIn('--read-only',r46.guest_create(('--version',),True))
        self.assertNotIn('--read-only',r46.guest_create(('--version',),False))
        for flag in ('--network','--cap-drop','--pids-limit','--memory','--security-opt','--pull'):
            self.assertIn(flag,r46.guest_create(('--version',),False))
    def test_probe_versions(self):
        self.assertTrue(r46.probe_ok('busybox_double_dash_help',0,'BusyBox v1.37.0'))
        self.assertFalse(r46.probe_ok('busybox_double_dash_help',127,'-help: applet not found\n'))
        self.assertTrue(r46.probe_ok('qemu_version',0,'qemu-arm version 10.0.4 (v10.0.4)'))
        self.assertTrue(r46.probe_ok('busybox_true',0,''))
        self.assertTrue(r46.probe_ok('busybox_uname_machine',0,'armv7l\n'))
        self.assertFalse(r46.probe_ok('busybox_uname_machine',0,'aarch64\n'))
    def test_invalid_docker_argv(self):
        with self.assertRaisesRegex(r46.Hold,'INVALID_DOCKER_ARGV'):
            r46.docker(['cp',None])
    def test_inspect_empty_json(self):
        with patch.object(r46,'docker',return_value=subprocess.CompletedProcess([],0,'[]','')):
            with self.assertRaisesRegex(r46.Hold,'INSPECT_INVALID'):
                r46.inspect('image','x')
    def test_elf_and_sha(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'elf';b=bytearray(64);b[:6]=b'\x7fELF\x01\x01';struct.pack_into('<H',b,18,40);struct.pack_into('<I',b,36,0x05000400);p.write_bytes(b)
            self.assertEqual(r46.elf_summary(p),{'bits':32,'machine':40,'e_flags':'0x05000400'})
            self.assertEqual(r46.sha256_file(p),hashlib.sha256(b).hexdigest())
    def test_no_image_build_commit_or_host_mount_in_source(self):
        source=Path(r46.__file__).read_text()
        for forbidden in ("docker(['commit'", "docker(['build'", "docker(['import'", "docker(['pull'", "docker(['run'", "docker(['volume'", "docker(['mount'", "docker(['exec'"):
            self.assertNotIn(forbidden,source)


class SyntheticLifecycle(unittest.TestCase):
    def simulate(self, *, allow_writable, cp_error='read-only file system', diff_extra=False):
        containers={}
        issued=[]
        seq=[0]
        def fake_docker(argv, timeout=100, allow_nonzero=False):
            a=list(argv);issued.append(a)
            if a[:2]==['version','--format']:
                return subprocess.CompletedProcess(a,0,json.dumps({'Arch':'arm64'}),'')
            if a[:2]==['image','inspect']:
                if a[2]==r46.PARENT:
                    js={'Id':PARENT_ID,'Os':'linux','Architecture':'arm','Variant':'v7'}
                elif a[2]==r46.HELPER:
                    js={'Id':'sha256:'+'2'*64,'Os':'linux','Architecture':'arm64','RepoDigests':[r46.HELPER_DIGEST]}
                else:
                    raise AssertionError(a)
                return subprocess.CompletedProcess(a,0,json.dumps([js]),'')
            if a[0]=='create':
                seq[0]+=1;cid=f'{seq[0]:064x}';name=a[a.index('--name')+1]
                if 'guest-' in name:
                    arr=a[a.index(r46.PARENT)+1:]
                    js=guest_info(arr,readonly='--read-only' in a)
                else:
                    js={'Image': 'sha256:'+'2'*64 if 'helper' in name else PARENT_ID,
                        'State':{'Status':'created','Running':False}}
                containers[cid]=js
                return subprocess.CompletedProcess(a,0,cid+'\n','')
            if a[:2]==['container','inspect']:
                if a[2] not in containers:
                    return subprocess.CompletedProcess(a,1,'','Error: No such container: '+a[2])
                return subprocess.CompletedProcess(a,0,json.dumps([containers[a[2]]]),'')
            if a[0]=='cp':
                dest=a[-1]; src=a[-2]
                if ':' in dest and '/usr/bin/qemu-arm-static' in dest:
                    cid=dest.split(':')[0]
                    if containers[cid]['HostConfig']['ReadonlyRootfs']:
                        return subprocess.CompletedProcess(a,1,'',cp_error)
                    return subprocess.CompletedProcess(a,0,'','')
                if ':' not in dest:
                    p=Path(dest);p.parent.mkdir(parents=True,exist_ok=True)
                    b=bytearray(64);b[:6]=b'\x7fELF\x02\x01' if '/qemu' in src else b'\x7fELF\x01\x01'
                    struct.pack_into('<H',b,18,183 if '/qemu' in src else 40)
                    if '/qemu' not in src:struct.pack_into('<I',b,36,0x05000400)
                    p.write_bytes(b)
                    return subprocess.CompletedProcess(a,0,'','')
                raise AssertionError(a)
            if a[:2]==['start','--attach']:
                cid=a[2];c=containers[cid];c['State']={'Status':'exited','Running':False,'OOMKilled':False,'ExitCode':0}
                arr=c['Args']
                out={('--version',):'qemu-arm version 10.0.4 (v10.0.4)\n',
                     ('/bin/busybox','--help'):'BusyBox v1.37.0\n',
                     ('/bin/busybox','true'):'',
                     ('/bin/busybox','uname','-m'):'armv7l\n'}[tuple(arr)]
                return subprocess.CompletedProcess(a,0,out,'')
            if a[0]=='diff':
                return subprocess.CompletedProcess(a,0,'A /usr/bin/qemu-arm-static\n'+('A /etc/unauthorized\n' if diff_extra else ''),'')
            if a[:2]==['rm','-f']:
                containers.pop(a[2],None)
                return subprocess.CompletedProcess(a,0,a[2],'')
            raise AssertionError('Unexpected docker: '+str(a))
        def fake_hash(p):
            return r46.BUSYBOX_SHA256 if Path(p).name=='busybox' else r46.QEMU_SHA256
        with patch.object(r46,'docker',side_effect=fake_docker),patch.object(r46,'sha256_file',side_effect=fake_hash):
            result=r46.run(allow_writable=allow_writable)
        return result,issued,containers
    def test_readonly_probe_confirms_and_holds_without_extra_permission(self):
        result,issued,containers=self.simulate(allow_writable=False)
        self.assertEqual(result['result'],'HOLD')
        self.assertEqual(result['error_category'],'READONLY_COPY_REJECTED_WRITABLE_FALLBACK_NOT_AUTHORIZED')
        self.assertEqual(result['read_only_copy_probe']['classification'],'READONLY_ROOTFS_COPY_REJECTED')
        self.assertFalse(result['authorized_qemu_execution_performed'])
        self.assertFalse(result['writable_fallback_used'])
        self.assertTrue(result['all_created_containers_removed'])
        self.assertTrue(result['original_image_unchanged'])
        self.assertFalse(any(x[0]=='start' for x in issued))
        self.assertEqual(containers,{})
    def test_explicit_optin_full_four_probes_with_prechecked_readonly_failure(self):
        result,issued,containers=self.simulate(allow_writable=True)
        self.assertEqual(result['result'],'PASS_ARM32_BUSYBOX_QEMU_ONLY',result)
        self.assertTrue(result['writable_fallback_used'])
        self.assertTrue(result['authorized_qemu_execution_performed'])
        self.assertEqual(len(result['runtime_probes']),4)
        self.assertTrue(result['all_created_containers_removed'])
        self.assertTrue(result['original_image_unchanged'])
        self.assertEqual(containers,{})
        self.assertEqual(len([a for a in issued if a[0]=='start']),4)
        self.assertFalse(any(a[0] in ('run','commit','import','build','pull') for a in issued))
    def test_unknown_cp_error_never_enters_writable_fallback(self):
        result,issued,_=self.simulate(allow_writable=True,cp_error='permission denied')
        self.assertEqual(result['result'],'HOLD')
        self.assertEqual(result['error_category'],'READONLY_GUEST_COPY_FAILED_UNCLASSIFIED')
        self.assertFalse(result['writable_fallback_used'])
        self.assertFalse(any(x[0]=='start' for x in issued))
    def test_writable_diff_change_after_exec_is_hold(self):
        result,issued,_=self.simulate(allow_writable=True,diff_extra=True)
        self.assertEqual(result['result'],'HOLD')
        self.assertEqual(result['error_category'],'WRITABLE_GUEST_UNEXPECTED_FILESYSTEM_DIFF')
        self.assertFalse(any(x[0]=='start' for x in issued))

if __name__=='__main__':
    unittest.main()
