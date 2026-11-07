"""Offline tests for R3877.33.1. Synthetic lines only, no real log needed."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pw3_r3877_31_buildlog_audit as prior
import pw3_r3877_32_2_link_error_taxonomy as old
import pw3_r3877_33_1_long_neighbor_triage as m


def digest(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


class LongLineTests(unittest.TestCase):
    def test_previous_15000_limit_is_observation_not_hold(self):
        neighbor = '  ' + 'x'*15001
        result = m.triage_neighbors(['cc -O2 \\', neighbor],start_line=1,
                                    expected_link_sha256=digest('cc -O2 \\'))
        self.assertTrue(result['any_neighbor_exceeds_old_limit'])
        self.assertEqual(result['following_line_evidence'][0]['character_count'],len(neighbor))
        self.assertEqual(result['following_line_evidence'][0]['printed_line_sha256'],digest(neighbor))
        self.assertEqual(result['lexical_result'],'SHLEX_TOKENIZED_CANDIDATE_ONLY')
        self.assertFalse(result['complete_historical_shell_command_verified'])
    def test_oversized_nextline_hashes_but_does_not_lex_partial_prefix(self):
        neighbor=' ' + '/not-to-be-disclosed/' + 'q'*(m.MAX_LEX_JOIN_CHARS+1)
        result=m.triage_neighbors(['cc -O2 \\',neighbor],start_line=1,
                                  expected_link_sha256=digest('cc -O2 \\'))
        self.assertEqual(result['lexical_result'],'NOT_LEXED_OVERSIZED_PRINTED_NEIGHBOR')
        self.assertEqual(result['bounded_lex_stop_reason'],'PRINTED_NEIGHBOR_EXCEEDS_SAFE_LEX_BOUND')
        self.assertIsNone(result['joined_text_sha256_if_lexed'])
        self.assertIsNone(result['joined_physical_line_count_if_lexed'])
        self.assertNotIn('not-to-be-disclosed',json.dumps(result))
    def test_short_normal_two_lines_preserved(self):
        result=m.triage_neighbors(['cc -O2 \\', ' -shared -nostdlib file.o'],start_line=1,
                                  expected_link_sha256=digest('cc -O2 \\'))
        self.assertEqual(result['joined_physical_line_count_if_lexed'],2)
        self.assertEqual(result['allowlisted_flags_from_lexed_tokens'],['-O2','-nostdlib','-shared'])
    def test_short_multi_line_still_bounded(self):
        result=m.triage_neighbors(['cc \\',' -O2 \\',' -shared'],start_line=1,
                                  expected_link_sha256=digest('cc \\'))
        self.assertEqual(result['joined_physical_line_count_if_lexed'],3)
    def test_escape_continues_for_five_lines(self):
        lines=['cc \\']+[' -O2 \\']*5+[' -shared']
        result=m.triage_neighbors(lines,start_line=1,expected_link_sha256=digest('cc \\'))
        self.assertTrue(result['adjacent_line_limit_reached'])
        self.assertEqual(result['following_line_count_observed'],5)
    def test_token_budget_is_classification_not_false_complete(self):
        report=m.lex_candidate('cc '+'-O2 '*m.MAX_TOKENS)
        self.assertEqual(report['lexical_result'],'SHLEX_TOKEN_BUDGET_REACHED')
        self.assertFalse(report['complete_historical_shell_command_verified'])
    def test_quoted_shell_expression_is_not_executed_or_disclosed(self):
        report=m.triage_neighbors(['cc \\', ' $(touch /private/secret) -O2'],start_line=1,
                                  expected_link_sha256=digest('cc \\'))
        self.assertNotIn('/private',json.dumps(report))
        self.assertFalse(report['untrusted_shell_substitutions_evaluated'])
    def test_wrong_start_hash_holds(self):
        with self.assertRaisesRegex(prior.AuditHold,'PINNED_LINK_SHA256_CHANGED'):
            m.triage_neighbors(['cc \\',' tail'],start_line=1,expected_link_sha256=digest('WRONG'))
    def test_noncontinuation_holds(self):
        with self.assertRaisesRegex(prior.AuditHold,'PINNED_LINK_NOT_UNPAIRED_BACKSLASH_TERMINATED'):
            m.triage_neighbors(['cc',' tail'],start_line=1,expected_link_sha256=digest('cc'))
    def test_no_following_line_holds(self):
        with self.assertRaisesRegex(prior.AuditHold,'PINNED_LINK_OR_FOLLOWING_LINE_MISSING'):
            m.triage_neighbors(['cc \\'],start_line=1,expected_link_sha256=digest('cc \\'))
    def test_missing_file_exit_hold(self):
        with tempfile.TemporaryDirectory() as td:
            result=subprocess.run([sys.executable,'-B',m.__file__,str(Path(td)/'none')],
                                  capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
    def test_symlink_exit_hold(self):
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'target';target.write_text('fake')
            link=Path(td)/'link';link.symlink_to(target)
            result=subprocess.run([sys.executable,'-B',m.__file__,str(link)],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
    def test_baseline_error_must_match(self):
        base={'error_kind':'OTHER_LEXER_ERROR', 'complete_prefix_tokens_before_error':66,
              'printed_line_ends_with_unpaired_backslash':True,
              'link_line_sha256_verified':True,'log_sha256_verified':True}
        with patch.object(old,'analyze',return_value=base):
            with self.assertRaisesRegex(prior.AuditHold,'PRIOR_LEXICAL_ERROR_CHANGED'):
                m.analyze(b'hello',expected_link_number=1,expected_link_hash=digest('hello'))
    def test_synthetic_baseline_complete(self):
        base={'error_kind':'ESCAPE_AT_END_OF_PRINTED_LINE', 'complete_prefix_tokens_before_error':66,
              'printed_line_ends_with_unpaired_backslash':True,
              'link_line_sha256_verified':True,'log_sha256_verified':True}
        with patch.object(old,'analyze',return_value=base):
            result=m.analyze(b'cc \\\n -O2 -shared\n',expected_link_number=1,
                             expected_link_hash=digest('cc \\'))
        self.assertEqual(result['lexical_result'],'SHLEX_TOKENIZED_CANDIDATE_ONLY')
        self.assertTrue(result['prior_r3877_32_2_hash_pins_revalidated'])
    def test_no_execution_modules_in_new_script(self):
        s=Path(m.__file__).read_text()
        for forbidden in ('import subprocess','import os','eval(','exec(','socket','paramiko'):
            self.assertNotIn(forbidden,s)
    def test_always_not_bootable(self):
        b=m.base()
        self.assertEqual(b['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(b['source_to_binary_reproducibility_verified'])
        self.assertFalse(b['historical_builder_complete_link_invocation_verified'])

if __name__=='__main__': unittest.main()
