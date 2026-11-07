#!/usr/bin/env python3
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
spec = importlib.util.spec_from_file_location('r45', HERE / 'pw3_r3877_45_direct_stopped_guest.py')
r45 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r45)


def example_guest(argv, *, parent=None):
    return {'Image': parent or 'sha256:' + '1' * 64, 'State': {'Status': 'created', 'Running': False},
            'Path': '/usr/bin/qemu-arm-static', 'Args': list(argv),
            'Config': {'User': '65534:65534', 'Entrypoint': ['/usr/bin/qemu-arm-static']},
            'HostConfig': {'ReadonlyRootfs': True, 'NetworkMode': 'none', 'Privileged': False,
                           'Binds': None, 'Devices': None, 'DeviceRequests': None,
                           'CapDrop': ['ALL'], 'SecurityOpt': ['no-new-privileges'],
                           'PidsLimit': 64, 'Memory': 268435456}, 'Mounts': []}


class R45Tests(unittest.TestCase):
    def test_preflight_does_not_call_docker(self):
        with patch.object(r45, 'docker', side_effect=AssertionError('Docker called')):
            result = r45.preflight()
            self.assertEqual(result['immutable_hold'], 'NOT_BOOTABLE')
            self.assertEqual(result['result'], 'HOLD')
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r45.main([]), 2)

    def test_authorization_required(self):
        with patch.object(r45, 'run', side_effect=AssertionError('Runtime called')):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r45.main([]), 2)

    def test_authorization_success_cli(self):
        with patch.object(r45, 'run', return_value={'result': 'PASS_ARM32_BUSYBOX_QEMU_ONLY'}):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r45.main(['--authorize-offline-qemu']), 0)

    def test_hard_pins(self):
        self.assertEqual(len(r45.QEMU_ARM_SHA256), 64)
        self.assertEqual(r45.BUSYBOX_SHA256, 'df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c')
        self.assertEqual(len(r45.PROBES), 4)
        self.assertNotIn('commit', Path(r45.__file__).read_text().split('docker([')[1])

    def test_correct_help(self):
        self.assertTrue(r45.probe_status('busybox_double_dash_help', 0, 'BusyBox v1.37.0'))
        self.assertFalse(r45.probe_status('busybox_double_dash_help', 127, '-help: applet not found\n'))
        self.assertFalse(r45.probe_status('busybox_double_dash_help', 0, 'usage'))

    def test_qemu_version(self):
        self.assertTrue(r45.probe_status('qemu_version', 0, 'qemu-arm version 10.0.4 (v10.0.4)'))
        self.assertFalse(r45.probe_status('qemu_version', 0, 'qemu-arm version 10.0.5'))

    def test_true_probe(self):
        self.assertTrue(r45.probe_status('busybox_true', 0, ''))
        self.assertFalse(r45.probe_status('busybox_true', 0, 'oops'))

    def test_uname_strict_armv7(self):
        self.assertTrue(r45.probe_status('busybox_uname_machine', 0, 'armv7l\n'))
        self.assertFalse(r45.probe_status('busybox_uname_machine', 0, 'aarch64\n'))

    def test_guest_accepts_strict_policy(self):
        self.assertTrue(r45.validate_guest(example_guest(['/bin/busybox', '--help']), 'sha256:' + '1'*64, ('/bin/busybox', '--help')))

    def test_guest_rejects_wrong_image(self):
        with self.assertRaisesRegex(r45.Hold, 'PARENT'):
            r45.validate_guest(example_guest(['--version']), 'sha256:' + '2'*64, ('--version',))

    def test_guest_rejects_bad_argv(self):
        with self.assertRaisesRegex(r45.Hold, 'ARGV'):
            r45.validate_guest(example_guest(['/bin/busybox', '-help']), 'sha256:' + '1'*64, ('/bin/busybox', '--help'))

    def test_guest_rejects_missing_readonly(self):
        j=example_guest(['--version']); j['HostConfig']['ReadonlyRootfs'] = False
        with self.assertRaisesRegex(r45.Hold, 'READONLY'):
            r45.validate_guest(j, 'sha256:' + '1'*64, ('--version',))

    def test_guest_rejects_network(self):
        j=example_guest(['--version']); j['HostConfig']['NetworkMode'] = 'bridge'
        with self.assertRaisesRegex(r45.Hold, 'NETWORK'):
            r45.validate_guest(j, 'sha256:' + '1'*64, ('--version',))

    def test_guest_rejects_host_mounts(self):
        j=example_guest(['--version']); j['Mounts'] = [{'Type': 'bind'}]
        with self.assertRaisesRegex(r45.Hold, 'MOUNT'):
            r45.validate_guest(j, 'sha256:' + '1'*64, ('--version',))

    def test_guest_rejects_privileged(self):
        j=example_guest(['--version']); j['HostConfig']['Privileged']=True
        with self.assertRaisesRegex(r45.Hold, 'PRIVILEGED'):
            r45.validate_guest(j, 'sha256:' + '1'*64, ('--version',))

    def test_guest_rejects_device(self):
        j=example_guest(['--version']); j['HostConfig']['Devices']=[{'PathOnHost':'/dev/sda'}]
        with self.assertRaisesRegex(r45.Hold, 'DEVICE'):
            r45.validate_guest(j, 'sha256:' + '1'*64, ('--version',))

    def test_guest_rejects_root(self):
        j=example_guest(['--version']); j['Config']['User']='0'
        with self.assertRaisesRegex(r45.Hold, 'USER'):
            r45.validate_guest(j, 'sha256:' + '1'*64, ('--version',))

    def test_guest_rejects_caps(self):
        j=example_guest(['--version']); j['HostConfig']['CapDrop'] = None
        with self.assertRaisesRegex(r45.Hold, 'CAPABILITIES'):
            r45.validate_guest(j, 'sha256:' + '1'*64, ('--version',))

    def test_guest_rejects_resource_limits(self):
        j=example_guest(['--version']); j['HostConfig']['PidsLimit']=0
        with self.assertRaisesRegex(r45.Hold, 'RESOURCE'):
            r45.validate_guest(j, 'sha256:' + '1'*64, ('--version',))

    def test_guest_rejects_running_before_injection(self):
        j=example_guest(['--version']); j['State']['Status'] = 'running'; j['State']['Running'] = True
        with self.assertRaisesRegex(r45.Hold, 'STOPPED'):
            r45.validate_guest(j, 'sha256:' + '1'*64, ('--version',))

    def test_elf32_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=bytearray(64); b[:6]=b'\x7fELF\x01\x01'; struct.pack_into('<H',b,18,40); struct.pack_into('<I',b,36,0x05000400)
            f=Path(tmp)/'elf'; f.write_bytes(b)
            self.assertEqual(r45.elf_summary(f), {'bits':32,'machine':40,'e_flags':'0x05000400'})

    def test_elf64_aarch64(self):
        with tempfile.TemporaryDirectory() as tmp:
            b=bytearray(64); b[:6]=b'\x7fELF\x02\x01'; struct.pack_into('<H',b,18,183)
            f=Path(tmp)/'elf'; f.write_bytes(b)
            self.assertEqual(r45.elf_summary(f)['machine'],183)

    def test_invalid_elf_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'bad';f.write_bytes(b'bad')
            with self.assertRaisesRegex(r45.Hold, 'ELF_HEADER_INVALID'):
                r45.elf_summary(f)

    def test_invalid_docker_argv(self):
        with self.assertRaisesRegex(r45.Hold, 'INVALID_DOCKER_ARGV'):
            r45.docker(['ps', None])

    def test_inspect_invalid_json(self):
        with patch.object(r45,'docker',return_value=subprocess.CompletedProcess([],0,'[]','')):
            with self.assertRaisesRegex(r45.Hold,'INSPECT_JSON_INVALID'):
                r45.inspect_json('image','x')

    def test_image_info_requires_sha256(self):
        with patch.object(r45,'inspect_json',return_value={'Id':'bad'}):
            with self.assertRaisesRegex(r45.Hold,'IMAGE_ID_INVALID'):
                r45.image_info('x')

    def test_invalid_docker_status(self):
        with patch.object(r45,'docker',side_effect=r45.Hold('DOCKER_COMMAND_FAILED')):
            r=r45.run()
        self.assertEqual(r['result'],'HOLD')
        self.assertEqual(r['error_category'],'DOCKER_COMMAND_FAILED')
        self.assertFalse(r['authorized_qemu_execution_performed'])

    def test_no_commit_or_import_command_in_runtime(self):
        import inspect
        source=inspect.getsource(r45.run)
        self.assertNotIn("docker(['commit'", source)
        self.assertNotIn("docker(['import'", source)
        self.assertNotIn("docker(['pull'", source)
        self.assertNotIn("docker(['run'", source)
        self.assertIn("docker(['start', '--attach', cid]", source)



