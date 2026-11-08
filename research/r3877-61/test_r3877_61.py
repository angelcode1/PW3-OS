#!/usr/bin/env python3
"""R3877.61 host-only tests; never start Docker, QEMU or access Kindle."""
import hashlib, io, json, stat, struct, unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
import pw3_r3877_61_qemu_getentropy_enosys as mod

HERE=Path(__file__).resolve().parent
SRC=(HERE/'pw3_r3877_61_armv7_getentropy_enosys.c').read_text()
OLD=(HERE/'pw3_r3877_60_4_qemu_enosys.py').read_text()
NEW=(HERE/'pw3_r3877_61_qemu_getentropy_enosys.py').read_text()
EXPECTED_SHA='ee6b5b8d175618afc46a15cf4451e070c1e67f5da3213150d0882188354acfa2'
EXPECTED_OUTPUT='R61_PASS_ARMV7_PTHREAD_TLS\nR61_OBS_GETRANDOM_ENOSYS\nR61_OBS_GETENTROPY_ENOSYS\nR61_PASS_QEMU_MUSL_ENTROPY_ENOSYS_ONLY\n'

def needed_count(binary):
    b=binary.read_bytes()
    if b[:7]!=b'\x7fELF\x01\x01\x01': raise ValueError('not little endian ELF32')
    phoff=struct.unpack_from('<I',b,28)[0]
    phentsize=struct.unpack_from('<H',b,42)[0]
    phnum=struct.unpack_from('<H',b,44)[0]
    tags=[]
    for i in range(phnum):
        off=phoff+i*phentsize
        if off+32>len(b): raise ValueError('phdr bounds')
        typ,p_offset,_,_,pfilesz,_,_,_=struct.unpack_from('<IIIIIIII',b,off)
        if typ==2:
            if pfilesz>65536 or p_offset+pfilesz>len(b):raise ValueError('dynamic bounds')
            for at in range(p_offset,p_offset+pfilesz,8):
                if at+8>len(b):raise ValueError('dyn tuple bounds')
                tag,val=struct.unpack_from('<II',b,at)
                if tag==0:break
                tags.append(tag)
    return tags.count(1)

