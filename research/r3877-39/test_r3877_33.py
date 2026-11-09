"""R3877.33 offline synthetic tests; never executes shell strings."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import pw3_r3877_31_buildlog_audit as prior
import pw3_r3877_32_2_link_error_taxonomy as previous
import pw3_r3877_33_adjacent_line_triage as m


def h(x): return hashlib.sha256(x.encode()).hexdigest()

class ContinuationTests(unittest.TestCase):
    def test_join_two_lines_lexical_only(self):
        x=m.triage_neighbors(['header','cc -O2 -shared \\','  -nostdlib /private/foo.o'],start_line=2,expected_link_sha256=h('cc -O2 -shared \\'))
        self.assertEqual(x['joined_physical_line_count'],2)
        self.assertEqual(x['lexical_result'],'SHLEX_TOKENIZED_ONLY')
        self.assertEqual(x['shlex_token_count'],5)
        self.assertEqual(x['driver_class'],'cc')
        self.assertEqual(x['allowlisted_flags'],['-O2','-nostdlib','-shared'])
        self.assertFalse(x['complete_historical_shell_command_verified'])
        self.assertNotIn('/private',json.dumps(x))
    def test_hash_is_on_printed_next_line(self):
        x=m.triage_neighbors(['cc -O2 \\','-shared'],start_line=1,expected_link_sha256=h('cc -O2 \\'))
        self.assertEqual(x['following_line_evidence'][0]['printed_line_sha256'],h('-shared'))
    def test_three_line_chain(self):
        x=m.triage_neighbors(['cc -O2 \\', ' -shared \\', ' -nostdlib f.o'],start_line=1,expected_link_sha256=h('cc -O2 \\'))
        self.assertEqual(x['joined_physical_line_count'],3)
        self.assertEqual(x['lexical_result'],'SHLEX_TOKENIZED_ONLY')
        self.assertFalse(x['still_ends_with_unpaired_backslash'])
    def test_odd_even_backslashes(self):
        self.assertTrue(m.trailing_unpaired_backslash('cc a\\'))
        self.assertFalse(m.trailing_unpaired_backslash('cc a\\\\'))
        self.assertTrue(m.trailing_unpaired_backslash('cc a\\\\\\'))
        self.assertFalse(m.trailing_unpaired_backslash('cc a'))
    def test_bad_hash_holds(self):
        with self.assertRaisesRegex(prior.AuditHold,'PINNED_LINK_SHA256_CHANGED'):
            m.triage_neighbors(['cc -shared \\', '-O2'],start_line=1,expected_link_sha256=h('no'))
    def test_no_next_line_holds(self):
        with self.assertRaisesRegex(prior.AuditHold,'FOLLOWING_LINE_MISSING'):
            m.triage_neighbors(['cc \\'],start_line=1,expected_link_sha256=h('cc \\'))
    def test_non_backslash_holds(self):
        with self.assertRaisesRegex(prior.AuditHold,'PINNED_LINK_LINE_NOT_BACKSLASH_TERMINATED'):
            m.triage_neighbors(['cc -shared','-O2'],start_line=1,expected_link_sha256=h('cc -shared'))
    def test_long_line_holds(self):
        with self.assertRaisesRegex(prior.AuditHold,'NEXT_LINE_TOO_LONG'):
            m.triage_neighbors(['cc \\', 'x'*15001],start_line=1,expected_link_sha256=h('cc \\'))
    def test_too_many_unfinished_lines_is_not_claimed_complete(self):
        lines=['cc \\']+[' /a\\']*m.MAX_ADJACENT_LINES+['more']
        x=m.triage_neighbors(lines,start_line=1,expected_link_sha256=h('cc \\'))
        self.assertTrue(x['line_limit_reached'])
        self.assertEqual(x['lexical_result'],'ESCAPE_AT_END_OF_PRINTED_LINE')
        self.assertFalse(x['complete_historical_shell_command_verified'])
    def test_shlex_unterminated_quote_is_not_executed(self):
        y=m.lex_only('cc -shared "unterminated')
        self.assertEqual(y['lexical_result'],'UNTERMINATED_QUOTED_TOKEN')
    def test_too_many_tokens_holds(self):
        with self.assertRaisesRegex(prior.AuditHold,'JOINED_TOO_MANY_TOKENS'):
            m.lex_only('cc '+'a '*4200)
    def test_untrusted_substitution_is_not_executed(self):
        x=m.lex_only('cc $(touch /private/SECRET) `whoami` -O2')
        self.assertNotIn('SECRET',json.dumps(x))
        self.assertEqual(x['allowlisted_flags'],['-O2'])
        self.assertFalse(x['text_was_executed_or_evaluated'])
    def test_nonallowlisted_abi_text_is_not_emitted(self):
        x=m.lex_only('cc -mfloat-abi=evil/secret -march=armv7-a -O2')
        self.assertEqual(x['allowlisted_flags'],['-O2','-march=armv7-a'])
        self.assertNotIn('evil',json.dumps(x))
    def test_missing_line_holds(self):
        with self.assertRaisesRegex(prior.AuditHold,'PINNED_LINK_LINE_MISSING'):
            m.triage_neighbors([],start_line=1,expected_link_sha256=h('x'))
    def test_base_preserves_not_bootable(self):
        x=m.base();self.assertEqual(x['immutable_hold'],'NOT_BOOTABLE')
        self.assertEqual(x['kindle_ssh_sessions'],0)
        self.assertFalse(x['binary_execution_performed'])
        self.assertFalse(x['recovery_verified'])
    def test_does_not_import_execution_tools(self):
        code=Path(m.__file__).read_text()
        for name in ('subprocess','os.system','eval(','exec(','socket','paramiko'):
            self.assertNotIn(name,code)
    def test_cli_missing_file_hold(self):
        with tempfile.TemporaryDirectory() as td:
            proc=subprocess.run([sys.executable,'-B',m.__file__,str(Path(td)/'absent')],capture_output=True,text=True)
        self.assertEqual(proc.returncode,2)
        d=json.loads(proc.stdout)
        self.assertEqual(d['result'],'HOLD')
        self.assertEqual(d['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
    def test_cli_symlink_hold(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a';p.write_text('x')
            s=Path(td)/'b';s.symlink_to(p)
            proc=subprocess.run([sys.executable,'-B',m.__file__,str(s)],capture_output=True,text=True)
        self.assertEqual(proc.returncode,2)
        self.assertEqual(json.loads(proc.stdout)['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
    def test_analyzer_require_exact_prior_classification(self):
        raw=b'line1\ncc -O2 \\\n-more\n'
        baseline={'error_kind':'UNTERMINATED_QUOTED_TOKEN', 'complete_prefix_tokens_before_error':66,
                  'printed_line_ends_with_unpaired_backslash':True,'link_line_sha256_verified':True,'log_sha256_verified':True}
        with patch.object(previous,'analyze',return_value=baseline):
            with self.assertRaisesRegex(prior.AuditHold,'PRIOR_LEXER_ERROR_CHANGED'):
                m.analyze(raw,expected_link_number=2,expected_link_hash=h('cc -O2 \\'))
    def test_analyzer_on_synthetic_baseline(self):
        first='cc -O2 -shared \\'
        raw=('intro\n'+first+'\n-nostdlib file.o\n').encode()
        baseline={'error_kind':'ESCAPE_AT_END_OF_PRINTED_LINE', 'complete_prefix_tokens_before_error':66,
                  'printed_line_ends_with_unpaired_backslash':True,'link_line_sha256_verified':True,'log_sha256_verified':True}
        with patch.object(previous,'analyze',return_value=baseline):
            x=m.analyze(raw,expected_link_number=2,expected_link_hash=h(first))
        self.assertEqual(x['lexical_result'],'SHLEX_TOKENIZED_ONLY')
        self.assertTrue(x['hash_pins_and_prior_classifications_rechecked'])
        self.assertFalse(x['historical_builder_complete_link_invocation_verified'])
    def test_hash_stable(self):
        first='cc -O2 \\'
        x=m.triage_neighbors([first, ' -shared'],start_line=1,expected_link_sha256=h(first))
        self.assertEqual(x['joined_text_sha256'],h('cc -O2  -shared'))

if __name__=='__main__': unittest.main()