class R45LifecycleSimulationTests(unittest.TestCase):
    def test_full_synthetic_lifecycle_four_probes_and_cleanup(self):
        import copy
        parent_id = 'sha256:' + '1' * 64
        helper_id = 'sha256:' + '2' * 64
        containers = {}
        captured_commands = []
        sequence = [0]

        def fake_docker(args, timeout=100, allow_nonzero=False):
            args = list(args)
            captured_commands.append(args)
            if args[:2] == ['version', '--format']:
                return subprocess.CompletedProcess(args, 0, json.dumps({'Arch':'arm64'}), '')
            if args[:2] == ['image', 'inspect']:
                ref = args[2]
                if ref == r45.PARENT:
                    obj = {'Id':parent_id, 'Os':'linux', 'Architecture':'arm', 'Variant':'v7'}
                elif ref == r45.HELPER:
                    obj = {'Id':helper_id, 'Os':'linux', 'Architecture':'arm64', 'RepoDigests':[r45.HELPER_DIGEST]}
                else:
                    raise AssertionError('Unknown image inspect: '+ref)
                return subprocess.CompletedProcess(args,0,json.dumps([obj]),'')
            if args[0] == 'create':
                sequence[0]+=1
                cid = f'{sequence[0]:064x}'
                if '--name' in args:
                    name = args[args.index('--name')+1]
                else:
                    raise AssertionError('No unique name')
                if 'guest-' in name:
                    argv = args[args.index(r45.PARENT)+1:]
                    obj = example_guest(argv,parent=parent_id)
                    obj['State'] = {'Status':'created','Running':False}
                elif 'helper-' in name:
                    obj = {'Image':helper_id, 'State':{'Status':'created','Running':False}}
                else:
                    obj = {'Image':parent_id, 'State':{'Status':'created','Running':False}}
                containers[cid] = obj
                return subprocess.CompletedProcess(args,0,cid+'\n','')
            if args[:2] == ['container', 'inspect']:
                return subprocess.CompletedProcess(args,0,json.dumps([containers[args[2]]]),'')
            if args[0]=='cp':
                dest=Path(args[-1])
                if ':' not in args[-1] and '/qemu-arm' in args[-2]:
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    b=bytearray(64); b[:6]=b'\x7fELF\x02\x01';struct.pack_into('<H',b,18,183)
                    dest.write_bytes(b)
                elif ':' not in args[-1] and '/bin/busybox' in args[-2]:
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    b=bytearray(64); b[:6]=b'\x7fELF\x01\x01';struct.pack_into('<H',b,18,40);struct.pack_into('<I',b,36,0x05000400)
                    dest.write_bytes(b)
                elif ':' not in args[-1] and '/qemu-arm-static' in args[-2]:
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    b=bytearray(64); b[:6]=b'\x7fELF\x02\x01';struct.pack_into('<H',b,18,183)
                    dest.write_bytes(b)
                return subprocess.CompletedProcess(args,0,'','')
            if args[:2] == ['start','--attach']:
                cid=args[2]
                obj=containers[cid]
                obj['State']={'Status':'exited','Running':False,'OOMKilled':False,'ExitCode':0}
                argv=obj['Args']
                if argv==['--version']:
                    output='qemu-arm version 10.0.4 (v10.0.4)\n'
                elif argv==['/bin/busybox','--help']:
                    output='BusyBox v1.37.0\n'
                elif argv==['/bin/busybox','true']:
                    output=''
                elif argv==['/bin/busybox','uname','-m']:
                    output='armv7l\n'
                else:
                    raise AssertionError('Unexpected argv')
                return subprocess.CompletedProcess(args,0,output,'')
            if args[:2] == ['rm','-f']:
                containers.pop(args[2],None)
                return subprocess.CompletedProcess(args,0,args[2],'')
            raise AssertionError('Unknown Docker command: '+str(args))

        def fake_sha(path):
            name=Path(path).name
            if name=='busybox':return r45.BUSYBOX_SHA256
            return r45.QEMU_ARM_SHA256
        with patch.object(r45,'docker',side_effect=fake_docker), patch.object(r45,'sha256_file',side_effect=fake_sha):
            result=r45.run()
        self.assertEqual(result['result'],'PASS_ARM32_BUSYBOX_QEMU_ONLY')
        self.assertTrue(result['authorized_qemu_execution_performed'])
        self.assertEqual(len(result['runtime_probes']),4)
        self.assertTrue(result['all_created_containers_removed'])
        self.assertEqual(containers,{})
        self.assertEqual(result['immutable_hold'],'NOT_BOOTABLE' if 'immutable_hold' in result else r45.HOLD)
        self.assertFalse(any(a[0] in ('run','commit','import','pull','build') for a in captured_commands))
        self.assertEqual(len([a for a in captured_commands if a[:2]==['start','--attach']]),4)
        self.assertEqual(len([a for a in captured_commands if a[:2]==['rm','-f']]),6)

if __name__ == '__main__':
    unittest.main()
