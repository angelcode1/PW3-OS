"""R54 tests: no Docker/Kindle/network/ARM invocation. Synthetic ELF32 bytes only."""
import contextlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

import pw3_r3877_54_busybox_entropy_elf_audit as a


def fake_elf(imports=('getrandom','read'), has_dynsym=True):
    """Tiny, bounded synthetic ELF32 ARM section table. Not executable."""
    b=bytearray(1024)
    b[:7]=b'\x7fELF\x01\x01\x01'
    struct.pack_into('<HHI',b,16,2,40,1)
    struct.pack_into('<I',b,32,128)
    struct.pack_into('<HH',b,46,40,3 if has_dynsym else 2)
    strtab=b'\0'+b''.join(x.encode()+b'\0' for x in imports)
    b[512:512+len(strtab)]=strtab
    struct.pack_into('<I',b,128+40+4,3)
    struct.pack_into('<II',b,128+40+16,512,len(strtab))
    if has_dynsym:
        offset=600
        st=1
        for j,name in enumerate(imports):
            struct.pack_into('<I',b,offset+(j+1)*16,st)
            st+=len(name)+1
            struct.pack_into('<H',b,offset+(j+1)*16+14,0)
        n=len(imports)+1
        base=128+40*2
        struct.pack_into('<I',b,base+4,11)
        struct.pack_into('<IIII',b,base+16,600,16*n,1,0)
        struct.pack_into('<I',b,base+36,16)
    return bytes(b)


