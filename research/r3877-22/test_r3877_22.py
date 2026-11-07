import copy
import hashlib
import json
import pathlib
import tempfile
import unittest
from pw3_r3877_21_arm_syscall_matrix import AuditError
from pw3_r3877_22_upstream_source_binding import assess, git_blob_sha1, REQUIRED_SENTINELS, main

ROOT=pathlib.Path(__file__).resolve().parent
EVIDENCE=json.loads((ROOT/'R3877_21_USER_REPORTED_INPUT.json').read_text())

def mock_header():
    # Fixture has the actual v3.0 sentinel numbers, but not original source identity.
    header='/* arch/arm/include/asm/unistd.h synthetic fixture */\n#define __NR_SYSCALL_BASE 0\n'
    for i in range(200):
        header+=f'#define __NR_test_{i} (__NR_SYSCALL_BASE + {i})\n'
    for name,n in REQUIRED_SENTINELS.items():
        header+=f'#define __NR_{name} (__NR_SYSCALL_BASE + {n})\n'
    for name,n in {'mmap2':192,'munmap':91,'set_tid_address':256,'clock_nanosleep':265,
                   'epoll_ctl':251,'epoll_wait':252,'eventfd2':356,'signalfd4':355,
                   'timerfd_create':350,'openat':322}.items():
        header+=f'#define __NR_{name} (__NR_SYSCALL_BASE + {n})\n'
    return header.encode()

class Tests(unittest.TestCase):
    def ok(self,evidence=None,header=None):
        h=header or mock_header()
        return assess(h,evidence or EVIDENCE,expected_blob_sha=git_blob_sha1(h))
    def test_success(self):
        r=self.ok()
        self.assertEqual(r['result'],'PASS_PINNED_UPSTREAM_ARM_SOURCE_NAMES_ONLY')
        self.assertEqual(r['immutable_hold'],'NOT_BOOTABLE')
        self.assertTrue(r['upstream_all_20_core_names_defined'])
        self.assertFalse(r['source']['same_as_running_vendor_kernel_verified'])
    def test_git_hash_known_vector(self):
        data=b'hello\n'
        self.assertEqual(git_blob_sha1(data),hashlib.sha1(b'blob 6\x00hello\n').hexdigest())
    def test_real_pinned_identity_rejects_fixture(self):
        with self.assertRaisesRegex(AuditError,'UPSTREAM_SOURCE_GIT_BLOB_MISMATCH'):
            assess(mock_header(),EVIDENCE)
    def test_altered_source_rejected(self):
        h=mock_header()
        with self.assertRaisesRegex(AuditError,'UPSTREAM_SOURCE_GIT_BLOB_MISMATCH'):
            assess(h+b'junk',EVIDENCE,git_blob_sha1(h))
    def test_corrupt_sentinel(self):
        h=mock_header().replace(b'__NR_read (__NR_SYSCALL_BASE + 3)',b'__NR_read (__NR_SYSCALL_BASE + 33)')
        with self.assertRaisesRegex(AuditError,'ARM_SOURCE_SENTINELS_MISMATCH'):
            self.ok(header=h)
    def test_changed_kernel(self):
        e=copy.deepcopy(EVIDENCE);e['kernel_release']='3.0.36-lab126'
        with self.assertRaisesRegex(AuditError,'TARGET_KERNEL_BASELINE_CHANGED'):
            self.ok(evidence=e)
    def test_missing_root_evidence(self):
        e=copy.deepcopy(EVIDENCE);e['root_backing_partition_verified']=False
        with self.assertRaisesRegex(AuditError,'ROOT_BASELINE_INCONSISTENT'):
            self.ok(evidence=e)
    def test_wrong_hold(self):
        e=copy.deepcopy(EVIDENCE);e['immutable_hold']='BOOTABLE'
        with self.assertRaisesRegex(AuditError,'HOLD_NOT_CONFIRMED'):
            self.ok(evidence=e)
    def test_no_missing_new_syscall_in_mock(self):
        r=self.ok()
        self.assertTrue(all(not x['name_defined_in_upstream_v3_0'] for x in r['post_v3_0_syscalls'].values()))
    def test_never_runtime_verified(self):
        r=self.ok()
        for key in ('runtime_syscall_execution_verified','target_musl_runtime_verified',
                    'recovery_verified','device_files_written','firmware_write_performed','boot_performed'):
            self.assertIs(r[key],False)
    def test_no_header_cli_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(main([str(pathlib.Path(t)/'missing'),str(ROOT/'R3877_21_USER_REPORTED_INPUT.json')]),2)
    def test_corrupt_evidence_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            f=pathlib.Path(t)/'f.h'; f.write_bytes(mock_header())
            g=pathlib.Path(t)/'bad.json';g.write_text('invalid')
            self.assertEqual(main([str(f),str(g)]),2)
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            dest=pathlib.Path(t)/'real';dest.write_bytes(mock_header())
            p=pathlib.Path(t)/'link';p.symlink_to(dest)
            self.assertEqual(main([str(p),str(ROOT/'R3877_21_USER_REPORTED_INPUT.json')]),2)
    def test_unpinned_header_is_never_vendor_verified(self):
        r=self.ok()
        self.assertFalse(r['source']['vendor_kernel_dispatch_verified'])
        self.assertFalse(r['target_kernel_syscall_dispatch_verified'])
if __name__=='__main__': unittest.main()
