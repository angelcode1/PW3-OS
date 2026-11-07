import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
import pw3_r3877_23_musl_source_audit as a


def sample_sources():
    num='\n'.join('#define __NR_%s\t%s' % (k,v) for k,v in a.EXPECTED_NR.items())+'\n'
    return {
     'alpine_APKBUILD':'pkgver=1.2.6\npkgrel=3\nsource="CVE-2026-107891.patch"\n',
     'clock_gettime.c':'SYS_clock_gettime64 SYS_clock_gettime r!=-ENOSYS __syscall(SYS_clock_gettime, clk, ts32)',
     '__timedwait.c':'SYS_futex_time64 SYS_futex r!=-ENOSYS __syscall_cp(SYS_futex, addr CLAMP(s)',
     'getrandom.c':'syscall_cp(SYS_getrandom, buf, buflen, flags)',
     'fstatat.c':'fstatat_statx ret!=-ENOSYS fstatat_kstat',
     'arm_syscall.h.in':num,
     'arm_syscall_arch.h':'VDSO_CGT32_SYM\nVDSO_CGT_SYM\n',
    }

class SourceTests(unittest.TestCase):
    def test_baseline_seven_source_paths(self):self.assertEqual(len(a.PINS),7)
    def test_reference_musl_release(self):self.assertEqual(a.EXPECTED_MUSL_VERSION,'1.2.6-r3')
    def test_source_report(self):
        d=a.classify_source(sample_sources());self.assertTrue(d['clock_gettime_legacy_fallback_source_present']);self.assertTrue(d['getrandom_wrapper_has_no_internal_enosys_fallback'])
    def test_reject_apk_version(self):
        d=sample_sources();d['alpine_APKBUILD']=d['alpine_APKBUILD'].replace('pkgver=1.2.6','pkgver=1.2.5')
        with self.assertRaisesRegex(a.AuditHold,'APKBUILD_VERSION'):a.classify_source(d)
    def test_reject_apk_patchlist(self):
        d=sample_sources();d['alpine_APKBUILD']=d['alpine_APKBUILD'].replace('CVE-2026-107891.patch','other.patch')
        with self.assertRaisesRegex(a.AuditHold,'PATCH_LIST'):a.classify_source(d)
    def test_reject_clock_fallback(self):
        d=sample_sources();d['clock_gettime.c']=d['clock_gettime.c'].replace('r!=-ENOSYS','r!=ENOENT')
        with self.assertRaisesRegex(a.AuditHold,'CLOCK_FALLBACK'):a.classify_source(d)
    def test_reject_futex_fallback(self):
        d=sample_sources();d['__timedwait.c']=d['__timedwait.c'].replace('CLAMP(s)','CLAMP()')
        with self.assertRaisesRegex(a.AuditHold,'FUTEX_FALLBACK'):a.classify_source(d)
    def test_reject_statx_fallback(self):
        d=sample_sources();d['fstatat.c']=d['fstatat.c'].replace('fstatat_kstat','fstat')
        with self.assertRaisesRegex(a.AuditHold,'STATX_FALLBACK'):a.classify_source(d)
    def test_reject_random_semantic_change(self):
        d=sample_sources();d['getrandom.c']+=' if (r==-ENOSYS) return urandom;'
        with self.assertRaisesRegex(a.AuditHold,'GETRANDOM_WRAPPER_SEMANTICS_CHANGED'):a.classify_source(d)
    def test_reject_random_wrapper_missing(self):
        d=sample_sources();d['getrandom.c']='call(SYS_getrandom)'
        with self.assertRaisesRegex(a.AuditHold,'GETRANDOM_WRAPPER_UNEXPECTED'):a.classify_source(d)
    def test_reject_syscall_number(self):
        d=sample_sources();d['arm_syscall.h.in']=d['arm_syscall.h.in'].replace('__NR_openat2\t437','__NR_openat2\t438')
        with self.assertRaisesRegex(a.AuditHold,'ARM_SYSCALL_NUMBER_UNEXPECTED'):a.classify_source(d)
    def test_reject_arm_vdso_macro(self):
        d=sample_sources();d['arm_syscall_arch.h']='VDSO_CGT32_SYM'
        with self.assertRaisesRegex(a.AuditHold,'VDSO_SOURCE'):a.classify_source(d)
    def test_git_blob_identity(self):
        self.assertEqual(a.sha_git_blob(b'hello\n'),'ce013625030ba8dba906f756967f9e9ca394464a')
    def test_matching_pinned_fixture(self):
        with tempfile.TemporaryDirectory() as t:
            d=sample_sources();pins={}
            for name,s in d.items():
                b=s.encode(); (Path(t)/name).write_bytes(b)
                pins[name]=('fake','test',name,a.sha_git_blob(b))
            result=a.analyze_source_dir(Path(t),pins)
            self.assertEqual(len(result['source_blob_sha1_by_file']),7)
    def test_tampered_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            d=sample_sources();pins={}
            for name,s in d.items():
                b=s.encode(); (Path(t)/name).write_bytes(b)
                pins[name]=('fake','test',name,a.sha_git_blob(b))
            (Path(t)/'getrandom.c').write_text('tampered')
            with self.assertRaisesRegex(a.AuditHold,'PINNED_SOURCE_GIT_BLOB_MISMATCH'):a.analyze_source_dir(Path(t),pins)
    def test_missing_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(a.AuditHold,'PINNED_SOURCE_MISSING'):a.analyze_source_dir(Path(t))
    def test_symlink_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/'getrandom.c').symlink_to('/etc/hosts')
            self.assertRaises(a.AuditHold,a.limited_read,Path(t)/'getrandom.c')
    def test_oversize_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'too_big';p.write_bytes(b'x'*65537)
            self.assertRaises(a.AuditHold,a.limited_read,p)

