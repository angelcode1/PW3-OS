#!/usr/bin/env python3
"""All tests are host-only; synthetic ELF / simulated Docker; never run Docker."""
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('r48', Path(__file__).with_name('pw3_r3877_48_musl_interp_audit.py'))
r48 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r48)


def make_elf(interp=None, *, dynamic=True, eflags=0x05000400, etype=3, machine=40, truncate=False):
    b = bytearray(512)
    b[:16] = b'\x7fELF\x01\x01\x01' + b'\x00' * 9
    struct.pack_into('<HHI', b, 16, etype, machine, 1)
    struct.pack_into('<I', b, 28, 52)
    struct.pack_into('<I', b, 36, eflags)
    structs = [(1, 0, 0)]
    if dynamic: structs.append((2, 400, 20))
    if interp is not None:
        raw = interp.encode() + b'\x00'
        b[300:300 + len(raw)] = raw
        structs.append((3, 300, len(raw)))
    struct.pack_into('<HH', b, 42, 32, len(structs))
    for i, (kind, offset, length) in enumerate(structs):
        ph = 52 + i * 32
        struct.pack_into('<II', b, ph, kind, offset)
        struct.pack_into('<I', b, ph + 16, length)
    if truncate: b = b[:30]
    return bytes(b)


class R48Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name) / 'probe'

    def save(self, raw):
        self.p.write_bytes(raw)
        return self.p

    def assert_hold(self, raw, name):
        with self.assertRaisesRegex(r48.Hold, name):
            r48.elf32_arm(self.save(raw))

    def test_preflight_zero_docker(self):
        with patch.object(r48, 'docker', side_effect=AssertionError('Docker called')):
            s = io.StringIO()
            with redirect_stdout(s):
                self.assertEqual(r48.main([]), 2)
            d = json.loads(s.getvalue())
            self.assertEqual(d['result'], 'HOLD')
            self.assertEqual(d['immutable_hold'], 'NOT_BOOTABLE')

    def test_host_only_no_execution_sources(self):
        s = Path(r48.__file__).read_text()
        for x in ("['start'", "['run'", "['commit'", "['build'", "['import'", "['prune'", "['pull'", "['exec'", "--privileged", "--volume", "--mount"):
            self.assertNotIn(x, s)

    def test_valid_busybox(self):
        d = r48.elf32_arm(self.save(make_elf(r48.INTERP)))
        self.assertEqual(d['pt_interp'], r48.INTERP)
        self.assertTrue(d['pt_dynamic_present'])
        self.assertEqual(d['pt_load_count'], 1)

    def test_valid_loader(self):
        d = r48.elf32_arm(self.save(make_elf()))
        self.assertIsNone(d['pt_interp'])
        self.assertEqual(d['type'], 'ET_DYN')

    def test_missing_interpreter_is_not_dynamic_proof(self):
        p = self.save(make_elf())
        with patch.object(r48, 'digest', side_effect=[r48.BUSYBOX_SHA256, r48.LOADER_SHA256]):
            with self.assertRaisesRegex(r48.Hold, 'NO_PT_INTERP'):
                r48.validate_linkage(p, p)

    def test_missing_pt_dynamic_denied(self):
        a = Path(self.tmp.name) / 'a'
        b = Path(self.tmp.name) / 'b'
        a.write_bytes(make_elf(r48.INTERP, dynamic=False))
        b.write_bytes(make_elf())
        with patch.object(r48, 'digest', side_effect=[r48.BUSYBOX_SHA256, r48.LOADER_SHA256]):
            with self.assertRaisesRegex(r48.Hold, 'PT_DYNAMIC_ABSENT'):
                r48.validate_linkage(a, b)

    def test_valid_linkage_proof(self):
        a = Path(self.tmp.name) / 'a'
        b = Path(self.tmp.name) / 'b'
        a.write_bytes(make_elf(r48.INTERP))
        b.write_bytes(make_elf())
        with patch.object(r48, 'digest', side_effect=[r48.BUSYBOX_SHA256, r48.LOADER_SHA256]):
            r = r48.validate_linkage(a, b)
        self.assertTrue(r['interpreter_path_matches_pinned_loader'])

    def test_wrong_interp_denied(self):
        p = Path(self.tmp.name) / 'bad'
        p.write_bytes(make_elf('/lib/ld-other.so.1'))
        q = Path(self.tmp.name) / 'ld'
        q.write_bytes(make_elf())
        with patch.object(r48, 'digest', side_effect=[r48.BUSYBOX_SHA256, r48.LOADER_SHA256]):
            with self.assertRaisesRegex(r48.Hold, 'PT_INTERP_UNEXPECTED'):
                r48.validate_linkage(p, q)

    def test_wrong_loader_hash_denied(self):
        p = Path(self.tmp.name) / 'bb'
        q = Path(self.tmp.name) / 'ld'
        p.write_bytes(make_elf(r48.INTERP)); q.write_bytes(make_elf())
        with patch.object(r48, 'digest', side_effect=[r48.BUSYBOX_SHA256, '0' * 64]):
            with self.assertRaisesRegex(r48.Hold, 'LOADER_BYTES'):
                r48.validate_linkage(p, q)

    def test_wrong_busybox_hash_denied(self):
        p = Path(self.tmp.name) / 'bb'
        q = Path(self.tmp.name) / 'ld'
        p.write_bytes(make_elf(r48.INTERP)); q.write_bytes(make_elf())
        with patch.object(r48, 'digest', side_effect=['0' * 64]):
            with self.assertRaisesRegex(r48.Hold, 'BUSYBOX_BYTES'):
                r48.validate_linkage(p, q)

    def test_loader_itself_interpreted_denied(self):
        a = Path(self.tmp.name) / 'bb'
        b = Path(self.tmp.name) / 'ld'
        a.write_bytes(make_elf(r48.INTERP)); b.write_bytes(make_elf(r48.INTERP))
        with patch.object(r48, 'digest', side_effect=[r48.BUSYBOX_SHA256, r48.LOADER_SHA256]):
            with self.assertRaisesRegex(r48.Hold, 'MUSL_LOADER_ELF_UNEXPECTED'):
                r48.validate_linkage(a, b)

    def test_et_exec_loader_denied(self):
        a = Path(self.tmp.name) / 'bb'
        b = Path(self.tmp.name) / 'ld'
        a.write_bytes(make_elf(r48.INTERP)); b.write_bytes(make_elf(etype=2))
        with patch.object(r48, 'digest', side_effect=[r48.BUSYBOX_SHA256, r48.LOADER_SHA256]):
            with self.assertRaisesRegex(r48.Hold, 'MUSL_LOADER_ELF_UNEXPECTED'):
                r48.validate_linkage(a, b)

    def test_truncated_elf_denied(self):
        self.assert_hold(make_elf(truncate=True), 'ELF32_LE_HEADER_INVALID')

    def test_wrong_machine_denied(self):
        self.assert_hold(make_elf(machine=183), 'MACHINE_OR_TYPE')

    def test_wrong_float_abi_denied(self):
        self.assert_hold(make_elf(eflags=0x05000200), 'EABI_HARDFLOAT')

    def test_no_load_denied(self):
        b = bytearray(make_elf())
        struct.pack_into('<I', b, 52, 0)
        self.assert_hold(bytes(b), 'PROGRAM_HEADER_SEMANTICS')

    def test_bad_interpreter_without_terminator_denied(self):
        b = bytearray(make_elf(r48.INTERP))
        b[300+len(r48.INTERP)] = ord('Q')
        self.assert_hold(bytes(b), 'TERMINATION')

    def test_duplicate_interpreter_denied(self):
        b = bytearray(make_elf(r48.INTERP))
        struct.pack_into('<HH', b, 42, 32, 4)
        struct.pack_into('<II', b, 52+3*32, 3, 300)
        struct.pack_into('<I', b, 52+3*32+16, len(r48.INTERP)+1)
        self.assert_hold(bytes(b), 'SEMANTICS')

    def test_program_header_overflow_denied(self):
        b = bytearray(make_elf())
        struct.pack_into('<I', b, 28, 500)
        self.assert_hold(bytes(b), 'OUT_OF_BOUNDS')

    def test_unsafe_interp_denied(self):
        self.assert_hold(make_elf('/lib/../../something'), 'INTERPRETER_UNSAFE')

    def test_nonascii_interp_denied(self):
        b = bytearray(make_elf(r48.INTERP))
        b[305] = 255
        self.assert_hold(bytes(b), 'NONASCII')

    def test_symlink_host_input_denied(self):
        target = Path(self.tmp.name) / 'target'
        target.write_bytes(make_elf())
        self.p.symlink_to(target)
        with self.assertRaisesRegex(r48.Hold, 'ELF_UNSAFE'):
            r48.elf32_arm(self.p)

    def test_docker_error_redacted(self):
        with patch('subprocess.run', return_value=subprocess.CompletedProcess([],1,'','secret/path')):
            with self.assertRaisesRegex(r48.Hold,'DOCKER_COMMAND_FAILED:cp') as c:
                r48.docker(['cp','A','B'])
            self.assertNotIn('secret/path',str(c.exception))

    def test_unauthorized_arg_not_present(self):
        with patch.object(r48, 'run', return_value={'result':'HOLD'}) as mock_run:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r48.main(['--authorize-stopped-image-audit']),2)
            mock_run.assert_called_once_with()

    def test_inspect_image_rejects_wrong_id(self):
        with patch.object(r48, 'docker', return_value=subprocess.CompletedProcess([],0,json.dumps([{'Id':'sha256:'+'1'*64,'Os':'linux','Architecture':'arm','Variant':'v7'}]),'')):
            with self.assertRaisesRegex(r48.Hold,'PARENT_IMAGE_PIN'):
                r48.inspect_image()

    def test_inspect_container_rejects_privileged(self):
        js = {'Image':r48.PARENT_ID,'State':{'Status':'created','Running':False},'Path':'/bin/true',
              'HostConfig':{'NetworkMode':'none','Privileged':True,'Binds':None,'Devices':None,'DeviceRequests':None},'Mounts':[]}
        with patch.object(r48, 'docker', return_value=subprocess.CompletedProcess([],0,json.dumps([js]),'')):
            with self.assertRaisesRegex(r48.Hold,'ISOLATION_UNVERIFIED'):
                r48.inspect_stopped('1'*64)

    def test_cleanup_and_parent_check_success_simulated(self):
        containers = set()
        commands=[]
        cid = '3'*64
        def fake_docker(argv,*,allow_nonzero=False):
            a=list(argv);commands.append(a)
            if a[:2] == ['image','inspect']:
                payload=[{'Id':r48.PARENT_ID,'Os':'linux','Architecture':'arm','Variant':'v7'}]
                return subprocess.CompletedProcess(a,0,json.dumps(payload),'')
            if a[0] == 'create':
                containers.add(cid)
                return subprocess.CompletedProcess(a,0,cid+'\n','')
            if a[:2] == ['container','inspect']:
                if cid not in containers:
                    return subprocess.CompletedProcess(a,1,'','Error: No such container: '+cid)
                obj={'Image':r48.PARENT_ID,'Path':'/bin/true','State':{'Status':'created','Running':False},
                     'HostConfig':{'NetworkMode':'none','Privileged':False,'Binds':None,'Devices':None,'DeviceRequests':None},'Mounts':[]}
                return subprocess.CompletedProcess(a,0,json.dumps([obj]),'')
            if a[0] == 'cp':
                dest=Path(a[-1])
                dest.write_bytes(make_elf(r48.INTERP) if dest.name == 'busybox' else make_elf())
                return subprocess.CompletedProcess(a,0,'','')
            if a[:2] == ['rm','-f']:
                containers.remove(cid)
                return subprocess.CompletedProcess(a,0,cid,'')
            raise AssertionError(a)
        with patch.object(r48,'docker',side_effect=fake_docker),patch.object(r48,'digest',side_effect=[r48.BUSYBOX_SHA256,r48.LOADER_SHA256]):
            result=r48.run()
        self.assertEqual(result['result'],'PASS_PINNED_BUSYBOX_MUSL_PT_INTERP_LINKAGE_ONLY',result)
        self.assertTrue(result['original_image_unchanged'])
        self.assertTrue(result['stopped_container_removed'])
        self.assertFalse(result['arm_binary_execution_performed'])
        self.assertEqual(containers,set())
        self.assertFalse(any(a[0] in ('start','run','build','commit','exec','import','pull') for a in commands))


if __name__=='__main__':
    unittest.main()
