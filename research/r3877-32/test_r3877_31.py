import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import pw3_r3877_31_buildlog_audit as m

FIXTURE=b'''>>> musl: Building musl-1.2.6-r3 (using abuild 3.17.0-r0)\ncc -O2 -march=armv7-a -mfloat-abi=hard -fPIC -fstack-protector-strong -c src/test.c -o test.o\narmv7-alpine-linux-musleabihf-gcc -Os -Wl,-z,relro -shared -o /private/build/path/libc.so test.o\nexport CFLAGS='-O2 -march=armv7-a'\ngcc (Alpine 15.2.0) 15.2.0\n>>> musl: Build complete\n'''

def audit(raw=FIXTURE):
    return m.analyze(raw,hashlib.sha256(raw).hexdigest(),len(raw))

class TestLogParser(unittest.TestCase):
    def test_expected_pin(self):
        self.assertEqual(m.EXPECTED_BYTES,1644394)
        self.assertEqual(len(m.EXPECTED_SHA256),64)
    def test_fixture_pass(self):
        d=audit()
        self.assertEqual(d['compiler_like_lines_with_flags'],2)
        self.assertEqual(d['likely_compile_lines'],1)
        self.assertEqual(d['likely_link_lines'],1)
    def test_allowlisted_flags(self):
        flags={x['flag'] for x in audit()['allowlisted_flags']}
        self.assertTrue({'-O2','-Os','-march=armv7-a','-mfloat-abi=hard','-fPIC','-Wl,-z,relro'}.issubset(flags))
    def test_no_path_leak(self):
        self.assertNotIn('/private/build/',json.dumps(audit()))
        self.assertNotIn('src/test.c',json.dumps(audit()))
    def test_ignore_unsafe_flags(self):
        raw=FIXTURE.replace(b'-fPIC',b'-DSECRET=abc123 -I/private/secret -fPIC')
        self.assertNotIn('abc123',json.dumps(audit(raw)))
    def test_missing_pkg(self):
        with self.assertRaisesRegex(m.AuditHold,'PACKAGE_VERSION'):audit(b'hello')
    def test_html_refused(self):
        with self.assertRaisesRegex(m.AuditHold,'HTML'):audit(b'<html>musl-1.2.6-r3</html>')
    def test_null_refused(self):
        with self.assertRaisesRegex(m.AuditHold,'NUL'):audit(b'musl-1.2.6-r3\0')
    def test_empty_refused(self):
        with self.assertRaisesRegex(m.AuditHold,'SIZE'):audit(b'')
    def test_excess_refused(self):
        with self.assertRaisesRegex(m.AuditHold,'SIZE'):audit(b'a'*(m.MAX_BYTES+1))
    def test_sha_mismatch(self):
        with self.assertRaisesRegex(m.AuditHold,'SHA256'):m.analyze(FIXTURE,'0'*64,len(FIXTURE))
    def test_len_mismatch(self):
        with self.assertRaisesRegex(m.AuditHold,'LENGTH'):m.analyze(FIXTURE,hashlib.sha256(FIXTURE).hexdigest(),len(FIXTURE)+1)
    def test_wrong_input(self):
        with self.assertRaisesRegex(m.AuditHold,'TYPE'):m.analyze('hello')
    def test_assignment_mentions(self):
        self.assertEqual(audit()['explicit_assignment_mentions']['CFLAGS'],1)
    def test_version_banner_number_is_unverified(self):
        self.assertIn('15.2.0',[x['number'] for x in audit()['version_banner_numbers_unverified']])
    def test_stage(self):
        self.assertEqual(audit()['musl_build_complete_marker_count'],1)
    def test_failed_marker(self):
        self.assertEqual(audit(FIXTURE+b'>>> musl: Build failed\n')['musl_build_failure_marker_count'],1)
    def test_source_commit_marker(self):
        self.assertTrue(audit(FIXTURE+m.SOURCE_COMMIT.encode())['source_commit_marker_found'])
    def test_without_source_marker(self):
        self.assertFalse(audit()['source_commit_marker_found'])
    def test_no_commands_still_pass(self):
        self.assertEqual(audit(b'musl-1.2.6-r3\n')['compiler_like_lines_with_flags'],0)
    def test_ansi_codes(self):
        self.assertEqual(audit(b'\x1b[32m'+FIXTURE)['likely_compile_lines'],1)
    def test_hold_stays(self):
        b=m.base();self.assertEqual(b['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(b['historical_builder_toolchain_versions_verified'])
    def test_no_binary_proof(self):
        self.assertFalse(audit()['source_to_binary_reproducibility_verified'])
    def test_no_source_exec(self):
        src=Path(m.__file__).read_text()
        self.assertNotIn('subprocess',src)
        self.assertNotIn('os.system(',src)
    def test_missing_file_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            r=subprocess.run([sys.executable,'-B',m.__file__,str(Path(td)/'missing')],capture_output=True,text=True)
            self.assertEqual(r.returncode,2)
            self.assertEqual(json.loads(r.stdout)['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
    def test_symlink_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'log';src.write_bytes(FIXTURE)
            dest=Path(td)/'link';dest.symlink_to(src)
            r=subprocess.run([sys.executable,'-B',m.__file__,str(dest)],capture_output=True,text=True)
            self.assertEqual(r.returncode,2)
            self.assertEqual(json.loads(r.stdout)['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
    def test_short_reported_file_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'log';f.write_bytes(FIXTURE)
            r=subprocess.run([sys.executable,'-B',m.__file__,str(f)],capture_output=True,text=True)
            self.assertEqual(r.returncode,2)
            self.assertEqual(json.loads(r.stdout)['hold_category'],'LOG_LENGTH_MISMATCH')

if __name__=='__main__':unittest.main()