class CandidateTests(unittest.TestCase):
    def make(self,t, *,version='1.2.6-r3', arch='armv7',image='sha256:dummy', loader=None):
        out=Path(t)
        (out/'image-id.txt').write_text(image+'\n')
        (out/'installed.db').write_text('P:busybox\nV:1.0\n\nP:musl\nV:'+version+'\nA:'+arch+'\n\n')
        ld=loader or (b'\x7fELF'+b'\x01\x01'+b'\x00'*12+b'\x28\x00'+b'\x00'*64)
        (out/'loader').write_bytes(ld)
        return ld
    def test_installed_db(self):
        x=a.extract_musl_stanza(b'P:busybox\nV:1\n\nP:musl\nV:1.2.6-r3\nA:armv7\n\n')
        self.assertEqual(x['V'],'1.2.6-r3')
    def test_db_missing_musl(self):
        with self.assertRaisesRegex(a.AuditHold,'MUSL_RECORD_MISSING'):a.extract_musl_stanza(b'P:busybox\n\n')
    def test_candidate_happy_path(self):
        with tempfile.TemporaryDirectory() as t:
            loader=self.make(t)
            d=a.analyze_candidate(Path(t),expected_image='sha256:dummy',expected_loader_sha256=hashlib.sha256(loader).hexdigest())
            self.assertTrue(d['candidate_musl_metadata_and_previous_hash_match'])
    def test_wrong_image(self):
        with tempfile.TemporaryDirectory() as t:
            loader=self.make(t)
            with self.assertRaisesRegex(a.AuditHold,'IMAGE_ID_BASELINE_MISMATCH'):a.analyze_candidate(Path(t),expected_loader_sha256=hashlib.sha256(loader).hexdigest())
    def test_wrong_loader(self):
        with tempfile.TemporaryDirectory() as t:
            self.make(t)
            with self.assertRaisesRegex(a.AuditHold,'LOADER_SHA256_MISMATCH'):a.analyze_candidate(Path(t),expected_image='sha256:dummy')
    def test_wrong_version(self):
        with tempfile.TemporaryDirectory() as t:
            loader=self.make(t,version='1.2.5-r1')
            with self.assertRaisesRegex(a.AuditHold,'MUSL_VERSION_DIFFERS'):a.analyze_candidate(Path(t),expected_image='sha256:dummy',expected_loader_sha256=hashlib.sha256(loader).hexdigest())
    def test_wrong_arch(self):
        with tempfile.TemporaryDirectory() as t:
            loader=self.make(t,arch='aarch64')
            with self.assertRaisesRegex(a.AuditHold,'ARCH_UNEXPECTED'):a.analyze_candidate(Path(t),expected_image='sha256:dummy',expected_loader_sha256=hashlib.sha256(loader).hexdigest())
    def test_invalid_elf_arm(self):
        with tempfile.TemporaryDirectory() as t:
            loader=self.make(t,loader=b'not an elf')
            with self.assertRaisesRegex(a.AuditHold,'NOT_ELF32_ARM'):a.analyze_candidate(Path(t),expected_image='sha256:dummy',expected_loader_sha256=hashlib.sha256(loader).hexdigest())
    def test_source_not_supplied_is_hold(self):
        with tempfile.TemporaryDirectory() as t:
            stdout=io.StringIO()
            with contextlib.redirect_stdout(stdout):ret=a.main(['--source-dir',t])
            self.assertEqual(ret,2)
            d=json.loads(stdout.getvalue());self.assertEqual(d['immutable_hold'],'NOT_BOOTABLE');self.assertEqual(d['kindle_ssh_sessions'],0)
    def test_no_implicit_docker_or_ssh(self):
        import inspect
        s=inspect.getsource(a.main)
        self.assertNotIn('subprocess',s)
        self.assertNotIn('ssh ',s)
        self.assertNotIn('docker ',s)

if __name__=='__main__':unittest.main()
