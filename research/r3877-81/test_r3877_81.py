"""R3877.81 host-only synthetic tests. No physical device I/O or ELF execution."""
import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import pw3_r3877_81_glibc_closure as m


def elf(*, etype=3, interp=None, needed=(), rpath=None, flags=0x05000200, machine=40):
    b=bytearray(2048)
    b[:16]=b'\x7fELF'+bytes([1,1,1,0])+bytes(8)
    phnum=3 if interp else 2
    struct.pack_into('<HHIIIIIHHHHHH',b,16,etype,machine,1,0x1000,52,0,flags,52,32,phnum,0,0,0)
    struct.pack_into('<8I',b,52,1,0,0x1000,0,len(b),len(b),5,0x1000)
    tags=[]; strings=b'\x00'
    for s in needed:
        tags.append((1,len(strings)))
        strings+=s.encode()+b'\x00'
    if rpath is not None:
        tags.append((15,len(strings)))
        strings+=rpath.encode()+b'\x00'
    tags=[(5,0x1200),(10,len(strings))]+tags+[(0,0)]
    for i,(tag,value) in enumerate(tags):
        struct.pack_into('<II',b,0x180+i*8,tag,value)
    struct.pack_into('<8I',b,84,2,0x180,0x1180,0,8*len(tags),8*len(tags),4,4)
    b[0x200:0x200+len(strings)]=strings
    if interp:
        interp_b=interp.encode()+b'\x00'
        struct.pack_into('<8I',b,116,3,0x300,0x1300,0,len(interp_b),len(interp_b),4,1)
        b[0x300:0x300+len(interp_b)]=interp_b
    return bytes(b)


def stage(root,*, rpath='$ORIGIN/../lib', needed=('libc.so.6','libm.so.6'), dup=False, missing=False, provider_hard=False):
    app=root/'opt/koreader-compat/app'
    app.mkdir(parents=True)
    (app/'luajit').write_bytes(elf(etype=2,interp='/lib/ld-linux.so.3',needed=needed,rpath=rpath))
    lib=root/'opt/koreader-compat/lib'
    lib.mkdir(parents=True)
    (lib/'libc.so.6').write_bytes(elf(needed=('ld-linux.so.3',)))
    if not missing:
        (lib/'libm.so.6').write_bytes(elf(needed=('libc.so.6',),flags=0x05000400 if provider_hard else 0x05000200))
    if dup:
        p=root/'lib'
        p.mkdir()
        (p/'libc.so.6').write_bytes(elf())
    l=root/'lib'
    l.mkdir(exist_ok=True)
    (l/'ld-linux.so.3').write_bytes(elf())
    return root


