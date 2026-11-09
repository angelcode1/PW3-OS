"""R3877.32.1: synthetic offline quote and hash-pin regression tests."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pw3_r3877_31_buildlog_audit as m31
import pw3_r3877_32_log_command_shapes as m32
import pw3_r3877_32_1_link_lexical_diagnostic as m

MOCK = (b'>>> musl: Building musl-1.2.6-r3\n'
        b'cc -O2 -fPIC -c /private/work/secret.c -o /private/x.o\n'
        b'cc -O2 -Wl,-soname,libc.musl-armv7.so.1 -shared -o /private/libc.so "broken\n'
        b'>>> musl: Build complete\n')


def baseline_stub(raw, expected_hash, expected_length):
    if len(raw) != expected_length or hashlib.sha256(raw).hexdigest() != expected_hash:
        raise m31.AuditHold('LOG_SHA256_MISMATCH')
    return {'log_line_count':1981,'likely_compile_lines':m32.EXPECTED_COMPILE,'likely_link_lines':m32.EXPECTED_LINK,
            'compiler_like_lines_with_flags':1429,
            'allowlisted_flags':[{'flag':key,'observed_line_count':value}
                                 for key,value in m32.EXPECTED_FLAG_COUNTS.items()]}


def synthetic(raw=MOCK, link_line=3):
    line = raw.splitlines()[link_line-1].decode().strip()
    with patch.object(m32.prior, 'analyze', side_effect=baseline_stub), \
         patch.object(m32, 'EXPECTED_COMPILE', 1), \
         patch.object(m32, 'EXPECTED_LINK', 1):
        return m.analyze(raw, hashlib.sha256(raw).hexdigest(), len(raw),
                         hashlib.sha256(line.encode()).hexdigest(), link_line, expected_compile_count=1)


class LexicalDiagnostics(unittest.TestCase):
    def test_lexical_unterminated_double(self):
        x=synthetic();self.assertEqual(x['lexical_result'],'UNTERMINATED_DOUBLE_QUOTE')
        self.assertEqual(x['prefix_driver_class'],'cc')
        self.assertFalse(x['complete_shell_tokenization'])
        self.assertIn('-Wl,-soname,libc.musl-armv7.so.1',x['allowlisted_prefix_flags'])
    def test_quote_single(self):
        self.assertEqual(m.summarize_link("cc -shared -O2 'bad")['lexical_result'],'UNTERMINATED_SINGLE_QUOTE')
    def test_quote_none_complete(self):
        x=m.summarize_link('armv7-linux-musleabihf-gcc -O2 -shared')
        self.assertEqual(x['lexical_result'],'TOKENIZED_WITH_SHLEX_NOT_SHELL_SEMANTICS')
        self.assertEqual(x['prefix_driver_class'],'target-prefixed-gcc')
    def test_nested_backslash(self):
        self.assertEqual(m._end_quote_state("cc -shared \\\"foo\\\""),'none')
    def test_macro_not_leaked(self):
        x=m.summarize_link('cc -shared -DAPI_TOKEN=TOP_SECRET -I/private/cache -O2 "dangling')
        z=json.dumps(x);self.assertNotIn('TOP_SECRET',z);self.assertNotIn('/private/',z)
    def test_flags_whitelist_only(self):
        x=m.summarize_link('cc -shared -mfloat-abi=hard -march=armv7-a -Wl,-z,relro -DSECRET=1')
        self.assertIn('-mfloat-abi=hard',x['allowlisted_prefix_flags'])
        self.assertNotIn('-DSECRET=1',json.dumps(x))
    def test_untrusted_substitutions_never_run(self):
        x=m.summarize_link('cc -shared $(touch /private/path) `echo hidden` -O2')
        self.assertTrue(x['untrusted_command_substitutions_not_evaluated'])
        self.assertNotIn('/private/path',json.dumps(x))
    def test_no_unverified_compiler_proof(self):
        self.assertFalse(synthetic()['historical_builder_linker_binary_and_version_verified'])
    def test_pin_hash(self):
        with patch.object(m32.prior,'analyze',side_effect=baseline_stub), \
             patch.object(m32,'EXPECTED_COMPILE',1),patch.object(m32,'EXPECTED_LINK',1):
            with self.assertRaisesRegex(m31.AuditHold,'FINGERPRINT'):
                m.analyze(MOCK,hashlib.sha256(MOCK).hexdigest(),len(MOCK),'0'*64,3,expected_compile_count=1)
    def test_count_change_hold(self):
        with self.assertRaises(m31.AuditHold):
            synthetic(MOCK + b'cc -O2 -shared -o another\n')
    def test_unknown_driver(self):
        self.assertEqual(m.summarize_link('/private/strange-wrapper -O2 -shared')['prefix_driver_class'],'driver_unresolved')
    def test_shell_comment_not_execute(self):
        x=m.summarize_link('cc -shared -O2 #not-an-argument')
        self.assertEqual(x['prefix_driver_class'],'cc')
    def test_invalid_text_length(self):
        with self.assertRaisesRegex(m31.AuditHold,'TOO_LONG'):m.summarize_link('x'*15001)
    def test_too_many_tokens(self):
        with self.assertRaisesRegex(m31.AuditHold,'TOO_MANY_TOKENS'):
            m.summarize_link('cc '+'x '*2049)
    def test_fail_closed_unpinned_log(self):
        with self.assertRaises(m31.AuditHold):m.analyze(MOCK)
    def test_no_file_writes_in_module(self):
        code=Path(m.__file__).read_text()
        for term in ('subprocess', 'os.system(','.write_text(','.write_bytes('):self.assertNotIn(term,code)
    def test_cli_missing_holds(self):
        with tempfile.TemporaryDirectory() as td:
            p=subprocess.run([sys.executable,'-B',str(Path(m.__file__).resolve()),str(Path(td)/'missing')],capture_output=True,text=True)
            self.assertEqual(p.returncode,2)
            obj=json.loads(p.stdout)
            self.assertEqual(obj['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
            self.assertEqual(obj['kindle_ssh_sessions'],0)
    def test_report_not_bootable(self):
        self.assertEqual(m.base()['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(m.base()['target_musl_runtime_verified'])


if __name__=='__main__':unittest.main()