class OfflineR61(unittest.TestCase):
    def test_01_verified_pins(self):self.assertTrue(mod.verify_pins())
    def test_02_new_elf_digest(self):self.assertEqual(hashlib.sha256(mod.ARM.read_bytes()).hexdigest(),EXPECTED_SHA)
    def test_03_new_elf_execute_mode(self):self.assertEqual(stat.S_IMODE(mod.ARM.stat().st_mode),0o755)
    def test_04_new_elf_machine(self):self.assertEqual(struct.unpack_from('<H',mod.ARM.read_bytes(),18)[0],40)
    def test_05_arm_hardfloat_flag(self):self.assertEqual(struct.unpack_from('<I',mod.ARM.read_bytes(),36)[0],0x05000400)
    def test_06_exact_interp(self):self.assertIn(b'/lib/ld-musl-armhf.so.1\0',mod.ARM.read_bytes())
    def test_07_exact_libc_needed(self):self.assertEqual(needed_count(mod.ARM),1);self.assertIn(b'libc.so\0',mod.ARM.read_bytes())
    def test_08_previous_arm_retained(self):self.assertEqual(hashlib.sha256((HERE/'pw3_r3877_59_2_armv7_probe.elf').read_bytes()).hexdigest(),'b0b89626cd48482e99ea8515b4c808c378e1ff65b4ea4de05b16a4c373df18f4')
    def test_09_launcher_identical(self):self.assertEqual(mod.LAUNCHER_SHA,'b9a433e2397e27c4cbdd2aade7b57cc39af4e6f36b37a4f204833b282a987b02')
    def test_10_base_script_pin(self):self.assertEqual(mod.BASE_SHA,'5fa8ae5a386d32427ee67e068af55d4dd23a9e61b312357b00d9c0ed6d6ad659')
    def test_11_new_milestone(self):self.assertEqual(mod.MILESTONE,'R3877.61')
    def test_12_new_pass_scope(self):self.assertIn('MUSL_GETENTROPY_ENOSYS',mod.PASS)
    def test_13_expected_program_output(self):self.assertEqual(mod.ARM_EXPECTED,EXPECTED_OUTPUT)
    def test_14_marker_literal_in_binary(self):
        for s in EXPECTED_OUTPUT.splitlines():self.assertIn(s.encode(),mod.ARM.read_bytes())
    def test_15_did_not_skip_getentropy(self):
        self.assertIn('int ret=getentropy(bytes,sizeof(bytes));',SRC)
        self.assertLess(SRC.index('getrandom(bytes,sizeof(bytes)'),SRC.index('getentropy(bytes,sizeof(bytes)'))
    def test_16_direct_errno_required(self):self.assertIn('n!=-1||*__errno_location()!=38',SRC)
    def test_17_getentropy_errno_required(self):self.assertIn('ret!=-1||*__errno_location()!=38',SRC)
    def test_18_errno_reset_before_getentropy(self):self.assertLess(SRC.index('*__errno_location()=0;'),SRC.index('int ret=getentropy'))
    def test_19_no_secure_fallback_claim(self):self.assertFalse(mod.preflight()['application_secure_entropy_fallback_verified'])
    def test_20_getentropy_flag_false_by_default(self):self.assertFalse(mod.preflight()['runtime_musl_getentropy_enosys_return_verified'])
    def test_21_no_guest_network(self):self.assertFalse(mod.preflight()['guest_network_enabled'])
    def test_22_no_host_mount(self):self.assertFalse(mod.preflight()['host_mounts_enabled'])
    def test_23_no_device(self):self.assertFalse(mod.preflight()['physical_device_access_performed'])
    def test_24_not_bootable(self):self.assertEqual(mod.preflight()['immutable_hold'],'NOT_BOOTABLE')
    def test_25_no_docker_without_auth(self):
        with patch.object(mod.base,'docker',side_effect=AssertionError('Docker disallowed')):
            out=io.StringIO()
            with redirect_stdout(out):self.assertEqual(mod.main([]),2)
        self.assertEqual(json.loads(out.getvalue())['result'],'HOLD')
    def test_26_no_docker_with_writable_flag_alone(self):
        with patch.object(mod.base,'docker',side_effect=AssertionError('Docker disallowed')):
            out=io.StringIO()
            with redirect_stdout(out):self.assertEqual(mod.main(['--allow-disposable-writable-layer']),2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'WRITABLE_OPT_IN_REQUIRES_OFFLINE_QEMU_AUTHORIZATION')
    def test_27_count_guest_getrandom_calls_twice(self):self.assertIn("required_calls=2 if name=='arm_trace' else 1",NEW)
    def test_28_require_both_guest_enosys(self):self.assertIn("wanted=2 if name=='arm_trace' else 0",NEW)
    def test_29_no_dilution_of_docker_seccomp(self):self.assertIn('DOCKER_BUILTIN_SECCOMP_DEFAULT_NOT_ATTESTED',NEW)
    def test_30_container_cleanup_uses_v(self):self.assertIn("['rm','-f','-v',cid]",NEW)
    def test_31_anonymous_volume_cleanup(self):self.assertIn("r['anonymous_volume_cleanup_verified']=volume_cleanup_verified",NEW)
    def test_32_require_host_statx_enosys(self):self.assertIn('host_statx_enosys_direct_verified=True',NEW)
    def test_33_require_host_getrandom_enosys(self):self.assertIn('host_getrandom_enosys_direct_verified=True',NEW)
    def test_34_guest_statx_emulation_distinct(self):self.assertIn('qemu_guest_statx_enosys_observed=False',NEW)
    def test_35_return_enosys_pass_field(self):self.assertIn('runtime_musl_getentropy_enosys_return_verified=True',NEW)
    def test_36_no_kindle(self):self.assertEqual(mod.preflight()['kindle_ssh_sessions'],0)
    def test_37_authorization_calls_run_only_after_opt_in(self):
        with patch.object(mod,'run',return_value={'result':mod.PASS}) as run:
            with redirect_stdout(io.StringIO()):rc=mod.main(['--authorize-offline-qemu'])
        self.assertEqual(rc,0);run.assert_called_once_with(False)
    def test_38_two_authorizations_for_writable(self):
        with patch.object(mod,'run',return_value={'result':'HOLD'}) as run:
            with redirect_stdout(io.StringIO()):rc=mod.main(['--authorize-offline-qemu','--allow-disposable-writable-layer'])
        self.assertEqual(rc,2);run.assert_called_once_with(True)
    def test_39_guest_arm_not_same(self):self.assertNotEqual(mod.ARM.name,'pw3_r3877_59_2_armv7_probe.elf')
    def test_40_no_new_launcher_or_base_pins(self):
        self.assertEqual(mod.LAUNCHER_SHA,'b9a433e2397e27c4cbdd2aade7b57cc39af4e6f36b37a4f204833b282a987b02')
        self.assertEqual(mod.base.PARENT_ID,'sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a')

if __name__=='__main__':unittest.main()
