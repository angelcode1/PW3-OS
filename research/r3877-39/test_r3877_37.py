"""Synthetic offline R3877.37 tests; never uses actual builder log or ARM code."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pw3_r3877_31_buildlog_audit as r31
import pw3_r3877_35_object_link_consistency as r35
import pw3_r3877_36_unlinked_compile_triage as r36
import pw3_r3877_37_auxiliary_context_audit as m

FILES=['private/a.o','private/b.o','private/c.o','private/d.o','private/e.o']


def make_lines():
    lines=['']*556
    for i, name in enumerate(FILES):
        lines[i]='cc -c private/s.c -o '+name
    lines[100]='cp private/a.o /out'
    lines[101]='install -m 644 private/b.o private/c.o /out'
    lines[102]='strip private/d.o'
    lines[103]='objcopy private/e.o /out'
    lines[105]='a'*270000  # safely classified as unparsed, not truncated into tokens
    return lines


class R37Tests(unittest.TestCase):
    def test_families(self):
        for cmd, expected in [('cp','copy'),('mv','move'),('install','install'),
                              ('strip','binary_tool'),('objcopy','binary_tool'),
                              ('ar','archive'),('ranlib','archive'),
                              ('gcc','compiler_or_linker'),('ld','compiler_or_linker')]:
            self.assertEqual(m.family([cmd,'x.o']),expected)
    def test_no_subcommand_scanning(self):
        self.assertEqual(m.family(['echo','cp','secret.o']),'other_or_unresolved')
        self.assertEqual(m.family(['sh','-c','cp secret.o']),'other_or_unresolved')
    def test_no_suspicious_words_reported(self):
        self.assertEqual(m.family(['$(touch','secret.o']),'other_or_unresolved')
    def test_printed_argument_positions(self):
        self.assertEqual(m.role(['cp','x.o','dst'],1,'copy'),'earlier_argument_candidate')
        self.assertEqual(m.role(['cp','src','x.o'],2,'copy'),'final_argument_candidate')
        self.assertEqual(m.role(['strip','x.o'],1,'binary_tool'),'role_unverified')
        self.assertEqual(m.role(['cp','-t','dst','x.o'],3,'copy'),'role_unverified')
        self.assertEqual(m.role(['cp','--target-directory=dst','x.o'],2,'copy'),'role_unverified')
    def test_role_position_oob_holds(self):
        with self.assertRaises(r31.AuditHold):
            m.role(['cp'],2,'copy')
    def test_all_five_aggregate_without_paths(self):
        data=m.private_context(make_lines(),FILES,{1,2,3,4,5})
        self.assertEqual(data['nonmain_lines_scanned'],551)
        self.assertEqual(data['nonmain_lines_not_lexically_parsed'],1)
        self.assertEqual(data['nonmain_lines_with_extra_object_mentions'],4)
        self.assertEqual(data['exact_printed_object_token_mentions'],5)
        self.assertEqual(data['extra_objects_with_any_exact_printed_mention'],5)
        self.assertEqual(data['printed_command_family_mention_counts'],{
            'binary_tool':2,'copy':1,'install':2})
        self.assertEqual(data['printed_argument_position_candidate_counts'],{
            'earlier_argument_candidate':3,'role_unverified':2})
        self.assertNotIn('private/',json.dumps(data))
        self.assertNotIn('/out',json.dumps(data))
    def test_repeated_mentions_counted_distinct_not_inflated(self):
        lines=make_lines()
        lines[110]='cp private/a.o private/a.o /somewhere'
        data=m.private_context(lines,FILES,{1,2,3,4,5})
        self.assertEqual(data['exact_printed_object_token_mentions'],7)
        self.assertEqual(data['extra_objects_with_any_exact_printed_mention'],5)
        self.assertEqual(data['printed_command_family_distinct_object_counts']['copy'],1)
    def test_substring_only_is_not_a_mention(self):
        lines=make_lines(); lines[100]='cp private/a.o-suffix /other'
        with self.assertRaisesRegex(r31.AuditHold,'NOT_ALL_FIVE_OBJECTS_RECOGNIZED'):
            m.private_context(lines,FILES,{1,2,3,4,5})
    def test_missing_object_holds(self):
        with self.assertRaisesRegex(r31.AuditHold,'FIVE_DISTINCT_OBJECTS_REQUIRED'):
            m.private_context([],['x.o'],set())
    def test_unparsed_budget_change_holds(self):
        lines=make_lines();lines[105]='short text'
        with self.assertRaisesRegex(r31.AuditHold,'NONMAIN_UNPARSED_LINE_COUNT_CHANGED'):
            m.private_context(lines,FILES,{1,2,3,4,5})
    def test_scanned_line_count_change_holds(self):
        with self.assertRaisesRegex(r31.AuditHold,'NONMAIN_SCANNED_LINE_COUNT_CHANGED'):
            m.private_context(make_lines()+['new'],FILES,{1,2,3,4,5})
    def test_line_budget_holds(self):
        with self.assertRaisesRegex(r31.AuditHold,'LINE_COUNT_BUDGET'):
            m.private_context(['']*3001,FILES,set())
    def test_prior_hold_precedes_new_audit(self):
        with patch.object(r36,'analyze',side_effect=r31.AuditHold('HASH_MISMATCH')):
            with self.assertRaisesRegex(r31.AuditHold,'HASH_MISMATCH'):
                m.analyze(b'untrusted')
    def test_prior_classification_mismatch_holds(self):
        prior={'printed_compile_outputs_not_in_main_link':5,
               'unmatched_printed_main_link_objects':0,
               'other_printed_lines_scanned':551,
               'other_printed_lines_not_lexically_parsed':1,
               'unlinked_outputs_with_full_token_mentions_outside_compile_or_main_link':5,
               'extra_printed_token_mentions_by_generic_context':{'archive_tool_like':5}}
        with patch.object(r36,'analyze',return_value=prior):
            with self.assertRaisesRegex(r31.AuditHold,'PRIOR_R3877_36_'):
                m.analyze(b'fake')
    def test_integration_sanitized(self):
        prior={'printed_compile_outputs_not_in_main_link':5,
               'unmatched_printed_main_link_objects':0,
               'other_printed_lines_scanned':551,
               'other_printed_lines_not_lexically_parsed':1,
               'unlinked_outputs_with_full_token_mentions_outside_compile_or_main_link':5,
               'extra_printed_token_mentions_by_generic_context':{
                   'copy_install_or_binary_tool_like':5}}
        records=[{'output':f'private/{i}.o','line_number':i+1}
                 for i in range(1428)]
        with patch.object(r36,'analyze',return_value=prior), \
             patch.object(r36,'extract_records',return_value=(['']*1981,records)), \
             patch.object(r35,'link_tokens_from_pinned',return_value=['cc']), \
             patch.object(r36,'reconcile_records',return_value=([{'output':x} for x in FILES],{})), \
             patch.object(m,'private_context',return_value={
                 'extra_objects_with_any_exact_printed_mention':5}):
            result=m.analyze(b'mock')
        self.assertEqual(result['extra_compile_output_count'],5)
        self.assertFalse(result['source_to_binary_reproducibility_verified'])
        self.assertNotIn('private/',json.dumps(result))
    def test_no_runtime_execution_calls(self):
        code=Path(m.__file__).read_text()
        for s in ('import subprocess','import os\n','eval(', 'exec(', 'Popen(',
                  'os.system(', 'ssh root@','docker run'):
            self.assertNotIn(s,code)
    def test_missing_log_keeps_hold(self):
        with tempfile.TemporaryDirectory() as td:
            p=subprocess.run([sys.executable,'-B',m.__file__,str(Path(td)/'missing')],
                             capture_output=True,text=True,check=False)
        self.assertEqual(p.returncode,2)
        result=json.loads(p.stdout)
        self.assertEqual(result['result'],'HOLD')
        self.assertEqual(result['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
        self.assertEqual(result['immutable_hold'],'NOT_BOOTABLE')
    def test_symlink_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            real=Path(td)/'file';real.write_text('test')
            symlink=Path(td)/'sym';symlink.symlink_to(real)
            p=subprocess.run([sys.executable,'-B',m.__file__,str(symlink)],
                             capture_output=True,text=True)
        self.assertEqual(json.loads(p.stdout)['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
    def test_modified_log_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            fake=Path(td)/'log';fake.write_text('fake log')
            p=subprocess.run([sys.executable,'-B',m.__file__,str(fake)],
                             capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        self.assertEqual(json.loads(p.stdout)['result'],'HOLD')
    def test_hold_facts_inherited(self):
        base=m.base()
        self.assertEqual(base['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(base['source_to_binary_reproducibility_verified'])

if __name__=='__main__':
    unittest.main()
