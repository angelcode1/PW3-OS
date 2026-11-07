"""Host-only synthetic regression tests for R3877.32.2 error categorization."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pw3_r3877_31_buildlog_audit as m31
import pw3_r3877_32_1_link_lexical_diagnostic as m321
import pw3_r3877_32_2_link_error_taxonomy as m


class LexerErrorTests(unittest.TestCase):
    def test_trailing_escape_without_quote(self):
        x = m.trace_lexer('cc -shared -O2 -o /something\\')
        self.assertEqual(x['error_kind'],'ESCAPE_AT_END_OF_PRINTED_LINE')
        self.assertTrue(x['printed_line_ends_with_unpaired_backslash'])
        self.assertEqual(x['end_quote_state'],'none')
        self.assertEqual(x['complete_prefix_tokens_before_error'],4)
    def test_unterminated_quote(self):
        x = m.trace_lexer('cc -O2 -shared "missing')
        self.assertEqual(x['error_kind'],'UNTERMINATED_QUOTED_TOKEN')
        self.assertEqual(x['end_quote_state'],'double')
    def test_unterminated_single_quote(self):
        x = m.trace_lexer("cc -O2 'open")
        self.assertEqual(x['error_kind'],'UNTERMINATED_QUOTED_TOKEN')
        self.assertEqual(x['end_quote_state'],'single')
    def test_even_backslashes_are_not_unpaired(self):
        x = m.trace_lexer('cc -shared a\\\\')
        self.assertEqual(x['error_kind'],'NO_LEXICAL_ERROR')
        self.assertFalse(x['printed_line_ends_with_unpaired_backslash'])
        self.assertTrue(x['printed_line_ends_with_backslash'])
    def test_complete_nonexecuted(self):
        x = m.trace_lexer('cc -O2 -shared /tmp/a.o')
        self.assertEqual(x['error_kind'],'NO_LEXICAL_ERROR')
        self.assertFalse(x['printed_command_complete_and_executable'])
        self.assertIsNone(x['lexer_stopped_at_character_offset'])
    def test_do_not_execute_substitutions(self):
        x = m.trace_lexer('cc -shared $(touch /danger/private) `whoami` -O2')
        self.assertNotIn('/danger',json.dumps(x))
        self.assertEqual(x['error_kind'],'NO_LEXICAL_ERROR')
    def test_value_error_is_allowlisted(self):
        self.assertEqual(m.lexical_failure_kind(ValueError('other /tmp/private')), 'OTHER_LEXER_ERROR')
        self.assertEqual(m.lexical_failure_kind(ValueError('No escaped character')),'ESCAPE_AT_END_OF_PRINTED_LINE')
    def test_no_raw_paths_in_summary(self):
        x = m.trace_lexer('cc -shared -Wl,-z,relro /private/ab\\')
        self.assertNotIn('private',json.dumps(x))
    def test_input_size_limit(self):
        with self.assertRaises(m31.AuditHold):m.trace_lexer('a'*15001)
    def test_token_limit(self):
        with self.assertRaises(m31.AuditHold):m.trace_lexer('cc '+'x '*2100)
    def test_quote_state_none_doesnt_claim_executable(self):
        x=m.trace_lexer('cc -O2 -shared trailing\\')
        self.assertEqual(x['end_quote_state'],'none')
        self.assertFalse(x['printed_command_complete_and_executable'])
    def test_base_hold(self):
        x=m.base()
        self.assertEqual(x['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(x['source_to_binary_reproducibility_verified'])
        self.assertEqual(x['kindle_ssh_sessions'],0)
    def test_fail_closed_missing_log(self):
        with tempfile.TemporaryDirectory() as d:
            p=subprocess.run([sys.executable,'-B',str(Path(m.__file__).resolve()),str(Path(d)/'notfound')],capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        o=json.loads(p.stdout)
        self.assertEqual(o['result'],'HOLD')
        self.assertEqual(o['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
    def test_no_subprocess_exec_file_access_module(self):
        code=Path(m.__file__).read_text()
        self.assertNotIn('subprocess',code)
        self.assertNotIn('eval(',code)
        self.assertNotIn('os.system',code)
    def test_baseline_rechecks_line_hash(self):
        content=b'line stuff\n'
        with patch.object(m321,'analyze',side_effect=m31.AuditHold('LINK_COMMAND_FINGERPRINT_MISMATCH')):
            with self.assertRaisesRegex(m31.AuditHold,'LINK_COMMAND_FINGERPRINT_MISMATCH'):
                m.analyze(content, expected_hash=hashlib.sha256(content).hexdigest(),expected_length=len(content))
    def test_success_mock_pinned_trailing_escape(self):
        line='cc -O2 -shared /private/ld\\'
        raw=f'test\n{line}\n'.encode()
        baseline={'complete_prefix_token_count':3,'end_quote_state':'none','complete_shell_tokenization':False,
                  'prefix_driver_class':'cc','allowlisted_prefix_flags':['-O2','-shared'],'lexical_result':'SHELL_TOKENIZATION_ERROR'}
        with patch.object(m321,'analyze',return_value=baseline):
            x=m.analyze(raw, expected_hash=hashlib.sha256(raw).hexdigest(),expected_length=len(raw),
                        expected_link_hash=hashlib.sha256(line.encode()).hexdigest(),expected_link_number=2)
        self.assertEqual(x['error_kind'],'ESCAPE_AT_END_OF_PRINTED_LINE')
        self.assertTrue(x['prior_r3877_32_1_reconciled'])
        self.assertNotIn('private',json.dumps(x))
    def test_fail_closed_prefix_mismatch(self):
        line='cc -O2 -shared /private/ld\\'
        raw=f'test\n{line}\n'.encode()
        baseline={'complete_prefix_token_count':4,'end_quote_state':'none','complete_shell_tokenization':False,
                  'prefix_driver_class':'cc','allowlisted_prefix_flags':[],'lexical_result':'SHELL_TOKENIZATION_ERROR'}
        with patch.object(m321,'analyze',return_value=baseline):
            with self.assertRaisesRegex(m31.AuditHold,'LEXER_PREFIX_TOKENS_CHANGED'):
                m.analyze(raw,expected_link_hash=hashlib.sha256(line.encode()).hexdigest(),expected_link_number=2)
    def test_unknown_error_does_not_leak(self):
        self.assertEqual(m.lexical_failure_kind(Exception('/secret')), 'OTHER_LEXER_ERROR')


if __name__ == '__main__':unittest.main()
