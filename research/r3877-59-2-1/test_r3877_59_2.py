#!/usr/bin/env python3
"""R59.2 host-only synthetic tests. No Docker, QEMU, ARM execution or Kindle."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
import pw3_r3877_59_2_musl_needed_runtime as m

PASSBASE=dict(result=m.r591.PASS,arm_guest_execution_performed=True,
              all_created_containers_removed=True,original_image_unchanged=True,
              writable_fallback_used=True,diagnostic_control_output={
                'exit_code':0,'output_bytes':156,'allowlisted_program_markers':['R59_PASS_ARMV7_PTHREAD_TLS']},
              diagnostics={'base_result':'PASS_QEMU_SYSCALL_NAMES_AND_UNTRACED_APPLET_CONTROLS_ONLY'},
              r59_result=m.r59.PASS)

class OfflineTests(unittest.TestCase):
    def test_01_prior_digest(self):
        a=m.check_prior_error_fingerprint()
        self.assertEqual(a['unresolved_symbol_count'],9)
        self.assertEqual(a['matched_prior_output_bytes'],740)
    def test_02_exact_sha(self):
        self.assertEqual(hashlib.sha256(m.reconstructed_relocation_error()).hexdigest(),m.OBSERVED_ERROR_SHA)
    def test_03_prior_text_count(self):
        self.assertEqual(len(m.reconstructed_relocation_error().splitlines()),9)
    def test_04_no_raw_output_in_report(self):
        self.assertNotIn('raw_guest_output',m.check_prior_error_fingerprint())
    def test_05_prior_digest_mutated_hold(self):
        with patch.object(m,'OBSERVED_ERROR_SHA','0'*64):
            with self.assertRaisesRegex(m.Hold,'FINGERPRINT_CHANGED'):m.check_prior_error_fingerprint()
    def test_06_prior_length_mutated_hold(self):
        with patch.object(m,'OBSERVED_ERROR_BYTES',739):
            with self.assertRaisesRegex(m.Hold,'FINGERPRINT_CHANGED'):m.check_prior_error_fingerprint()
    def test_07_linked_elf_positive(self):
        x=m.validate_elf_dependency(m.NEW_PROBE)
        self.assertEqual(x['dt_needed'],['libc.so'])
        self.assertTrue(x['pt_tls_present'])
    def test_08_pinned_sha(self):
        self.assertEqual(m.file_sha(m.NEW_PROBE),m.NEW_SHA)
    def test_09_old_has_no_needed(self):
        # Do not depend on GNU readelf: macOS Command Line Tools omit it.
        # Fail closed on a malformed ELF, missing dynamic section, or any
        # DT_NEEDED tag rather than skipping assertions after a tool error.
        self.assertNotIn(1, self.elf_dynamic_tags(m.r59.PROBE))

    @staticmethod
    def elf_dynamic_tags(path):
        b=Path(path).read_bytes()
        if len(b)<52 or b[:7]!=b'\x7fELF\x01\x01\x01':
            raise AssertionError('ELF32_LE_HEADER_INVALID')
        phoff=struct.unpack_from('<I',b,28)[0]
        phentsize,phnum=struct.unpack_from('<HH',b,42)
        if phentsize!=32 or not 1<=phnum<=128 or phoff<52 or phoff+phentsize*phnum>len(b):
            raise AssertionError('ELF32_PROGRAM_HEADERS_INVALID')
        dynamic=[]
        for i in range(phnum):
            off=phoff+i*phentsize
            kind,fileoff,_,_,filesz,_=struct.unpack_from('<IIIIII',b,off)
            if kind==2:
                if not 8<=filesz<=4096 or filesz%8 or fileoff+filesz>len(b):
                    raise AssertionError('ELF_DYNAMIC_SEGMENT_INVALID')
                dynamic.append((fileoff,filesz))
        if len(dynamic)!=1:
            raise AssertionError('ELF_DYNAMIC_SEGMENT_COUNT_INVALID')
        fileoff,filesz=dynamic[0]
        tags=[]
        for pos in range(fileoff,fileoff+filesz,8):
            tag,_=struct.unpack_from('<II',b,pos)
            tags.append(tag)
            if tag==0:break
        if not tags or tags[-1]!=0:
            raise AssertionError('ELF_DYNAMIC_NOT_TERMINATED')
        return tags

    def test_33_portable_dynamic_tags_old_vs_new(self):
        self.assertNotIn(1,self.elf_dynamic_tags(m.r59.PROBE))
        self.assertEqual(self.elf_dynamic_tags(m.NEW_PROBE).count(1),1)

    def test_34_elf_parser_rejects_corrupt_header(self):
        with tempfile.TemporaryDirectory(prefix='r5921-') as d:
            p=Path(d)/'bad.elf'
            b=bytearray(m.r59.PROBE.read_bytes());b[0]=0
            p.write_bytes(b)
            with self.assertRaisesRegex(AssertionError,'ELF32_LE_HEADER_INVALID'):
                self.elf_dynamic_tags(p)

    def test_35_elf_check_does_not_use_external_commands(self):
        import subprocess
        with patch.object(subprocess,'run',side_effect=AssertionError('external tool invoked')):
            self.test_09_old_has_no_needed()
    def test_10_old_and_new_are_distinct(self):
        self.assertNotEqual(m.file_sha(m.NEW_PROBE),m.file_sha(m.r59.PROBE))
    def test_11_wrong_sha_hold(self):
        with patch.object(m,'NEW_SHA','0'*64):
            with self.assertRaisesRegex(m.Hold,'SHA256_MISMATCH'):m.validate_elf_dependency(m.NEW_PROBE)
    def test_12_symlink_rejected(self):
        with tempfile.TemporaryDirectory(prefix='r592-') as d:
            p=Path(d)/'linked.elf'
            p.symlink_to(m.NEW_PROBE)
            with self.assertRaisesRegex(m.Hold,'SYMLINK'):m.file_sha(p)
    def test_13_missing_rejected(self):
        with self.assertRaisesRegex(m.Hold,'LOCAL_FILE_MISSING'):m.file_sha('/does-not-exist-r592')
    def test_14_empty_rejected(self):
        with tempfile.TemporaryDirectory(prefix='r592-') as d:
            p=Path(d)/'empty';p.write_bytes(b'')
            with self.assertRaisesRegex(m.Hold,'OVERSIZE'):m.file_sha(p)
    def test_15_header_tamper_hold(self):
        with tempfile.TemporaryDirectory(prefix='r592-') as d:
            p=Path(d)/'x.elf';b=bytearray(m.NEW_PROBE.read_bytes());b[0]=0;p.write_bytes(b)
            with patch.object(m,'NEW_SHA',m.file_sha(p)):
                with self.assertRaisesRegex(m.Hold,'HEADER_INVALID'):m.validate_elf_dependency(p)
    def test_16_no_needed_hold(self):
        with tempfile.TemporaryDirectory(prefix='r592-') as d:
            p=Path(d)/'x.elf';b=bytearray(m.NEW_PROBE.read_bytes())
            phoff=struct.unpack_from('<I',b,28)[0];n=struct.unpack_from('<H',b,44)[0]
            for i in range(n):
                at=phoff+i*32
                if struct.unpack_from('<I',b,at)[0]==2:
                    off=struct.unpack_from('<I',b,at+4)[0]
                    for pos in range(off,off+struct.unpack_from('<I',b,at+16)[0],8):
                        if struct.unpack_from('<I',b,pos)[0]==1:
                            struct.pack_into('<I',b,pos,14);break
                    break
            p.write_bytes(b)
            with patch.object(m,'NEW_SHA',m.file_sha(p)):
                with self.assertRaisesRegex(m.Hold,'NEEDED_COUNT'):m.validate_elf_dependency(p)
    def test_17_wrong_needed_name_hold(self):
        with tempfile.TemporaryDirectory(prefix='r592-') as d:
            p=Path(d)/'x.elf';b=m.NEW_PROBE.read_bytes().replace(b'libc.so\0',b'evil.so\0')
            self.assertNotEqual(b,m.NEW_PROBE.read_bytes());p.write_bytes(b)
            with patch.object(m,'NEW_SHA',m.file_sha(p)):
                with self.assertRaisesRegex(m.Hold,'NEEDED_NOT_MUSL_LIBC'):m.validate_elf_dependency(p)
    def test_18_invalid_flag_hold(self):
        with tempfile.TemporaryDirectory(prefix='r592-') as d:
            p=Path(d)/'x.elf';b=bytearray(m.NEW_PROBE.read_bytes());struct.pack_into('<I',b,36,0);p.write_bytes(b)
            with patch.object(m,'NEW_SHA',m.file_sha(p)):
                with self.assertRaisesRegex(m.Hold,'EABI_HARDFLOAT'):m.validate_elf_dependency(p)
    def test_19_original_sha_expected(self):
        self.assertEqual(m.file_sha(m.r59.PROBE),m.ORIGINAL_SHA)
    def test_20_safe_preflight(self):
        r=m.preflight();self.assertFalse(r['docker_used']);self.assertEqual(r['immutable_hold'],'NOT_BOOTABLE')
    def test_21_zero_docker_default(self):
        with patch.object(m.r59.r49,'docker',side_effect=AssertionError('Docker invoked')):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main([]),2)
        self.assertEqual(json.loads(out.getvalue())['result'],'HOLD')
    def test_22_writable_alone_refuses(self):
        with patch.object(m.r59.r49,'docker',side_effect=AssertionError('Docker invoked')):
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(m.main(['--allow-disposable-writable-layer']),2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'WRITABLE_OPT_IN_REQUIRES_QEMU_AUTHORIZATION')
    def test_23_explicit_auth_routes(self):
        with patch.object(m,'run',return_value={'result':m.PASS}) as fn:
            with redirect_stdout(io.StringIO()):self.assertEqual(m.main(['--authorize-offline-qemu']),0)
            fn.assert_called_once_with(False)
    def test_24_writable_auth_routes(self):
        with patch.object(m,'run',return_value={'result':m.PASS}) as fn:
            with redirect_stdout(io.StringIO()):self.assertEqual(m.main(['--authorize-offline-qemu','--allow-disposable-writable-layer']),0)
            fn.assert_called_once_with(True)
    def test_25_mocked_qemu_pass_narrow(self):
        with patch.object(m.r591,'execute',return_value=PASSBASE) as fn:
            r=m.run(True)
        self.assertEqual(r['result'],m.PASS)
        self.assertTrue(r['pthread_and_tls_runtime_under_qemu_verified'])
        self.assertNotIn('no_changes_to_pinned_arm_elf',r)
        self.assertEqual(m.r59.PROBE,m.r59.Path(m.r59.__file__).resolve().parent/'pw3_r3877_59_armv7_probe.elf')
        fn.assert_called_once_with(True)
    def test_26_missing_cleanup_is_hold(self):
        bad=dict(PASSBASE,all_created_containers_removed=False)
        with patch.object(m.r591,'execute',return_value=bad):r=m.run(True)
        self.assertEqual(r['result'],'HOLD')
    def test_27_missing_original_image_is_hold(self):
        bad=dict(PASSBASE,original_image_unchanged=False)
        with patch.object(m.r591,'execute',return_value=bad):r=m.run(True)
        self.assertEqual(r['result'],'HOLD')
    def test_28_missing_arm_exec_is_hold(self):
        bad=dict(PASSBASE,arm_guest_execution_performed=False)
        with patch.object(m.r591,'execute',return_value=bad):r=m.run(True)
        self.assertEqual(r['result'],'HOLD')
    def test_29_underlying_failed_output_retained(self):
        bad=dict(PASSBASE,result='HOLD',diagnostic_control_output={'exit_code':127,'output_sha256':'1'*64,'unrecognized_line_count':1})
        with patch.object(m.r591,'execute',return_value=bad):r=m.run(True)
        self.assertEqual(r['result'],'HOLD');self.assertEqual(r['diagnostic_control_output']['exit_code'],127)
    def test_30_underlying_exceptions_hold(self):
        with patch.object(m.r591,'execute',side_effect=ValueError('SYNTHETIC_HOLD')):
            r=m.run(True)
        self.assertEqual(r['result'],'HOLD');self.assertEqual(r['hold_category'],'SYNTHETIC_HOLD')
    def test_31_no_kindle_proof(self):
        r=m.preflight();self.assertFalse(r['actual_vendor_kernel_compatibility_verified']);self.assertFalse(r['recovery_verified'])
    def test_32_pinned_artifact_not_modified(self):
        before=m.file_sha(m.r59.PROBE)
        with patch.object(m.r591,'execute',return_value=PASSBASE):m.run(True)
        self.assertEqual(m.file_sha(m.r59.PROBE),before)

if __name__=='__main__':unittest.main()