class TestR387781(unittest.TestCase):
    def test_01_elf_soft_eabi(self):
        x=m.parse_elf(elf(etype=2,interp='/lib/ld-linux.so.3',needed=('libc.so.6',)))
        self.assertEqual(x['float_flag'],'soft')
        self.assertEqual(x['needed'],['libc.so.6'])
        self.assertEqual(x['interpreter'],'/lib/ld-linux.so.3')

    def test_02_rpath_origin(self):
        self.assertEqual(m.classify_path('$ORIGIN/../lib'),'ORIGIN_RELATIVE_REVIEW_NEEDED')

    def test_03_rpath_absolute_held(self):
        self.assertEqual(m.classify_path('/opt/koreader/lib'),'ABSOLUTE_DEVICE_PATH_NOT_RELOCATABLE')

    def test_04_rpath_empty_element(self):
        self.assertEqual(m.classify_path('$ORIGIN/lib:'),'EMPTY_PATH_ELEMENT_HOLD')

    def test_05_hard_float_contradiction(self):
        with self.assertRaises(m.Refused):
            m.parse_elf(elf(flags=0x05000600))

    def test_06_nonarm_rejected(self):
        with self.assertRaises(m.Refused):
            m.parse_elf(elf(machine=62))

    def test_07_minimal_transitive_closure(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.audit(stage(Path(d)/'stage'))
        self.assertEqual([x['name'] for x in r['provider_list']],['ld-linux.so.3','libc.so.6','libm.so.6'])
        self.assertTrue(r['all_needed_names_unique_regular'])
        self.assertFalse(r['dynamic_loader_resolution_verified'])
        self.assertEqual(r['entrypoint_float_flag'],'soft')

    def test_08_duplicate_provider_is_not_resolved(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.audit(stage(Path(d)/'stage',dup=True))
        self.assertIn('DUPLICATE_REGULAR_PROVIDERS',[x['category'] for x in r['unresolved_or_ambiguous']])
        self.assertFalse(r['all_needed_names_unique_regular'])

    def test_09_symlink_only_is_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            root=stage(Path(d)/'stage',missing=True)
            (root/'opt/koreader-compat/lib/libm.so.6').symlink_to('/usr/lib/libm.so.6')
            r=m.audit(root)
        self.assertIn('SYMLINK_ONLY_PROVIDER_NOT_FOLLOWED',[x['category'] for x in r['unresolved_or_ambiguous']])

    def test_10_provider_hard_float_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.audit(stage(Path(d)/'stage',provider_hard=True))
        self.assertIn('HARD_FLOAT_VS_SOFT_ENTRYPOINT',[x['category'] for x in r['unresolved_or_ambiguous']])

    def test_11_default_optin_required_no_file_scans(self):
        with patch.object(m,'audit',side_effect=AssertionError('must not access stage')):
            with contextlib.redirect_stdout(io.StringIO()) as f:
                self.assertEqual(m.main(['--stage','/no/stage']),2)
        self.assertEqual(json.loads(f.getvalue())['hold_category'],'HOST_ONLY_DEPENDENCY_AUDIT_NOT_AUTHORIZED')

    def test_12_full_pass_still_hold(self):
        with tempfile.TemporaryDirectory() as d:
            root=stage(Path(d)/'stage')
            with contextlib.redirect_stdout(io.StringIO()) as f:
                self.assertEqual(m.main(['--stage',str(root),'--acknowledge-host-only-glibc-dependency-audit']),2)
        j=json.loads(f.getvalue())
        self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')
        self.assertEqual(j['result'],'HOLD')
        self.assertFalse(j['review']['koreader_device_runtime_verified'])
        self.assertFalse(j['device_access_performed'])

    def test_13_stage_symlink_root_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=stage(Path(d)/'stage')
            alias=Path(d)/'alias'
            alias.symlink_to(root)
            with self.assertRaises(m.Refused):
                m.audit(alias)

    def test_14_no_private_absolute_paths_reported(self):
        with tempfile.TemporaryDirectory() as d:
            root=stage(Path(d)/'stage')
            with contextlib.redirect_stdout(io.StringIO()) as f:
                m.main(['--stage',str(root),'--acknowledge-host-only-glibc-dependency-audit'])
            self.assertNotIn(d,f.getvalue())

    def test_15_rpath_still_not_loader_verified(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.audit(stage(Path(d)/'stage',rpath='/wrong/absolute/lib'))
        self.assertEqual(r['entrypoint_rpath_categories'],['ABSOLUTE_DEVICE_PATH_NOT_RELOCATABLE'])
        self.assertFalse(r['dynamic_loader_resolution_verified'])

    def test_16_bad_dynamic_strings_rejected(self):
        b=bytearray(elf(needed=('libc.so.6',)))
        struct.pack_into('<II',b,0x180,5,0xffffffff)
        with self.assertRaises(m.Refused):
            m.parse_elf(bytes(b))

    def test_17_provider_unexpected_interp_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            root=stage(Path(d)/'stage')
            (root/'opt/koreader-compat/lib/libc.so.6').write_bytes(elf(interp='/lib/ld-linux.so.3'))
            r=m.audit(root)
        self.assertIn('SHARED_PROVIDER_HAS_INTERPRETER',[x['category'] for x in r['unresolved_or_ambiguous']])

    def test_18_no_dynamic_loader_or_version_approval(self):
        with tempfile.TemporaryDirectory() as d:
            r=m.audit(stage(Path(d)/'stage'))
        self.assertFalse(r['symbol_version_compatibility_verified'])
        self.assertFalse(r['arm_build_attributes_verified'])
        self.assertFalse(r['stage_identity_revalidated_against_R26'])

if __name__=='__main__':
    unittest.main()
