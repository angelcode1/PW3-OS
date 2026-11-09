#!/usr/bin/env python3
"""R3877.60.4 host-only tests; no Docker or ARM execution."""
import hashlib, json, io, stat, struct, unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
import pw3_r3877_60_4_qemu_enosys as mod

HERE=Path(__file__).resolve().parent
SRC=(HERE/'pw3_r3877_60_4_aarch64_seccomp_selftest.c').read_text()

class TestR604(unittest.TestCase):
    def test_01_launcher_pin_and_arm_elf(self): self.assertTrue(mod.verify_pins())
    def test_02_arm_never_changed(self): self.assertEqual(mod.ARM_SHA,'b0b89626cd48482e99ea8515b4c808c378e1ff65b4ea4de05b16a4c373df18f4')
    def test_03_host_filter_arch(self): self.assertIn('AUDIT_ARCH_AARCH64 0xc00000b7U',SRC)
    def test_04_seccomp_stacks(self): self.assertIn('PR_SET_NO_NEW_PRIVS',SRC);self.assertIn('PR_SET_SECCOMP',SRC)
    def test_05_guest_filters_both(self): self.assertIn('GUEST_FILTERED_GETRANDOM_NR 278',SRC);self.assertIn('GUEST_FILTERED_STATX_NR 291',SRC)
    def test_06_both_raw_syscalls_checked(self): self.assertIn('if (sys5(GUEST_FILTERED_GETRANDOM_NR',SRC);self.assertIn('if (sys5(GUEST_FILTERED_STATX_NR',SRC)
    def test_07_both_require_negative_enosys(self): self.assertEqual(SRC.count('!= -ENOSYS'),2)
    def test_08_selftests_before_exec(self): self.assertLess(SRC.index('if (sys5(GUEST_FILTERED_STATX_NR'),SRC.index('sys5(NR_EXECVE'))
    def test_09_statx_path_is_constant(self): self.assertIn('target_path[]="/bin/busybox"',SRC)
    def test_10_marker_whitelist_exact(self): self.assertEqual(mod.FILTER_MARKER,'R604_HOST_FILTER_INSTALLED\nR604_HOST_GETRANDOM_ENOSYS_VERIFIED\nR604_HOST_STATX_ENOSYS_VERIFIED\n')
    def test_11_direct_marker_strict(self):
        out=mod.extract_filter_marker('',mod.FILTER_MARKER+'APP\n'); self.assertEqual(out,'APP\n')
    def test_12_missing_marker_hold(self):
        with self.assertRaises(mod.Hold):mod.extract_filter_marker('','APP\n')
    def test_13_partial_marker_hold(self):
        with self.assertRaises(mod.Hold):mod.extract_filter_marker('','R604_HOST_FILTER_INSTALLED\n')
    def test_14_duplicate_marker_hold(self):
        with self.assertRaises(mod.Hold):mod.extract_filter_marker('',mod.FILTER_MARKER*2)
    def test_15_no_docker_default(self):
        with patch.object(mod.base,'docker',side_effect=AssertionError('unexpected Docker')):
            out=io.StringIO()
            with redirect_stdout(out):code=mod.main([])
            self.assertEqual(code,2)
            data=json.loads(out.getvalue())
            self.assertEqual(data['result'],'HOLD');self.assertEqual(data['immutable_hold'],'NOT_BOOTABLE')
    def test_16_no_docker_without_explicit_permission(self):
        with patch.object(mod.base,'docker',side_effect=AssertionError('unexpected Docker')):
            out=io.StringIO()
            with redirect_stdout(out):code=mod.main(['--allow-disposable-writable-layer'])
            self.assertEqual(code,2)
    def test_17_authorized_dispatch(self):
        with patch.object(mod,'run',return_value={'result':mod.PASS}) as mocked:
            with redirect_stdout(io.StringIO()):self.assertEqual(mod.main(['--authorize-offline-qemu']),0)
            mocked.assert_called_once_with(False)
    def test_18_authorized_extra_layer(self):
        with patch.object(mod,'run',return_value={'result':mod.PASS}) as mocked:
            with redirect_stdout(io.StringIO()):self.assertEqual(mod.main(['--authorize-offline-qemu','--allow-disposable-writable-layer']),0)
            mocked.assert_called_once_with(True)
    def test_19_pinned_launcher_elf_machine(self):
        b=mod.LAUNCHER.read_bytes();self.assertEqual(b[:4],b'\x7fELF');self.assertEqual(b[4],2);self.assertEqual(struct.unpack_from('<H',b,18)[0],183)
    def test_20_launcher_execute_mode(self):self.assertTrue(mod.LAUNCHER.stat().st_mode & stat.S_IXOTH)
    def test_21_built_in_seccomp_check_present(self):self.assertIn('DOCKER_BUILTIN_SECCOMP_DEFAULT_NOT_ATTESTED',mod.run.__code__.co_consts)
    def test_22_parent_pinned(self):self.assertTrue(mod.BASE_SHA)
    def test_23_cleanup_rm_volumes(self):
        import inspect
        self.assertIn("['rm','-f','-v',cid]",inspect.getsource(mod.run))
    def test_24_host_and_guest_flags_distinct(self):
        import inspect
        code=inspect.getsource(mod.run)
        self.assertIn('host_statx_enosys_direct_verified=True',code)
        self.assertIn('qemu_guest_statx_enosys_observed=False',code)
    def test_25_statx_guest_error_not_required(self):
        import inspect
        code=inspect.getsource(mod.run)
        self.assertIn("wanted=1 if name=='arm_trace' else 0",code)
    def test_26_host_statx_data_not_raw(self):self.assertNotIn('raw_guest_output_published=True',mod.run.__code__.co_consts)
    def test_27_expected_success_is_narrow(self):self.assertIn('GUEST_STATX_EMULATION_ONLY',mod.PASS)
    def test_28_immutable_hold(self):self.assertEqual(mod.preflight()['immutable_hold'],'NOT_BOOTABLE')
    def test_29_source_reproducibility_pin(self):self.assertEqual(hashlib.sha256(mod.LAUNCHER.read_bytes()).hexdigest(),mod.LAUNCHER_SHA)
    def test_30_enosys_constant(self):self.assertIn('#define ENOSYS 38',SRC)

if __name__=='__main__':unittest.main()
