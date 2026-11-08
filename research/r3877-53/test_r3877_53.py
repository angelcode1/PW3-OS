import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pw3_r3877_53_entropy_source_audit as audit


SOURCES = {
    'lab126/arch/arm/include/asm/unistd.h': '#define __NR_set_tid_address (__NR_SYSCALL_BASE+256)\n',
    'lab126/arch/arm/kernel/calls.S': 'CALL(sys_set_tid_address)\n',
    'musl/src/linux/getrandom.c': 'ssize_t getrandom(void *buf, size_t buflen, unsigned flags) { return syscall_cp(SYS_getrandom, buf, buflen, flags); }\n',
    'musl/src/misc/getentropy.c': 'int getentropy(void *buffer, size_t len) { while (len) { ret = getrandom(pos, len, 0); if (ret < 0) { if (errno == EINTR) continue; else break; } } return ret; }\n',
    'musl/src/env/__libc_start_main.c': 'void __init_libc(void) { __init_ssp((void *)aux[AT_RANDOM]); }\n',
    'musl/src/env/__stack_chk_fail.c': 'void __init_ssp(void *entropy) { if (entropy) memcpy(&__stack_chk_guard, entropy, sizeof(uintptr_t)); else __stack_chk_guard = (uintptr_t)&__stack_chk_guard * 1103515245; }\n',
}

PRIOR = {
    'milestone': 'R3877.52.1',
    'result': audit.PRIOR_RESULT,
    'exit_code_reported': 0,
    'immutable_hold': 'NOT_BOOTABLE',
    'verified_public_git_blob_count': 13,
    'actual_vendor_syscall_dispatch_verified': False,
    'target_musl_linux_3_0_35_compatibility_verified': False,
    'selected_live_metadata': {'kernel_release': '3.0.35-lab126', 'architecture': 'armv7l',
                               'selected_config_count': 18, 'core_abi_config_flags_enabled': True},
}