class R54Tests(unittest.TestCase):
    def test_01_parse_undefined_symbols(self):
        self.assertEqual(a.elf32_dyn_undefined(fake_elf()),{'getrandom','read'})
    def test_02_empty_import_table(self):
        self.assertEqual(a.elf32_dyn_undefined(fake_elf(())),set())
    def test_03_missing_dynsym_hold(self):
        with self.assertRaisesRegex(a.AuditHold,'DYNAMIC_SYMBOL_TABLE_MISSING'):
            a.elf32_dyn_undefined(fake_elf(has_dynsym=False))
    def test_04_wrong_machine_hold(self):
        b=bytearray(fake_elf());struct.pack_into('<H',b,18,62)
        with self.assertRaisesRegex(a.AuditHold,'ELF_NOT_ARM'):a.elf32_dyn_undefined(bytes(b))
    def test_05_small_elf_hold(self):
        with self.assertRaisesRegex(a.AuditHold,'ELF_INPUT_SIZE'):a.elf32_dyn_undefined(b'bad')
    def test_06_bad_magic_hold(self):
        b=bytearray(fake_elf());b[0]=0
        with self.assertRaisesRegex(a.AuditHold,'ELF32_LE_HEADER'):a.elf32_dyn_undefined(bytes(b))
    def test_07_shoff_zero_hold(self):
        b=bytearray(fake_elf());struct.pack_into('<I',b,32,0)
        with self.assertRaisesRegex(a.AuditHold,'SECTION_HEADERS_MISSING'):a.elf32_dyn_undefined(bytes(b))
    def test_08_shnum_oversized_hold(self):
        b=bytearray(fake_elf());struct.pack_into('<H',b,48,4097)
        with self.assertRaisesRegex(a.AuditHold,'SECTION_HEADERS_MISSING'):a.elf32_dyn_undefined(bytes(b))
    def test_09_shentsize_too_small_hold(self):
        b=bytearray(fake_elf());struct.pack_into('<H',b,46,39)
        with self.assertRaisesRegex(a.AuditHold,'SECTION_HEADERS_MISSING'):a.elf32_dyn_undefined(bytes(b))
    def test_10_shoff_exceeds_file_hold(self):
        b=bytearray(fake_elf());struct.pack_into('<I',b,32,1022)
        with self.assertRaisesRegex(a.AuditHold,'SECTION_HEADERS_OUT_OF_BOUNDS'):a.elf32_dyn_undefined(bytes(b))
    def test_11_section_oob_hold(self):
        b=bytearray(fake_elf());struct.pack_into('<I',b,128+40+16,1020)
        with self.assertRaisesRegex(a.AuditHold,'SECTION_OUT_OF_BOUNDS'):a.elf32_dyn_undefined(bytes(b))
    def test_12_bad_dynstr_link_hold(self):
        b=bytearray(fake_elf());struct.pack_into('<I',b,128+80+24,12)
        with self.assertRaisesRegex(a.AuditHold,'STRING_TABLE_LINK_INVALID'):a.elf32_dyn_undefined(bytes(b))
    def test_13_dynsym_wrong_stride_hold(self):
        b=bytearray(fake_elf());struct.pack_into('<I',b,128+80+36,8)
        with self.assertRaisesRegex(a.AuditHold,'SYMBOL_TABLE_SIZE_OR_STRIDE'):a.elf32_dyn_undefined(bytes(b))
    def test_14_dynsym_oversized_hold(self):
        b=bytearray(fake_elf());struct.pack_into('<I',b,128+80+20,10000)
        with self.assertRaisesRegex(a.AuditHold,'SECTION_OUT_OF_BOUNDS'):a.elf32_dyn_undefined(bytes(b))
    def test_15_missing_string_nul_hold(self):
        b=bytearray(fake_elf());b[512]=65
        with self.assertRaisesRegex(a.AuditHold,'DYNAMIC_STRING_TABLE_INVALID'):a.elf32_dyn_undefined(bytes(b))
    def test_16_name_oob_hold(self):
        b=bytearray(fake_elf());struct.pack_into('<I',b,600+16,10000)
        with self.assertRaisesRegex(a.AuditHold,'SYMBOL_NAME_OUT_OF_BOUNDS'):a.elf32_dyn_undefined(bytes(b))
    def test_17_name_unterminated_hold(self):
        b=bytearray(fake_elf());b[512+10:512+16]=b'xxxxxx'
        struct.pack_into('<I',b,128+40+20,16)
        with self.assertRaisesRegex(a.AuditHold,'SYMBOL_NAME_UNTERMINATED'):a.elf32_dyn_undefined(bytes(b))
    def test_18_ignore_defined_symbols(self):
        b=bytearray(fake_elf());struct.pack_into('<H',b,600+16+14,2)
        self.assertEqual(a.elf32_dyn_undefined(bytes(b)),{'read'})
    def test_19_reject_bad_symbol_chars(self):
        b=bytearray(fake_elf());b[513]=ord('$')
        with self.assertRaisesRegex(a.AuditHold,'SYMBOL_NAME_UNEXPECTED'):a.elf32_dyn_undefined(bytes(b))
    def test_20_no_docker_default(self):
        with mock.patch.object(a.baseline,'docker',side_effect=AssertionError('docker called')):
            f=io.StringIO()
            with contextlib.redirect_stdout(f):code=a.main([])
        self.assertEqual(code,2)
        data=json.loads(f.getvalue());self.assertEqual(data['result'],'HOLD');self.assertFalse(data['docker_used'])
    def test_21_only_loader_argument_hold(self):
        with contextlib.redirect_stdout(io.StringIO()) as f:
            code=a.main(['--loader','/missing'])
        self.assertEqual(code,2)
    def test_22_original_r48_source_pin_verified(self):
        a.require_baseline_code()
    def test_23_wrong_r48_source_pin_hold(self):
        with mock.patch.object(a,'EXPECTED_R48_SHA256','0'*64):
            with self.assertRaisesRegex(a.AuditHold,'BASELINE_CODE_SHA256_MISMATCH'):
                a.require_baseline_code()
    def test_24_no_input_does_not_prove_fallback(self):
        r=a.preflight();self.assertFalse(r['application_entropy_fallback_verified'])
        self.assertFalse(r['target_musl_linux_3_0_35_compatibility_verified'])
    def test_25_synthetic_binary_import_audit(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bb';q=Path(d)/'ld'
            p.write_bytes(fake_elf()+b'/dev/urandom\0')
            q.write_bytes(b'elfloader')
            with mock.patch.object(a.baseline,'validate_linkage',return_value={'pinned':True}):
                result=a.inspect_binary_pair(p,q)
        self.assertTrue(result['direct_getrandom_dynamic_import_present'])
        self.assertTrue(result['embedded_byte_marker_present']['/dev/urandom'])
        self.assertFalse(result['application_entropy_fallback_verified'])
    def test_26_no_import_is_not_no_syscall(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bb';q=Path(d)/'ld'
            p.write_bytes(fake_elf(()));q.write_bytes(b'fake')
            with mock.patch.object(a.baseline,'validate_linkage',return_value={'pinned':True}):
                r=a.inspect_binary_pair(p,q)
            self.assertFalse(r['direct_getrandom_dynamic_import_present'])
            self.assertTrue(r['no_dynamic_import_does_not_prove_no_syscall'])
    def test_27_bad_linkage_hold(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bb';q=Path(d)/'ld';p.write_bytes(fake_elf());q.write_bytes(b'fake')
            with mock.patch.object(a.baseline,'validate_linkage',side_effect=a.baseline.Hold('BAD_PIN')):
                r=a.run_files(p,q)
            self.assertEqual(r['result'],'HOLD');self.assertIn('R48_LINKAGE_HOLD',r['hold_category'])
    def test_28_success_scope(self):
        with mock.patch.object(a,'inspect_binary_pair',return_value={'application_entropy_fallback_verified':False}):
            r=a.run_files('x','y')
        self.assertEqual(r['result'],a.PASS);self.assertEqual(r['immutable_hold'],'NOT_BOOTABLE')
    def test_29_stopped_image_no_guest_start(self):
        calls=[]
        def dock(argv,**kw):
            calls.append(tuple(argv))
            if argv[0]=='create':return mock.Mock(stdout='a'*64,returncode=0,stderr='')
            if argv[:2]==['container','inspect'] and kw.get('allow_nonzero'):
                return mock.Mock(returncode=1,stderr='Error: No such container')
            return mock.Mock(stdout='',returncode=0,stderr='')
        with mock.patch.object(a.baseline,'docker',side_effect=dock), \
             mock.patch.object(a.baseline,'inspect_image'), \
             mock.patch.object(a.baseline,'inspect_stopped'), \
             mock.patch.object(a,'inspect_binary_pair',return_value={'application_entropy_fallback_verified':False}):
            result=a.run_stopped_image()
        self.assertEqual(result['result'],a.PASS)
        self.assertTrue(result['original_image_unchanged']);self.assertTrue(result['stopped_container_removed'])
        self.assertFalse(any(x[0]=='start' for x in calls))
        self.assertTrue(any(x[0]=='create' and '--network' in x and 'none' in x for x in calls))
        self.assertFalse(any(x[0]=='pull' for x in calls))
    def test_30_cleanup_failure_hold(self):
        def dock(argv,**kw):
            if argv[0]=='create':return mock.Mock(stdout='a'*64,returncode=0,stderr='')
            if argv[:2]==['rm','-f']:return mock.Mock(returncode=1,stderr='')
            if argv[:2]==['container','inspect'] and kw.get('allow_nonzero'):
                return mock.Mock(returncode=1,stderr='No such container')
            return mock.Mock(returncode=0,stdout='',stderr='')
        with mock.patch.object(a.baseline,'docker',side_effect=dock),\
             mock.patch.object(a.baseline,'inspect_image'),\
             mock.patch.object(a.baseline,'inspect_stopped'),\
             mock.patch.object(a,'inspect_binary_pair',return_value={'application_entropy_fallback_verified':False}):
            r=a.run_stopped_image()
        self.assertEqual(r['result'],'HOLD');self.assertEqual(r['hold_category'],'CLEANUP_OR_IMAGE_UNVERIFIED')
    def test_31_parent_image_reinspect_failure_hold(self):
        with mock.patch.object(a.baseline,'inspect_image',side_effect=[None,a.baseline.Hold('bad')]),\
             mock.patch.object(a.baseline,'docker',side_effect=lambda argv,**kw:mock.Mock(stdout='a'*64 if argv[0]=='create' else '',returncode=(1 if argv[:2]==['container','inspect'] and kw.get('allow_nonzero') else 0),stderr='No such container')),\
             mock.patch.object(a.baseline,'inspect_stopped'),\
             mock.patch.object(a,'inspect_binary_pair',return_value={'application_entropy_fallback_verified':False}):
            r=a.run_stopped_image()
        self.assertEqual(r['result'],'HOLD')
    def test_32_immutable_fields(self):
        r=a.preflight()
        for k in ('boot_performed','firmware_write_performed','arm_executable_launched','physical_device_access_performed','kindle_ssh_sessions','recovery_verified'):
            self.assertIn(k,r);self.assertFalse(r[k])

if __name__=='__main__':unittest.main()
