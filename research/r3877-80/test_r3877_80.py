"""R3877.80 synthetic host-only tests. No SSH, ELF execution, or network."""
import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import pw3_r3877_80_luajit_abi_audit as m


def make_elf(flags=0x05000200, dependencies=('libc.so.6','libm.so.6'), interp='/lib/ld-linux.so.3', machine=40, dynamic=True, rpath=False):
    b = bytearray(1024)
    b[:16] = b'\x7fELF' + bytes([1,1,1,0]) + bytes(8)
    struct.pack_into('<HHIIIIIHHHHHH', b, 16, 2, machine, 1, 0x1000, 52, 0, flags, 52, 32, 3, 0, 0, 0)
    struct.pack_into('<8I', b, 52, 1, 0x100, 0x1000, 0, 0x300, 0x300, 5, 0x1000)
    interp_bytes = interp.encode()+b'\x00'
    struct.pack_into('<8I', b, 84, 3, 0x140, 0x1040, 0, len(interp_bytes), len(interp_bytes), 4, 1)
    b[0x140:0x140+len(interp_bytes)] = interp_bytes
    strtab = b'\x00'
    offsets=[]
    for dep in dependencies:
        offsets.append(len(strtab))
        strtab += dep.encode()+b'\x00'
    struct.pack_into('<8I', b, 116, 2 if dynamic else 0, 0x180, 0x1080, 0, 0x80, 0x80, 4, 4)
    b[0x1c0:0x1c0+len(strtab)] = strtab
    pairs = [(5,0x10c0),(10,len(strtab))] + [(1,x) for x in offsets]
    if rpath:
        pairs.append((15,0))
    pairs.append((0,0))
    for i,pair in enumerate(pairs):
        struct.pack_into('<II',b,0x180+i*8,*pair)
    return bytes(b)


def stage(root, blob=None):
    app=root/'opt/koreader-compat/app'
    app.mkdir(parents=True)
    (app/'luajit').write_bytes(blob or make_elf())
    lib=root/'opt/koreader-compat/lib'
    lib.mkdir()
    (lib/'libc.so.6').write_bytes(b'testing')
    (lib/'libm.so.6').symlink_to('/something-outside')
    (root/'lib').mkdir()
    (root/'lib/ld-linux.so.3').write_bytes(b'loader')
    return root

class Tests(unittest.TestCase):
    def test_01_arm_soft_flag(self):
        r=m.parse_luajit(make_elf())
        self.assertEqual(r['arm_float_header_flag'],'soft')
        self.assertEqual(r['arm_e_flags_hex'],'0x05000200')
        self.assertEqual(r['needed'],['libc.so.6','libm.so.6'])
        self.assertFalse(r['full_dependency_closure_verified'])

    def test_02_unspecified_float_not_hard(self):
        r=m.parse_luajit(make_elf(flags=0x05000000))
        self.assertEqual(r['arm_float_header_flag'],'unspecified')
        self.assertFalse(r['arm_attributes_vfp_calling_convention_decoded'])

    def test_03_hard_float_only_when_bit_set(self):
        self.assertEqual(m.parse_luajit(make_elf(flags=0x05000400))['arm_float_header_flag'],'hard')

    def test_04_conflicting_float_rejected(self):
        with self.assertRaises(m.Refused):m.parse_luajit(make_elf(flags=0x05000600))

    def test_05_nonarm_rejected(self):
        with self.assertRaises(m.Refused):m.parse_luajit(make_elf(machine=62))

    def test_06_no_dynamic_rejected(self):
        with self.assertRaises(m.Refused):m.parse_luajit(make_elf(dynamic=False))

    def test_07_interpreter_unapproved_rejected(self):
        with self.assertRaises(m.Refused):m.parse_luajit(make_elf(interp='/usr/lib/odd.so'))

    def test_08_missing_needed_rejected(self):
        with self.assertRaises(m.Refused):m.parse_luajit(make_elf(dependencies=()))

    def test_09_rpath_hidden(self):
        r=m.parse_luajit(make_elf(rpath=True))
        self.assertTrue(r['has_rpath'])
        self.assertNotIn('rpath_value',r)

    def test_10_default_no_optin_no_scan(self):
        with patch.object(m,'_safe_stage',side_effect=AssertionError('scan not allowed')):
            with contextlib.redirect_stdout(io.StringIO()) as o:
                self.assertEqual(m.main(['--stage','/not-a-path']),2)
        r=json.loads(o.getvalue());self.assertEqual(r['hold_category'],'HOST_ONLY_ELF_AUDIT_NOT_AUTHORIZED')

    def test_11_stage_provider_counts_symlinks_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            p=stage(Path(d)/'root')
            c=m.provider_counts(p,['libc.so.6','libm.so.6'],'/lib/ld-linux.so.3')
            self.assertEqual(c['stage_regular_file_count'],3)
            info={x['object_name']:x for x in c['candidates']}
            self.assertEqual(info['libm.so.6']['regular_name_matches'],0)
            self.assertEqual(info['libm.so.6']['symlink_name_matches_not_followed'],1)
            self.assertFalse(info['libm.so.6']['runtime_loader_resolution_verified'])

    def test_12_target_parent_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'root';root.mkdir();(root/'opt').symlink_to('/etc')
            with self.assertRaises(m.Refused):m._safe_stage(str(root))

    def test_13_full_pass_still_hold(self):
        with tempfile.TemporaryDirectory() as d:
            root=stage(Path(d)/'root')
            with contextlib.redirect_stdout(io.StringIO()) as o:
                code=m.main(['--stage',str(root),'--acknowledge-host-only-elf-audit'])
            j=json.loads(o.getvalue())
            self.assertEqual(code,2)
            self.assertEqual(j['result'],'HOLD')
            self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')
            self.assertEqual(j['review']['luajit']['needed'],['libc.so.6','libm.so.6'])
            self.assertFalse(j['koreader_device_runtime_verified'])

    def test_14_symlink_target_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=stage(Path(d)/'root');p=root/'opt/koreader-compat/app/luajit'
            p.unlink();p.symlink_to('/bin/sh')
            with self.assertRaises(m.Refused):m._safe_stage(str(root))

    def test_15_malformed_elf_still_hold(self):
        with tempfile.TemporaryDirectory() as d:
            root=stage(Path(d)/'root',b'not-elf')
            with contextlib.redirect_stdout(io.StringIO()) as o:
                self.assertEqual(m.main(['--stage',str(root),'--acknowledge-host-only-elf-audit']),2)
            j=json.loads(o.getvalue());self.assertNotIn('review',j)

    def test_16_no_private_absolute_paths_in_result(self):
        with tempfile.TemporaryDirectory() as d:
            root=stage(Path(d)/'root')
            with contextlib.redirect_stdout(io.StringIO()) as o:
                m.main(['--stage',str(root),'--acknowledge-host-only-elf-audit'])
            self.assertNotIn(d,o.getvalue())

if __name__ == '__main__':unittest.main()