class R53Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # macOS /var is commonly a symlink; fixture must be canonical without
        # relaxing the production auditor's symlink rejection.
        self.root = Path(self.tmp.name).resolve(strict=True)
        self.src = self.root / 'sources'
        self.src.mkdir()
        self.pins = {}
        for name, body in SOURCES.items():
            p = self.src / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body)
            self.pins[name] = ('fixture', 'immutable', name, audit.git_blob_sha1(body.encode()))
        self.prior = self.root / 'prior.json'
        self.update_prior(PRIOR)

    def tearDown(self):
        self.tmp.cleanup()

    def update_prior(self, data):
        self.prior.write_text(json.dumps(data))

    def replace(self, name, before, after, update_pin=True):
        p = self.src/name
        s=p.read_text()
        self.assertIn(before,s)
        s=s.replace(before,after)
        p.write_text(s)
        if update_pin:
            old=self.pins[name]
            self.pins[name]=(*old[:3], audit.git_blob_sha1(s.encode()))

    def run_audit(self):
        return audit.run(self.src,self.prior,self.pins)

    def test_01_positive(self):
        self.assertEqual(self.run_audit()['result'],audit.RESULT)

    def test_02_hold_immutable(self):
        self.assertEqual(self.run_audit()['immutable_hold'],'NOT_BOOTABLE')

    def test_03_no_target_execution(self):
        d=self.run_audit()
        self.assertFalse(d['arm_executable_launched'])
        self.assertFalse(d['target_musl_linux_3_0_35_compatibility_verified'])

    def test_04_source_count(self):
        self.assertEqual(self.run_audit()['public_source_git_blob_count'],6)

    def test_05_digests(self):
        d=self.run_audit()['public_source_git_blob_sha1_by_path']
        self.assertEqual(d,set(self.pins) and {k:v[3] for k,v in self.pins.items()})

    def test_06_previous_r52_is_used(self):
        self.assertEqual(self.run_audit()['selected_prior_user_reported_R52_1_evidence']['verified_public_git_blob_count'],13)

    def test_07_fail_missing(self):
        (self.src/'musl/src/linux/getrandom.c').unlink()
        with self.assertRaisesRegex(audit.AuditHold,'FILE_MISSING_OR_OUT_OF_BOUNDS'):
            self.run_audit()

    def test_08_fail_source_blob_drift(self):
        self.replace('musl/src/linux/getrandom.c','return syscall_cp','return  syscall_cp',False)
        with self.assertRaisesRegex(audit.AuditHold,'PINNED_GIT_BLOB_MISMATCH'):
            self.run_audit()

    def test_09_fail_symlink_source(self):
        p=self.src/'musl/src/linux/getrandom.c'
        target=self.root/'untrusted'
        p.rename(target)
        p.symlink_to(target)
        with self.assertRaisesRegex(audit.AuditHold,'SYMLINK_REJECTED'):
            self.run_audit()

    def test_10_fail_symlink_parent(self):
        s=self.root/'safe-source'
        self.src.rename(s)
        self.src.symlink_to(s,target_is_directory=True)
        with self.assertRaisesRegex(audit.AuditHold,'SYMLINK_REJECTED'):
            self.run_audit()

    def test_11_fail_header_new_getrandom(self):
        self.replace('lab126/arch/arm/include/asm/unistd.h', '256)\n', '256)\n#define __NR_getrandom (__NR_SYSCALL_BASE+384)\n')
        with self.assertRaisesRegex(audit.AuditHold,'PUBLIC_ARM_HEADER_GETRANDOM'):
            self.run_audit()

    def test_12_fail_calls_new_getrandom(self):
        self.replace('lab126/arch/arm/kernel/calls.S','CALL(sys_set_tid_address)','CALL(sys_set_tid_address)\nCALL(sys_getrandom)')
        with self.assertRaisesRegex(audit.AuditHold,'PUBLIC_ARM_CALL_TABLE_GETRANDOM'):
            self.run_audit()

    def test_13_fail_header_bad_baseline(self):
        self.replace('lab126/arch/arm/include/asm/unistd.h','256','777')
        with self.assertRaisesRegex(audit.AuditHold,'PUBLIC_ARM_HEADER_UNRECOGNIZED'):
            self.run_audit()

    def test_14_fail_call_table_bad_baseline(self):
        self.replace('lab126/arch/arm/kernel/calls.S','sys_set_tid_address','sys_other')
        with self.assertRaisesRegex(audit.AuditHold,'PUBLIC_ARM_CALL_TABLE_UNRECOGNIZED'):
            self.run_audit()

    def test_15_getrandom_wrapper_not_claimed_fallback(self):
        self.assertTrue(self.run_audit()['source_audit']['musl_getrandom_direct_syscall_wrapper_without_device_fallback_source'])

    def test_16_fail_wrapper_changed(self):
        self.replace('musl/src/linux/getrandom.c','syscall_cp(SYS_getrandom','syscall_cp(SYS_other')
        with self.assertRaisesRegex(audit.AuditHold,'GETRANDOM_DIRECT_WRAPPER'):
            self.run_audit()

    def test_17_fail_wrapper_new_device_fallback(self):
        self.replace('musl/src/linux/getrandom.c',' }\n',' /* /dev/urandom */ }\n')
        with self.assertRaisesRegex(audit.AuditHold,'GETRANDOM_WRAPPER_FALLBACK'):
            self.run_audit()

    def test_18_fail_getentropy_caller_changed(self):
        self.replace('musl/src/misc/getentropy.c','getrandom(pos','other(pos')
        with self.assertRaisesRegex(audit.AuditHold,'GETENTROPY_CALLPATH'):
            self.run_audit()

    def test_19_fail_getentropy_EINTR_changed(self):
        self.replace('musl/src/misc/getentropy.c','errno == EINTR','errno == EINVAL')
        with self.assertRaisesRegex(audit.AuditHold,'GETENTROPY_EINTR'):
            self.run_audit()

    def test_20_fail_getentropy_propagation_changed(self):
        self.replace('musl/src/misc/getentropy.c','else break','else continue')
        with self.assertRaisesRegex(audit.AuditHold,'GETENTROPY_ERROR_PROPAGATION'):
            self.run_audit()

    def test_21_fail_getentropy_device_added(self):
        self.replace('musl/src/misc/getentropy.c',' }\n',' /* /dev/urandom */ }\n')
        with self.assertRaisesRegex(audit.AuditHold,'GETENTROPY_FALLBACK_CHANGED'):
            self.run_audit()

    def test_22_fail_auxv_changed(self):
        self.replace('musl/src/env/__libc_start_main.c','AT_RANDOM','AT_OTHER')
        with self.assertRaisesRegex(audit.AuditHold,'AT_RANDOM_STARTUP_PATH'):
            self.run_audit()

    def test_23_fail_guard_memory_copy_changed(self):
        self.replace('musl/src/env/__stack_chk_fail.c','memcpy(&__stack_chk_guard','memcpy(&unrelated')
        with self.assertRaisesRegex(audit.AuditHold,'STACK_CANARY_ENTROPY_SOURCE'):
            self.run_audit()

    def test_24_fail_guard_fallback_changed(self):
        self.replace('musl/src/env/__stack_chk_fail.c','1103515245','101')
        with self.assertRaisesRegex(audit.AuditHold,'STACK_CANARY_MISSING_AUX_FALLBACK'):
            self.run_audit()

    def test_25_prior_bad_result(self):
        d=dict(PRIOR,result='HOLD');self.update_prior(d)
        with self.assertRaisesRegex(audit.AuditHold,'PRIOR_R52_PASS_EVIDENCE'):
            self.run_audit()

    def test_26_prior_bad_count(self):
        d=dict(PRIOR,verified_public_git_blob_count=12);self.update_prior(d)
        with self.assertRaisesRegex(audit.AuditHold,'PRIOR_R52_PASS_SCOPE'):
            self.run_audit()

    def test_27_prior_bad_kernel(self):
        d=dict(PRIOR,selected_live_metadata=dict(PRIOR['selected_live_metadata'],kernel_release='6.1'))
        self.update_prior(d)
        with self.assertRaisesRegex(audit.AuditHold,'PRIOR_R52_LIVE_CONTEXT'):
            self.run_audit()

    def test_28_prior_bad_config(self):
        d=dict(PRIOR,selected_live_metadata=dict(PRIOR['selected_live_metadata'],selected_config_count=0))
        self.update_prior(d)
        with self.assertRaisesRegex(audit.AuditHold,'PRIOR_R52_LIVE_CONTEXT'):
            self.run_audit()

    def test_29_prior_runtime_true(self):
        d=dict(PRIOR,target_musl_linux_3_0_35_compatibility_verified=True)
        self.update_prior(d)
        with self.assertRaisesRegex(audit.AuditHold,'PRIOR_R52_PASS_SCOPE'):
            self.run_audit()

    def test_30_bad_utf8(self):
        p=self.src/'musl/src/linux/getrandom.c'
        p.write_bytes(b'\xff\xfe')
        v=self.pins['musl/src/linux/getrandom.c']
        self.pins['musl/src/linux/getrandom.c']=(*v[:3],audit.git_blob_sha1(b'\xff\xfe'))
        with self.assertRaisesRegex(audit.AuditHold,'SOURCE_NOT_UTF8'):
            self.run_audit()

    def test_31_positive_source_risk_no_runtime(self):
        d=self.run_audit()['source_audit']
        self.assertFalse(d['running_vendor_kernel_getrandom_availability_verified'])
        self.assertFalse(d['application_level_entropy_fallback_verified'])

    def test_32_at_random_separate(self):
        self.assertTrue(self.run_audit()['source_audit']['AT_RANDOM_not_the_getrandom_syscall'])

    def test_33_default_cli_hold(self):
        p=Path(audit.__file__).resolve()
        r=subprocess.run([sys.executable,'-B',str(p)],text=True,capture_output=True,cwd=self.root,timeout=10)
        self.assertEqual(r.returncode,2)
        d=json.loads(r.stdout)
        self.assertEqual(d['result'],'HOLD')
        self.assertEqual(d['immutable_hold'],'NOT_BOOTABLE')

    def test_34_empty_prior_file(self):
        self.prior.write_bytes(b'')
        with self.assertRaisesRegex(audit.AuditHold,'FILE_MISSING_OR_OUT_OF_BOUNDS'):
            self.run_audit()

    def test_35_untrusted_symlink_prior(self):
        p=self.root/'new.json'
        self.prior.rename(p)
        self.prior.symlink_to(p)
        with self.assertRaisesRegex(audit.AuditHold,'SYMLINK_REJECTED'):
            self.run_audit()

    def test_36_extra_source_ignored(self):
        (self.src/'unrelated').write_text('data')
        self.assertEqual(self.run_audit()['result'],audit.RESULT)

    def test_37_no_source_set_change(self):
        bodies={k:v for k,v in SOURCES.items()};bodies['other']='a'
        with self.assertRaisesRegex(audit.AuditHold,'SOURCE_INPUT_SET_CHANGED'):
            audit.check_source(bodies)

    def test_38_getrandom_public_absence_not_device_proof(self):
        d=self.run_audit()['source_audit']
        self.assertFalse(d['public_linux3_arm_getrandom_syscall_definition_present'])
        self.assertFalse(d['running_vendor_kernel_getrandom_availability_verified'])

    def test_39_pin_filename_injection_rejected(self):
        p={**self.pins, '../bad':('a','b','c','d')}
        with self.assertRaisesRegex(audit.AuditHold,'PIN_MALFORMED'):
            audit.load_sources(self.src,p)

    def test_40_bounded_size(self):
        p=self.src/'musl/src/linux/getrandom.c'
        p.write_bytes(b'a'*65537)
        with self.assertRaisesRegex(audit.AuditHold,'FILE_MISSING_OR_OUT_OF_BOUNDS'):
            self.run_audit()

if __name__ == '__main__':
    unittest.main()