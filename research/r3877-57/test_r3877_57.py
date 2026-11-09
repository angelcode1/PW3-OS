#!/usr/bin/env python3
"""R3877.57 offline synthetic tests ONLY; no Docker, Kindle or ARM execution."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import pw3_r3877_57_elf_applet_names as mod

LIST=b'/bin/ash\n/bin/sh\n/usr/bin/awk\n/usr/bin/wget\n'
NAMES=[b'ash',b'awk',b'sh',b'wget']
PATTERN=b''.join(x+b'\0' for x in NAMES)+b'\0'
DB=b'P:busybox\nV:1.37.0-r31\nA:armv7\n\n'

# Valid synthetic ELF32 ARM ET_DYN with one PT_LOAD and optional inert overlay.
def elf_load(data=PATTERN, *, phnum=1, phentsize=32, machine=40, flags=0x05000400,
             offset=0x100, filesz=None, memsz=None, prepend=b'HEAD', overlay=b'', t=3):
    b=bytearray(b'\0'*max(0x100,offset))
    b[0:16]=b'\x7fELF\x01\x01\x01'+b'\0'*9
    struct.pack_into('<HHI',b,16,t,machine,1)
    struct.pack_into('<I',b,28,52)
    struct.pack_into('<I',b,36,flags)
    struct.pack_into('<HH',b,42,phentsize,phnum)
    if phnum and phentsize>=32:
        segment=prepend+data
        struct.pack_into('<IIIIIIII',b,52,1,offset,0x10000,0,len(segment) if filesz is None else filesz,
                     len(segment) if memsz is None else memsz,4,0x1000)
    if offset<=len(b):
        b.extend(prepend+data)
    b.extend(overlay)
    return bytes(b)

class R57Tests(unittest.TestCase):
    def setUp(self):
        self.patches=[patch.object(mod,'EXPECTED_COUNT',4),
                      patch.object(mod,'APPLET_EXPECTED_SHA256',hashlib.sha256(LIST).hexdigest())]
        for p in self.patches:p.start();self.addCleanup(p.stop)
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.dir=Path(self.tmp.name).resolve()
        self.paths={x:self.dir/x for x in ('installed','listing','busybox','loader')}
        self.paths['installed'].write_bytes(DB)
        self.paths['listing'].write_bytes(LIST)
        self.paths['busybox'].write_bytes(elf_load())
        self.paths['loader'].write_bytes(b'NO_ARM_CODE_EXECUTION')
    def assertHold(self,fn,msg):
        with self.assertRaises(mod.AuditHold) as e:fn()
        self.assertIn(msg,str(e.exception))
    def evidence(self,b=None,alist=LIST):return mod.applet_name_array_evidence(elf_load() if b is None else b,alist)
    def test_01_positive_synthetic_embedded(self):
        self.assertTrue(self.evidence()['exact_sorted_nul_separated_applet_name_array_in_elf_pt_load'])
    def test_02_matching_name_count(self):self.assertEqual(self.evidence()['matched_name_count'],4)
    def test_03_pattern_digest(self):
        self.assertEqual(self.evidence()['applet_names_array_sha256'],hashlib.sha256(PATTERN).hexdigest())
    def test_04_length(self):self.assertEqual(self.evidence()['applet_names_array_byte_length'],len(PATTERN))
    def test_05_runtime_not_proved(self):self.assertFalse(self.evidence()['applet_execution_verified'])
    def test_06_dispatch_not_proved(self):self.assertFalse(self.evidence()['actual_function_pointer_dispatch_table_verified'])
    def test_07_entropy_not_proved(self):self.assertFalse(self.evidence()['application_entropy_fallback_verified'])
    def test_08_reproducibility_not_proved(self):self.assertFalse(self.evidence()['binary_reproducibility_verified'])
    def test_09_absent_pattern_hold(self):
        self.assertHold(lambda:self.evidence(elf_load(b'ash\0awk\0other\0')),'NOT_FOUND')
    def test_10_overlay_not_allowed(self):
        self.assertHold(lambda:self.evidence(elf_load(b'irrelevant bytes',overlay=PATTERN)),'NOT_FOUND')
    def test_11_duplicate_pattern_hold(self):
        self.assertHold(lambda:self.evidence(elf_load(PATTERN+PATTERN)),'NOT_UNIQUE')
    def test_12_truncated_elf_hold(self):self.assertHold(lambda:self.evidence(b'ELF'),'ELF32_LE')
    def test_13_wrong_machine_hold(self):self.assertHold(lambda:self.evidence(elf_load(machine=183)),'HARDFLOAT_IDENTITY')
    def test_14_wrong_flags_hold(self):self.assertHold(lambda:self.evidence(elf_load(flags=0)),'HARDFLOAT_IDENTITY')
    def test_15_wrong_type_hold(self):self.assertHold(lambda:self.evidence(elf_load(t=1)),'HARDFLOAT_IDENTITY')
    def test_16_wrong_stride_hold(self):self.assertHold(lambda:self.evidence(elf_load(phentsize=31)),'HEADERS_INVALID')
    def test_17_zero_phnum_hold(self):self.assertHold(lambda:self.evidence(elf_load(phnum=0)),'HEADERS_INVALID')
    def test_18_filesz_beyond_memsz_hold(self):self.assertHold(lambda:self.evidence(elf_load(filesz=1000,memsz=10)),'PT_LOAD_OUT_OF_BOUNDS')
    def test_19_filesz_beyond_file_hold(self):self.assertHold(lambda:self.evidence(elf_load(filesz=4000,memsz=4000)),'PT_LOAD_OUT_OF_BOUNDS')
    def test_20_symlinked_applet_list_rejected(self):
        alias=self.dir/'alias';alias.symlink_to(self.paths['listing'])
        with self.assertRaisesRegex(mod.r56.AuditHold,'SYMLINK'):
            mod.r56.bounded(alias,mod.r56.MAX_LIST)
    def test_21_unknown_package_list_digest_hold(self):
        with patch.object(mod,'APPLET_EXPECTED_SHA256','0'*64):
            self.assertHold(lambda:self.evidence(),'NOT_THE_REPORTED')
    def test_22_count_change_hold(self):
        with patch.object(mod,'EXPECTED_COUNT',304):
            self.assertHold(lambda:self.evidence(),'NOT_THE_REPORTED')
    def test_23_seedrng_list_entry_rejected(self):
        self.assertHold(lambda:self.evidence(alist=LIST+b'/usr/sbin/seedrng\n'),'SEEDRNG_CONFLICTS')
    def test_24_ash_absent_rejected(self):
        self.assertHold(lambda:self.evidence(alist=b'/bin/sh\n/usr/bin/awk\n'),'ASH_MISSING')
    def test_25_no_docker_default(self):
        with patch.object(mod.BASE,'docker',side_effect=AssertionError('Docker called')):
            self.assertEqual(mod.main([]),2)
    def test_26_no_docker_default_flags(self):
        p=mod.preflight()
        for k in ('docker_used','arm_executable_launched','physical_device_access_performed',
                  'firmware_write_performed','boot_performed','recovery_verified'):
            self.assertFalse(p[k])
    def test_27_hold_immutable(self):
        self.assertEqual(mod.preflight()['immutable_hold'],'NOT_BOOTABLE')
    def test_28_invalid_r56_digest_rejected(self):
        with patch.object(mod,'R56_SHA256','0'*64):
            self.assertHold(mod.require_helpers,'PINNED_R56_HELPER_CHANGED')
    def test_29_local_synthetic_control(self):
        with patch.object(mod,'require_helpers'),patch.object(mod.r56,'analyze',return_value={'synthetic':True}):
            r=mod.run_local(**self.paths)
        self.assertEqual(r['result'],mod.PASS)
        self.assertFalse(r['audit']['compiled_applets_callable_verified'])
    def test_30_local_missing_file_holds(self):
        self.paths['listing'].unlink()
        with patch.object(mod,'require_helpers'),patch.object(mod.r56,'analyze',return_value={'synthetic':True}):
            r=mod.run_local(**self.paths)
        self.assertEqual(r['result'],'HOLD')
    def test_31_no_partial_local_access(self):
        with patch.object(mod.BASE,'docker',side_effect=AssertionError('Docker called')):
            self.assertEqual(mod.main(['--busybox',str(self.paths['busybox'])]),2)
    def test_32_pattern_must_be_contiguous(self):
        altered=PATTERN.replace(b'awk\0',b'awk\0x')
        self.assertHold(lambda:self.evidence(elf_load(altered)),'NOT_FOUND')
    def test_33_spurious_short_marker_not_enough(self):
        self.assertHold(lambda:self.evidence(elf_load(b'ash\x00/\x00seedrng\x00/\x00')),'NOT_FOUND')
    def test_34_wrong_elf_endianness(self):
        b=bytearray(elf_load());b[5]=2
        self.assertHold(lambda:self.evidence(bytes(b)),'ELF32_LE')
    def test_35_target_runtime_false(self):self.assertFalse(mod.preflight()['target_musl_linux_3_0_35_compatibility_verified'])
    def test_36_overlay_same_pattern_only_hold(self):
        b=elf_load(b'other data',overlay=b'\x00'*10+PATTERN)
        self.assertHold(lambda:self.evidence(b),'NOT_FOUND')

    def test_37_zero_length_load_holds(self):
        self.assertHold(lambda:self.evidence(elf_load(filesz=0,memsz=0)),'PT_LOAD_OUT_OF_BOUNDS')
    def test_38_realistic_304_synthetic_names(self):
        names=[b'ash']+[('testapp%03d'%i).encode('ascii') for i in range(303)]
        fake_list=b''.join(b'/usr/bin/'+name+b'\n' for name in names)
        seq=b''.join(name+b'\0' for name in sorted(names))+b'\0'
        with patch.object(mod,'EXPECTED_COUNT',304),patch.object(mod,'APPLET_EXPECTED_SHA256',hashlib.sha256(fake_list).hexdigest()):
            data=mod.applet_name_array_evidence(elf_load(seq),fake_list)
        self.assertEqual(data['matched_name_count'],304)
    def test_39_pattern_only_in_second_load(self):
        data=bytearray(elf_load(data=b'no-match',phnum=2))
        second_off=len(data)
        data.extend(PATTERN)
        struct.pack_into('<IIIIIIII',data,84,1,second_off,0x20000,0,len(PATTERN),len(PATTERN),4,0x1000)
        self.assertTrue(self.evidence(bytes(data))['exact_sorted_nul_separated_applet_name_array_in_elf_pt_load'])
    def test_40_bad_second_load_rejected(self):
        data=bytearray(elf_load(phnum=2))
        struct.pack_into('<IIIIIIII',data,84,1,999999,0x20000,0,80,80,4,0x1000)
        self.assertHold(lambda:self.evidence(bytes(data)),'PT_LOAD_OUT_OF_BOUNDS')

if __name__=='__main__':unittest.main()
