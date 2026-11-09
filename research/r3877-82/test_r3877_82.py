"""Synthetic-only checks: no Kindle connection, no native ELF execution."""
import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import pw3_r3877_82_version_abi_audit as a


def fake_elf(kind=3, interp=None, needed=(), rpath=None, flags=0x05000200):
    b=bytearray(2048)
    b[:16]=b'\x7fELF'+bytes([1,1,1,0])+bytes(8)
    nph=3 if interp else 2
    struct.pack_into('<HHIIIIIHHHHHH',b,16,kind,40,1,0x1000,52,0,flags,52,32,nph,0,0,0)
    struct.pack_into('<8I',b,52,1,0,0x1000,0,2048,2048,5,0x1000)
    strings=b'\x00'; tags=[]
    for dep in needed:
        tags.append((1,len(strings))); strings+=dep.encode()+b'\x00'
    if rpath is not None:
        tags.append((15,len(strings))); strings+=rpath.encode()+b'\x00'
    tags=[(5,0x1200),(10,len(strings))]+tags+[(0,0)]
    for i,t in enumerate(tags):struct.pack_into('<II',b,0x180+i*8,*t)
    struct.pack_into('<8I',b,84,2,0x180,0x1180,0,8*len(tags),8*len(tags),4,4)
    b[0x200:0x200+len(strings)]=strings
    if interp:
        v=interp.encode()+b'\0'
        struct.pack_into('<8I',b,116,3,0x300,0x1300,0,len(v),len(v),4,1)
        b[0x300:0x300+len(v)]=v
    return bytes(b)


def add_sections(base, required=None, provided=None, attr=None):
    names=b'\x00'; indices={}
    for n in ('.shstrtab','.dynstr','.gnu.version_r','.gnu.version_d','.ARM.attributes'):
        indices[n]=len(names);names+=n.encode()+b'\0'
    strs=b'\x00libc.so.6\x00GLIBC_2.4\x00'
    auxname=strs.index(b'GLIBC_2.4');libname=strs.index(b'libc.so.6')
    req=struct.pack('<HHIII',1,1,libname,16,0)+struct.pack('<IHHII',0,0,2,auxname,0)
    defs=struct.pack('<HHHHIII',1,0,2,1,0,20,0)+struct.pack('<II',auxname,0)
    if attr is not None:
        tag_file=b'\x01'+struct.pack('<I',7)+bytes([28,attr])
        vend=b'aeabi\0'
        arm=b'A'+struct.pack('<I',4+len(vend)+len(tag_file))+vend+tag_file
    else:arm=None
    chunks=[('.shstrtab',3,names,0),('.dynstr',3,strs,0)]
    if required is not None:chunks.append(('.gnu.version_r',a.VERNEED,req,2))
    if provided is not None:chunks.append(('.gnu.version_d',a.VERDEF,defs,2))
    if arm is not None:chunks.append(('.ARM.attributes',a.ARMATTR,arm,0))
    data=bytearray(base);headers=[(0,0,0,0,0,0,0,0,0,0)]
    for name, typ, body, link in chunks:
        pos=len(data);data.extend(body)
        headers.append((indices[name],typ,0,0,pos,len(body),link,0,1,0))
    off=len(data)
    for h in headers:data.extend(struct.pack('<10I',*h))
    struct.pack_into('<I',data,32,off)
    struct.pack_into('<H',data,46,40)
    struct.pack_into('<H',data,48,len(headers))
    struct.pack_into('<H',data,50,1)
    return bytes(data)


def fixture(root):
    app=root/'opt/koreader-compat/app';app.mkdir(parents=True)
    libs=root/'opt/koreader-compat/gnu/lib';libs.mkdir(parents=True)
    (app/'luajit').write_bytes(add_sections(fake_elf(kind=2,interp='/lib/ld-linux.so.3',needed=('libc.so.6',),rpath='$ORIGIN/../gnu/lib'),required=True,attr=0))
    (libs/'libc.so.6').write_bytes(add_sections(fake_elf(needed=('ld-linux.so.3',)),provided=True,attr=0))
    (libs/'ld-linux.so.3').write_bytes(add_sections(fake_elf(),attr=0))
    return root

