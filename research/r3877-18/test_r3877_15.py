import importlib.util
import io
import pathlib
import struct
import tarfile
import unittest
from unittest.mock import patch
p=pathlib.Path(__file__).with_name('pw3_r3877_15_koreader_elf_audit.py')
spec=importlib.util.spec_from_file_location('m',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def elf(needed=False, interp=False, floatflag=0x400):
    # Synthetic ELF32 ARM with PT_LOAD mapped dynstr and optional PT_DYNAMIC.
    blob=bytearray(0x300)
    blob[0:7]=b'\x7fELF\x01\x01\x01'
    struct.pack_into('<H',blob,16,3)
    struct.pack_into('<H',blob,18,40)
    struct.pack_into('<I',blob,28,52)
    struct.pack_into('<I',blob,36,0x05000000 | floatflag)
    struct.pack_into('<HH',blob,42,32,3 if interp else 2)
    struct.pack_into('<IIIIIIII',blob,52,1,0x100,0x1000,0,0x180,0x180,5,0x1000)
    if needed:
        struct.pack_into('<IIIIIIII',blob,84,2,0x120,0x1020,0,32,32,4,4)
        struct.pack_into('<II',blob,0x120,5,0x1100)
        struct.pack_into('<II',blob,0x128,10,32)
        struct.pack_into('<II',blob,0x130,1,1)
        struct.pack_into('<II',blob,0x138,0,0)
        blob[0x200:0x200+32]=b'\0libkoreader.so\0'+ b'\0'*(32-16)
    else:
        struct.pack_into('<IIIIIIII',blob,84,2,0x120,0x1020,0,8,8,4,4)
        struct.pack_into('<II',blob,0x120,0,0)
    if interp:
        struct.pack_into('<IIIIIIII',blob,116,3,0x280,0x1280,0,19,19,4,1)
        blob[0x280:0x293]=b'/lib/ld-linux.so.3\0'
    return bytes(blob)

def archive(files):
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w:') as t:
        for k,v in files.items():
            info=tarfile.TarInfo(k);info.size=len(v)
            t.addfile(info,io.BytesIO(v))
    return out.getvalue()

class Test(unittest.TestCase):
    def test_fixed_scope(self):
        self.assertIn('/mnt/us/koreader',m.TARGET_SCRIPT)
        self.assertNotIn('/mnt/us/documents',m.TARGET_SCRIPT)
        self.assertNotIn('chmod ',m.TARGET_SCRIPT)
        self.assertNotIn('mount ',m.TARGET_SCRIPT)
        self.assertNotIn('curl ',m.TARGET_SCRIPT)
    def test_name_accept(self):
        for a in ['luajit','fbink','libs/libc.so.6','libs/libmupdf.so']:
            self.assertTrue(m.safe_name(a),a)
    def test_name_reject(self):
        for a in ['/etc/passwd','../x','libs/../settings','settings.reader.lua','libs/bad name.so','libs/more/f.so','libs/foo.txt']:
            self.assertFalse(m.safe_name(a),a)
    def test_archive_valid(self):
        x=m.parse_archive(archive({'luajit':elf(), 'fbink':elf(), 'libs/libmupdf.so':elf()}))
        self.assertEqual(len(x),3)
    def test_archive_path_reject(self):
        with self.assertRaises(m.Hold):m.parse_archive(archive({'luajit':elf(),'fbink':elf(),'../foo':b'1'}))
    def test_archive_missing_binary(self):
        with self.assertRaises(m.Hold):m.parse_archive(archive({'luajit':elf()}))
    def test_elf32_arm(self):
        r=m.inspect_elf(elf())
        self.assertEqual(r['kind'],'ELF32_ARM')
        self.assertEqual(r['eabi_version'],5)
        self.assertEqual(r['float_abi'],'HARD')
    def test_elf_needed(self):
        r=m.inspect_elf(elf(True))
        self.assertEqual(r['needed'],['libkoreader.so'])
    def test_elf_interp(self):
        r=m.inspect_elf(elf(False,True))
        self.assertEqual(r['pt_interp'],'/lib/ld-linux.so.3')
    def test_elf_nonelf(self):
        self.assertEqual(m.inspect_elf(b'#!/bin/sh\n')['kind'],'NON_ELF')
    def test_elf_invalid(self):
        x=bytearray(elf());struct.pack_into('<I',x,28,0xfffffff0)
        with self.assertRaises(m.Hold):m.inspect_elf(x)
    def test_resolution(self):
        summary=m.summarize({'luajit':('file',elf(True)), 'fbink':('file',elf()),'libs/libkoreader.so':('file',elf())})
        r=next(z for z in summary['files'] if z['path']=='luajit')
        self.assertEqual(r['matching_names_in_collected_app_libs'],['libkoreader.so'])
    def test_authorization_preflight(self):
        with patch('sys.stdout',new_callable=io.StringIO) as cap:
            self.assertEqual(m.main([]),2)
            self.assertIn('EXPLICIT_READONLY_SSH_AUTHORIZATION_REQUIRED',cap.getvalue())
    def test_wrong_target_fails_without_ssh(self):
        with patch.object(m,'remote_tar',side_effect=AssertionError('should not execute')):
            with patch('sys.stdout',new_callable=io.StringIO) as cap:
                self.assertEqual(m.main(['--target','root@other','--authorize-live-readonly-ssh']),2)
                self.assertIn('UNEXPECTED_SSH_TARGET',cap.getvalue())
    def test_expected_success_mock(self):
        data=archive({'luajit':elf(),'fbink':elf(),'libs/libfoo.so':elf()})
        with patch.object(m,'remote_tar',return_value=data):
            with patch('sys.stdout',new_callable=io.StringIO) as cap:
                self.assertEqual(m.main(['--target',m.EXPECTED_TARGET,'--authorize-live-readonly-ssh']),0)
                self.assertIn('PASS_KOREADER_APP_ELF_METADATA_ONLY',cap.getvalue())

if __name__=='__main__':unittest.main()
