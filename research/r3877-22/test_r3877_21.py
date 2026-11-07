import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from pw3_r3877_21_arm_syscall_matrix import AuditError, audit, parse_arm_syscalls, parse_kernel_version, safe_read

HERE=pathlib.Path(__file__).resolve().parent
BASE=json.loads((HERE/'R3877_21_USER_REPORTED_INPUT.json').read_text())

def fake_header():
    lines=['#define __NR_SYSCALL_BASE 0', '#define __NR_read (__NR_SYSCALL_BASE+3)',
           '#define __NR_write (__NR_SYSCALL_BASE+4)',
           '#define __NR_futex (__NR_SYSCALL_BASE+240)',
           '#define __NR_clock_gettime (__NR_SYSCALL_BASE+263)']
    lines += [f'#define __NR_dummy_{i} (__NR_SYSCALL_BASE+{i+1000})' for i in range(180)]
    return ('\n'.join(lines)+'\n').encode()

class KernelAuditTests(unittest.TestCase):
    def test_user_evidence_only_pass(self):
        r=audit(BASE)
        self.assertEqual(r['result'],'PASS_VERSION_CONFIG_RISK_MATRIX_ONLY')
        self.assertEqual(r['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(r['runtime_syscall_execution_verified'])
        self.assertEqual(r['root_backing_partition_confirmed_from_prior_live_metadata'],'mmcblk0p1')
    def test_baseline_exceeds_musl_minimum(self):
        self.assertTrue(audit(BASE)['kernel_version_exceeds_musl_general_minimum'])
    def test_newer_syscalls_are_only_mainline_expectations(self):
        for v in audit(BASE)['newer_mainline_syscall_baseline'].values():
            self.assertTrue(v['mainline_postdates_device_kernel'])
            self.assertFalse(v['vendor_backport_checked'])
            self.assertFalse(v['actual_target_syscall_verified'])
    def test_config_is_not_execution(self):
        for v in audit(BASE)['kernel_config_reports'].values():
            self.assertFalse(v['actual_syscall_dispatch_verified'])
    def test_source_header_success(self):
        r=audit(BASE,fake_header(),'upstream_linux_v3_0')
        self.assertEqual(r['result'],'PASS_UPSTREAM_ARM_SYSCALL_NAMES_METADATA_ONLY')
        self.assertEqual(r['core_arm_syscall_names']['futex']['arm_v3_0_source_number'],240)
        self.assertFalse(r['source']['same_as_running_vendor_kernel_verified'])
    def test_vendor_header_cannot_claim_upstream(self):
        r=audit(BASE,fake_header(),'vendor_3_0_35_unverified')
        self.assertEqual(r['result'],'PASS_VERSION_CONFIG_RISK_MATRIX_ONLY')
    def test_bad_digest_holds(self):
        with self.assertRaisesRegex(AuditError,'ARM_SOURCE_SHA256_MISMATCH'):
            audit(BASE,fake_header(),'upstream_linux_v3_0','0'*64)
    def test_bad_header_missing_base_holds(self):
        with self.assertRaisesRegex(AuditError,'ARM_SOURCE_BASE_MISSING'):
            parse_arm_syscalls(fake_header().replace(b'#define __NR_SYSCALL_BASE 0',b'ignore'))
    def test_bad_header_missing_sentinels_holds(self):
        with self.assertRaisesRegex(AuditError,'ARM_SOURCE_SENTINELS_MISMATCH'):
            parse_arm_syscalls(fake_header().replace(b'__NR_futex (__NR_SYSCALL_BASE+240)',b'__NR_futex (__NR_SYSCALL_BASE+241)'))
    def test_tiny_header_is_refused(self):
        with self.assertRaisesRegex(AuditError,'ARM_SOURCE_TOO_FEW_ENTRIES'):
            parse_arm_syscalls(b'#define __NR_SYSCALL_BASE 0\n#define __NR_read (__NR_SYSCALL_BASE+3)')
    def test_duplicate_conflicting_definitions_are_refused(self):
        with self.assertRaisesRegex(AuditError,'ARM_SYSCALL_DUPLICATE_CONFLICT'):
            parse_arm_syscalls(fake_header()+b'\n#define __NR_read (__NR_SYSCALL_BASE+999)\n')
    def test_comments_ignored(self):
        h=fake_header()+b'\n/* #define __NR_fake (__NR_SYSCALL_BASE+5) */\n'
        self.assertNotIn('fake',parse_arm_syscalls(h))
    def test_release_parse(self):
        self.assertEqual(parse_kernel_version('3.0.35-lab126'),(3,0,35))
    def test_bad_release(self):
        with self.assertRaises(AuditError):
            parse_kernel_version('3.0.35; rm -rf /')
    def test_missing_hold_refused(self):
        b=copy.deepcopy(BASE);b['immutable_hold']='BOOTABLE'
        with self.assertRaises(AuditError):audit(b)
    def test_missing_tls_evidence_refused(self):
        b=copy.deepcopy(BASE);b['hwcap_tls_reported']=False
        with self.assertRaises(AuditError):audit(b)
    def test_mismatched_partition_refused(self):
        b=copy.deepcopy(BASE);b['root_backing_partition']='mmcblk0p2'
        with self.assertRaises(AuditError):audit(b)
    def test_header_and_label_both_required(self):
        with self.assertRaises(AuditError):audit(BASE,fake_header())
    def test_host_only_preflight_cli_no_device(self):
        p=subprocess.run([sys.executable,'-B',str(HERE/'pw3_r3877_21_arm_syscall_matrix.py'),str(HERE/'R3877_21_USER_REPORTED_INPUT.json')],capture_output=True,text=True)
        self.assertEqual(p.returncode,0)
        j=json.loads(p.stdout);self.assertFalse(j['physical_device_access_performed'])
    def test_held_cli_does_not_crash(self):
        p=subprocess.run([sys.executable,'-B',str(HERE/'pw3_r3877_21_arm_syscall_matrix.py'),'/not/a/real/path'],capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        self.assertEqual(json.loads(p.stdout)['result'],'HOLD')
    def test_reject_symlink_input(self):
        with tempfile.TemporaryDirectory() as t:
            p=pathlib.Path(t);f=p/'real';f.write_text('hi');s=p/'link';s.symlink_to(f)
            with self.assertRaisesRegex(AuditError,'INPUT_MISSING_OR_SYMLINK'):safe_read(s,100)

if __name__=='__main__':unittest.main()