class Tests(unittest.TestCase):
    def test_01_no_sections(self):self.assertEqual(a.metadata_sections(fake_elf()),[])
    def test_02_arm_base_aapcs(self):
        b=add_sections(fake_elf(),attr=0)
        self.assertEqual(a.arm_vfp_args(b,a.metadata_sections(b))['status'],'BASE_AAPCS')
    def test_03_arm_vfp_aapcs(self):
        b=add_sections(fake_elf(),attr=1)
        self.assertEqual(a.arm_vfp_args(b,a.metadata_sections(b))['tag_value'],1)
    def test_04_arm_compatible_aapcs(self):
        b=add_sections(fake_elf(),attr=3)
        self.assertEqual(a.arm_vfp_args(b,a.metadata_sections(b))['status'],'BOTH_COMPATIBLE')
    def test_05_arm_unknown_tag(self):
        b=add_sections(fake_elf(),attr=4)
        self.assertEqual(a.arm_vfp_args(b,a.metadata_sections(b))['status'],'UNKNOWN_VALUE')
    def test_06_need(self):
        b=add_sections(fake_elf(),required=True)
        self.assertEqual(a.parse_verneed(b,a.metadata_sections(b)),{'libc.so.6':['GLIBC_2.4']})
    def test_07_definition(self):
        b=add_sections(fake_elf(),provided=True)
        self.assertEqual(a.parse_verdef(b,a.metadata_sections(b)),['GLIBC_2.4'])
    def test_08_absent_versions_unverified(self):
        b=add_sections(fake_elf(),attr=0)
        self.assertIsNone(a.parse_verneed(b,a.metadata_sections(b)))
        self.assertIsNone(a.parse_verdef(b,a.metadata_sections(b)))
    def test_09_bounds_refused(self):
        b=bytearray(add_sections(fake_elf(),provided=True))
        struct.pack_into('<I',b,32,len(b)-2)
        with self.assertRaises(a.Refused):a.metadata_sections(bytes(b))
    def test_10_origin_gnu_dir_match(self):
        with tempfile.TemporaryDirectory() as d:
            p=fixture(Path(d)/'stage')
            self.assertEqual(a.origin_report(p,a.APP,['$ORIGIN/../gnu/lib']),['MATCHES_GNU_PROVIDER_DIRECTORY'])
    def test_11_origin_escape_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=fixture(Path(d)/'stage')
            self.assertEqual(a.origin_report(p,a.APP,['$ORIGIN/../../../../etc']),['RPATH_ESCAPES_APP_BUNDLE'])
    def test_12_origin_absolute_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=fixture(Path(d)/'stage')
            self.assertEqual(a.origin_report(p,a.APP,['/usr/lib']),['UNSAFE_OR_UNKNOWN_RPATH'])
    def test_13_integration_versions_named_not_runtime_proven(self):
        with tempfile.TemporaryDirectory() as d:
            root=fixture(Path(d)/'stage')
            r=a.inspect(root)
            self.assertTrue(r['objects']['luajit']['arm_vfp_args']['tag_value']==0)
            self.assertEqual(r['counts']['matched_versions'],1)
            self.assertFalse(r['loader_symbol_resolution_verified'])
            self.assertFalse(r['manual_one_shot_device_execution_authorized'])
    def test_14_default_optin_does_not_scan(self):
        with patch.object(a,'inspect',side_effect=AssertionError('should not scan')):
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                rc=a.main(['--stage','/not-here'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(buf.getvalue())['hold_category'],'HOST_ONLY_REVIEW_NOT_AUTHORIZED')
    def test_15_explicit_still_hold(self):
        with tempfile.TemporaryDirectory() as d:
            root=fixture(Path(d)/'stage')
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                rc=a.main(['--stage',str(root),'--acknowledge-mac-only-review'])
        self.assertEqual(rc,2)
        j=json.loads(buf.getvalue())
        self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(j['device_execution_performed'])
    def test_16_corrupted_version_strtab_link_refused(self):
        b=bytearray(add_sections(fake_elf(),required=True))
        sections=a.metadata_sections(bytes(b))
        v=next(s for s in sections if s['type']==a.VERNEED)
        # Set the actual verneed sh_link to an invalid section number.
        index=sections.index(v)
        shoff=a.u32(b,32)
        struct.pack_into('<I',b,shoff+index*40+24,0xffff)
        with self.assertRaises(a.Refused):
            a.parse_verneed(bytes(b),a.metadata_sections(bytes(b)))
    def test_17_no_private_mac_path(self):
        with tempfile.TemporaryDirectory() as d:
            root=fixture(Path(d)/'stage')
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                a.main(['--stage',str(root),'--acknowledge-mac-only-review'])
            self.assertNotIn(d,buf.getvalue())
    def test_18_soft_flag_allows_eabi_attribute_base(self):
        with tempfile.TemporaryDirectory() as d:
            root=fixture(Path(d)/'stage')
            j=a.inspect(root)
            self.assertFalse(j['arm_vfp_warnings'])

    def test_19_vfp_calling_convention_warning(self):
        with tempfile.TemporaryDirectory() as d:
            root=fixture(Path(d)/'stage')
            target=root/a.APP
            target.write_bytes(add_sections(fake_elf(kind=2,interp='/lib/ld-linux.so.3',needed=('libc.so.6',),rpath='$ORIGIN/../gnu/lib'),required=True,attr=1))
            result=a.inspect(root)
            self.assertIn('luajit',[x['object'] for x in result['arm_vfp_warnings']])

    def test_20_missing_required_version_remains_unproven(self):
        with tempfile.TemporaryDirectory() as d:
            root=fixture(Path(d)/'stage')
            (root/'opt/koreader-compat/gnu/lib/libc.so.6').write_bytes(add_sections(fake_elf(needed=('ld-linux.so.3',)),attr=0))
            result=a.inspect(root)
            self.assertEqual(result['counts']['versions_without_definition_table'],1)
            self.assertFalse(result['loader_symbol_resolution_verified'])

if __name__=='__main__':unittest.main()
