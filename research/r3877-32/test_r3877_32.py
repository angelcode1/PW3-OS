"""R3877.32 offline regression; never uses Kindle or public log contents."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import pw3_r3877_32_log_command_shapes as m
import pw3_r3877_31_buildlog_audit as earlier

MOCKLOG=(b'>>> musl: Building musl-1.2.6-r3\n'
         b'cc -O2 -fPIC -mfloat-abi=hard -c src/secret.c -o /private/obj.o\n'
         b'armv7-alpine-linux-musleabihf-gcc -O2 -fno-asynchronous-unwind-tables '
         b'-Wl,-soname,libc.musl-armv7.so.1 -shared -o /private/libc.so /private/obj.o\n'
         b'>>> musl: Build complete\n')

# Isolate R3877.32's exact source logic using a synthetic R3877.31 baseline.
def mocked_prior(raw, expected_hash, expected_length):
    if hashlib.sha256(raw).hexdigest()!=expected_hash or len(raw)!=expected_length:
        raise earlier.AuditHold('LOG_SHA256_MISMATCH')
    return {'log_line_count':m.EXPECTED_LINES,'likely_compile_lines':m.EXPECTED_COMPILE,
            'likely_link_lines':m.EXPECTED_LINK,
            'compiler_like_lines_with_flags':m.EXPECTED_COMPILER_WITH_FLAGS,
            'allowlisted_flags':[{'flag':k,'observed_line_count':v} for k,v in m.EXPECTED_FLAG_COUNTS.items()]}

def synthetic(raw=MOCKLOG):
    with patch.object(m.prior,'analyze',side_effect=mocked_prior),\
         patch.object(m,'EXPECTED_COMPILE',1),\
         patch.object(m,'EXPECTED_LINK',1):
        return m.analyze(raw,hashlib.sha256(raw).hexdigest(),len(raw))

class TestCommandShapes(unittest.TestCase):
    def test_pins(self):
        self.assertEqual(m.EXPECTED_LINES,1981)
        self.assertEqual(m.EXPECTED_COMPILE,1428)
        self.assertEqual(m.EXPECTED_LINK,1)
    def test_synthetic_classification(self):
        x=synthetic()
        self.assertEqual(x['likely_compile_line_count'],1)
        self.assertEqual(x['likely_link_line_count'],1)
        self.assertEqual(x['link_driver_classes'][0]['value'],'target-prefixed-gcc')
        self.assertEqual(x['compile_driver_classes'][0]['value'],'cc')
    def test_report_no_raw_paths(self):
        d=json.dumps(synthetic());self.assertNotIn('/private/',d)
        self.assertNotIn('secret.c',d)
    def test_link_command_digest_not_raw(self):
        s=MOCKLOG.splitlines()[2].decode()
        x=synthetic()['link_command_fingerprints'][0]
        self.assertEqual(x['line_number'],3)
        self.assertEqual(x['printed_command_sha256'],hashlib.sha256(s.encode()).hexdigest())
    def test_safe_flag_abi(self):
        vals=[x['value'] for x in synthetic()['safe_compile_flag_lines']]
        self.assertIn('-mfloat-abi=hard',vals)
    def test_macro_never_disclosed(self):
        raw=MOCKLOG.replace(b'-fPIC ',b'-fPIC -DSECRET_PASSWORD=TOPSECRET -I/private/folder ')
        d=json.dumps(synthetic(raw))
        self.assertNotIn('TOPSECRET',d)
        self.assertNotIn('-DSECRET_PASSWORD',d)
        self.assertNotIn('/private/',d)
    def test_unique_link_required(self):
        with self.assertRaisesRegex(earlier.AuditHold,'LINK_COUNT'):
            synthetic(MOCKLOG+MOCKLOG.splitlines()[2]+b'\n')
    def test_legacy_compile_only_count(self):
        with self.assertRaisesRegex(earlier.AuditHold,'COMPILE_COUNT'):
            synthetic(MOCKLOG.replace(b' -c ',b' -E '))
    def test_allowlisted_cannot_disclose_paths(self):
        self.assertIsNone(m.SAFE_FLAG.fullmatch('-Wl,-soname,/private/lib.so'))
        self.assertIsNone(m.SAFE_FLAG.fullmatch('-I/private'))
    def test_unknown_driver_is_safe(self):
        tool,_=m.parse_tool('/private/custom/usr/bin/gcc -O2 -c x.c')
        self.assertEqual(tool,'gcc')
        tool,_=m.parse_tool('/private/unknown-compiler -O2')
        self.assertEqual(tool,'driver_unresolved')
    def test_unterminated_quote_not_crash(self):
        self.assertEqual(m.parse_tool("cc '-O2")[0],'unparsed_shell_quoting')
    def test_big_token_count_defended(self):
        self.assertEqual(m.parse_tool('cc '+'x '*2200)[0],'argv_too_long')
    def test_compiler_string_no_version_proof(self):
        d=synthetic();self.assertFalse(d['historical_compiler_linker_executable_versions_verified'])
    def test_static_hold(self):
        self.assertEqual(m.base()['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(m.base()['source_to_binary_reproducibility_verified'])
    def test_fake_log_bad_hash(self):
        with patch.object(m.prior,'analyze',side_effect=mocked_prior):
            with self.assertRaisesRegex(earlier.AuditHold,'SHA256'):
                m.analyze(MOCKLOG,'0'*64,len(MOCKLOG))
    def test_real_prior_not_bypassed(self):
        with self.assertRaises(earlier.AuditHold):m.analyze(MOCKLOG)
    def test_no_subprocess_in_audit_module(self):
        text=Path(m.__file__).read_text()
        self.assertNotIn('subprocess',text)
        self.assertNotIn('os.system',text)
    def test_missing_cli_holds(self):
        with tempfile.TemporaryDirectory() as td:
            p=subprocess.run([sys.executable,'-B',str(Path(m.__file__).resolve()),str(Path(td)/'missing')],capture_output=True,text=True)
            self.assertEqual(p.returncode,2)
            v=json.loads(p.stdout)
            self.assertEqual(v['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
            self.assertEqual(v['kindle_ssh_sessions'],0)

if __name__=='__main__':unittest.main()
