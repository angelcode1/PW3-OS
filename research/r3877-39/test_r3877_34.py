"""R3877.34 host-only synthetic regression tests, no real public log embedded."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pw3_r3877_31_buildlog_audit as r31
import pw3_r3877_33_1_long_neighbor_triage as r331
import pw3_r3877_34_pinned_link_structure as m


def sha(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


class StructureTests(unittest.TestCase):
    def test_does_not_return_names_or_raw_tokens(self):
        values = m.count_structure(['cc', '-shared', '-nostdlib', '-o',
                                    '/private/user/secret.so', '/path/my_secret.o',
                                    '/path/libstuff.a', '-Wl,--hash-style=both'])
        self.assertEqual(values['explicit_output_switch_count'], 1)
        self.assertEqual(values['token_classes']['object_like'], 1)
        self.assertEqual(values['token_classes']['static_archive_like'], 1)
        self.assertEqual(values['token_classes']['shared_library_like'], 1)
        out = json.dumps(values)
        self.assertNotIn('private', out)
        self.assertNotIn('my_secret', out)
        self.assertNotIn('libstuff', out)
        self.assertFalse(values['shell_expressions_evaluated'])
    def test_shell_markers_not_evaluated(self):
        values = m.count_structure(['cc', '$(echo /private/file)', '${PRIVATE}', '`rm -rf /`', ';'])
        self.assertEqual(values['printed_shell_expansion_marker_token_count'], 3)
        self.assertEqual(values['printed_shell_metacharacter_token_count'], 1)
        self.assertNotIn('private', json.dumps(values).lower())
    def test_distinguish_link_options_from_obj_files(self):
        values = m.count_structure(['cc', '-O2', '-shared', '-nostdlib', '-lcrypto', '-L/safe',
                                    '/some/a.lo', '/some/b.o', '/a.so.1', '-Wl,--hash-style=both'])
        self.assertEqual(values['token_classes']['object_like'], 2)
        self.assertEqual(values['token_classes']['shared_library_like'], 1)
        self.assertEqual(values['token_classes']['link_by_name_options'], 1)
        self.assertEqual(values['token_classes']['library_search_options'], 1)
        self.assertIn('-shared', values['allowlisted_flags'])
    def test_incomplete_output_switch_only_reports_false(self):
        r = m.count_structure(['cc', '-o'])
        self.assertEqual(r['explicit_output_switch_count'], 1)
        self.assertFalse(r['explicit_output_switches_have_following_non_option'])
    def test_token_budget_holds(self):
        with self.assertRaisesRegex(r31.AuditHold, 'JOINED_TOKEN_BUDGET_REACHED'):
            m.tokenize_no_execution('cc ' + '-O2 ' * (m.MAX_TOKENS + 1))
    def test_invalid_token_type_holds(self):
        with self.assertRaisesRegex(r31.AuditHold, 'TOKEN_SIZE_OR_TYPE_INVALID'):
            m.count_structure(['cc', None])
    def test_lexical_quote_failure_holds(self):
        with self.assertRaisesRegex(r31.AuditHold, 'JOINED_SHLEX_NOT_COMPLETE'):
            m.tokenize_no_execution("cc -O2 'broken")
    def test_whitespace_does_not_execute(self):
        t = m.tokenize_no_execution('cc -O2 \\$(printf do-not-run) -shared')
        self.assertEqual(t[0], 'cc')
        self.assertEqual(t[-1], '-shared')
    def test_historical_flags_never_set_by_static_pass(self):
        d = m.base()
        for x in ('historical_builder_complete_link_invocation_verified',
                  'historical_builder_toolchain_versions_verified',
                  'source_to_binary_reproducibility_verified',
                  'target_musl_runtime_verified'):
            self.assertFalse(d[x])
        self.assertEqual(d['immutable_hold'], 'NOT_BOOTABLE')
    def test_missing_file_holds(self):
        with tempfile.TemporaryDirectory() as td:
            x = subprocess.run([sys.executable, '-B', m.__file__, str(Path(td)/'notfound')],
                               capture_output=True, text=True)
        self.assertEqual(x.returncode, 2)
        self.assertEqual(json.loads(x.stdout)['hold_category'], 'LOG_FILE_MISSING_OR_SYMLINK')
    def test_symlink_holds(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)/'original'; target.write_text('fake')
            link = Path(td)/'link'; link.symlink_to(target)
            x = subprocess.run([sys.executable, '-B', m.__file__, str(link)],
                               capture_output=True, text=True)
        self.assertEqual(x.returncode, 2)
    def test_partial_user_report_does_not_override_pins(self):
        self.assertEqual(m.PINNED_LEX_TOKENS, 1494)
        self.assertEqual(m.PINNED_JOINED_CHARS, 40671)
    def test_no_forbidden_api_in_source(self):
        raw=Path(m.__file__).read_text()
        for forbidden in ('import subprocess', 'import os\n', 'import socket',
                          'eval(', 'exec(', 'Popen(', 'os.system(', 'getenv(', 'ssh '):
            self.assertNotIn(forbidden, raw)
    def test_source_is_not_applied_to_device(self):
        self.assertFalse(m.base()['new_kindle_binary_installed_or_executed'])
        self.assertEqual(m.base()['kindle_ssh_sessions'],0)


class SyntheticBoundAudit(unittest.TestCase):
    def payload(self):
        a = 'cc -O2 -shared \\'
        b = ' -nostdlib -o out/lib.so sub/obj1.o sub/obj2.o -Wl,--hash-style=both'
        joined = a[:-1]+b
        raw = (a+'\n'+b+'\n').encode()
        expected_count=len(m.tokenize_no_execution(joined))
        prior={'lexical_result':'SHLEX_TOKENIZED_CANDIDATE_ONLY',
               'following_line_count_observed':1,
               'following_line_evidence':[{'printed_line_sha256':sha(b)}],
               'joined_text_sha256_if_lexed':sha(joined),
               'joined_text_character_count_if_lexed':len(joined),
               'lexical_token_count_bounded':expected_count,
               'driver_class':'cc'}
        return a,b,joined,raw,prior,expected_count
    def run_audit(self, **kwargs):
        a,b,j,raw,prior,c=self.payload()
        opts={'expected_hash':hashlib.sha256(raw).hexdigest(),'expected_length':len(raw),
              'link_line_number':1,'link_line_hash':sha(a),'next_line_hash':sha(b),
              'joined_hash':sha(j),'joined_chars':len(j),'expected_tokens':c}
        opts.update(kwargs)
        with patch.object(r331,'analyze',return_value=prior):
            return m.analyze(raw,**opts)
    def test_exact_join_candidate_synthetic_pass(self):
        result=self.run_audit()
        self.assertEqual(result['joined_physical_lines'],2)
        self.assertEqual(result['driver_class'],'cc')
        self.assertEqual(result['token_classes']['object_like'],2)
        self.assertFalse(result['historical_builder_complete_link_invocation_verified'])
    def test_adjacent_hash_mismatch_refuses(self):
        with self.assertRaisesRegex(r31.AuditHold,'NEXT_LINE_SHA256_CHANGED'):
            self.run_audit(next_line_hash='0'*64)
    def test_joined_hash_mismatch_refuses(self):
        with self.assertRaisesRegex(r31.AuditHold,'JOINED_TEXT_SHA256_CHANGED'):
            self.run_audit(joined_hash='0'*64)
    def test_token_count_mismatch_refuses(self):
        with self.assertRaisesRegex(r31.AuditHold,'PRIOR_JOINED_TOKEN_COUNT_CHANGED'):
            self.run_audit(expected_tokens=999)
    def test_driver_mismatch_refuses(self):
        a,b,j,raw,prior,c = self.payload();prior['driver_class']='ld'
        with patch.object(r331,'analyze',return_value=prior):
            with self.assertRaisesRegex(r31.AuditHold,'PRIOR_PRINTED_DRIVER_CHANGED'):
                m.analyze(raw, expected_hash=hashlib.sha256(raw).hexdigest(),
                          expected_length=len(raw), link_line_number=1,
                          link_line_hash=sha(a),next_line_hash=sha(b),
                          joined_hash=sha(j),joined_chars=len(j),expected_tokens=c)


if __name__ == '__main__':
    unittest.main()
