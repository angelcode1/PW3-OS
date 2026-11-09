"""Offline synthetic tests of R3877.38; no real log, subprocess or device contact."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pw3_r3877_31_buildlog_audit as r31
import pw3_r3877_38_copy_operand_audit as m

OBJECTS=[f'priv/{n}.o' for n in 'abcde']


def make_lines():
    lines=['']*556
    for i,n in enumerate(OBJECTS):
        lines[i]=f'cc -c priv/s.c -o {n}'
    for i,n in enumerate(OBJECTS):
        lines[100+i]=f'cp -f {n} priv/out{i}.o'
    lines[110]='z'*270000
    return lines


class R38Tests(unittest.TestCase):
    def test_cp_parse_no_options(self):
        self.assertEqual(m.cp_operands(['cp','a.o','dest'])[0], 'supported_cp_positional_shape')
    def test_cp_flag(self):
        self.assertEqual(m.cp_operands(['cp','-fp','a.o','dest'])[1],['a.o','dest'])
    def test_cp_long_flags(self):
        self.assertEqual(m.cp_operands(['cp','--force','a.o','dst'])[1],['a.o','dst'])
    def test_double_dash(self):
        self.assertEqual(m.cp_operands(['cp','--','-file.o','-dest'])[1],['-file.o','-dest'])
    def test_target_dir_unresolved(self):
        for words in (['cp','-t','destination','a.o'],
                      ['cp','--target-directory=destination','a.o'],
                      ['cp','-S','suffix','a.o','dst'],
                      ['cp','--suffix=x','a.o','dst']):
            self.assertEqual(m.cp_operands(words)[0], 'option_unresolved')
    def test_unknown_options_fail_closed(self):
        self.assertEqual(m.cp_operands(['cp','-z','a.o','dst'])[0],'option_unresolved')
    def test_t_requires_two_operands(self):
        self.assertEqual(m.cp_operands(['cp','-T','a.o','b.o','dst'])[0],
                         'no_target_directory_arity_unresolved')
    def test_expansion_operand_not_evaluated(self):
        self.assertEqual(m.cp_operands(['cp','$(touch)','dst'])[0],
                         'expansion_or_invalid_operand_unresolved')
    def test_other_command_ignored(self):
        self.assertEqual(m.cp_operands(['echo','cp','a.o'])[0], 'not_copy')
    def test_ambiguous_arity(self):
        self.assertEqual(m.cp_operands(['cp','-f','only.o'])[0],'insufficient_operands')
    def test_all_five_source_positions(self):
        summary=m.classify_copy_mentions(make_lines(),OBJECTS,{1,2,3,4,5})
        self.assertEqual(summary['copy_command_lines_with_exact_orphan_mentions'],5)
        self.assertEqual(summary['exact_copy_object_token_mentions'],5)
        self.assertEqual(summary['printed_cp_operand_role_candidates'],{'source_operand_candidate':5})
        self.assertEqual(summary['distinct_printed_destination_texts_for_supported_copy_shapes'],5)
        self.assertEqual(summary['nonmain_lines_not_lexically_parsed'],1)
        self.assertFalse(summary['cp_command_interpreter_or_shell_executed'])
        for obj in OBJECTS:
            self.assertNotIn(obj,json.dumps(summary))
    def test_target_role_is_possible(self):
        lines=make_lines()
        lines[100]='cp source '+OBJECTS[0]
        summary=m.classify_copy_mentions(lines,OBJECTS,{1,2,3,4,5})
        self.assertEqual(summary['extra_objects_in_destination_operand_position'],1)
        self.assertEqual(summary['extra_objects_in_source_operand_position'],4)
    def test_unsupported_flags_unresolved_not_guessed(self):
        lines=make_lines();lines[100]='cp -t target '+OBJECTS[0]
        summary=m.classify_copy_mentions(lines,OBJECTS,{1,2,3,4,5})
        self.assertEqual(summary['printed_cp_operand_role_candidates'],
                         {'role_unresolved':1,'source_operand_candidate':4})
    def test_one_missing_mention_holds(self):
        lines=make_lines();lines[100]='cp priv/a.o-suffix priv/out0.o'
        with self.assertRaisesRegex(r31.AuditHold,'PRINTED_COPY_MENTION_LINE_COUNT_CHANGED'):
            m.classify_copy_mentions(lines,OBJECTS,{1,2,3,4,5})
    def test_noncopy_mismatch_holds(self):
        lines=make_lines();lines[100]='mv '+OBJECTS[0]+' priv/out0.o'
        with self.assertRaisesRegex(r31.AuditHold,'NONCOPY_ORPHAN_MENTION_CHANGED'):
            m.classify_copy_mentions(lines,OBJECTS,{1,2,3,4,5})
    def test_duplicate_mentions_holds(self):
        lines=make_lines();lines[100]='cp '+OBJECTS[0]+' '+OBJECTS[0]+' out'
        with self.assertRaisesRegex(r31.AuditHold,'PRINTED_COPY_MENTION_COUNT_CHANGED'):
            m.classify_copy_mentions(lines,OBJECTS,{1,2,3,4,5})
    def test_wrong_scanned_count_holds(self):
        with self.assertRaisesRegex(r31.AuditHold,'PRINTED_NONMAIN_SCANNED_LINES_CHANGED'):
            m.classify_copy_mentions(make_lines()+[''],OBJECTS,{1,2,3,4,5})
    def test_unparsed_count_holds(self):
        lines=make_lines();lines[110]='not long'
        with self.assertRaisesRegex(r31.AuditHold,'PRINTED_NONMAIN_UNPARSED_LINES_CHANGED'):
            m.classify_copy_mentions(lines,OBJECTS,{1,2,3,4,5})
    def test_reject_wrong_orphan_count(self):
        with self.assertRaisesRegex(r31.AuditHold,'FIVE_DISTINCT'):
            m.classify_copy_mentions(make_lines(),OBJECTS[:3],set())
    def test_prior_37_hold_propagates(self):
        with patch.object(m.r37,'analyze',side_effect=r31.AuditHold('HASH_CHANGED')):
            with self.assertRaisesRegex(r31.AuditHold,'HASH_CHANGED'):
                m.analyze(b'invalid')
    def test_prior_class_changed_holds(self):
        with patch.object(m.r37,'analyze',return_value={
                'printed_command_family_mention_counts': {'archive':5}}):
            with self.assertRaisesRegex(r31.AuditHold,'R3877_37_COPY_CONTEXT_CHANGED'):
                m.analyze(b'invalid')
    def test_integrated_sanitization_and_safety_flags(self):
        old={'printed_command_family_mention_counts':{'copy':5},
             'printed_argument_position_candidate_counts':{'earlier_argument_candidate':5},
             'extra_objects_with_any_exact_printed_mention':5}
        with patch.object(m.r37,'analyze',return_value=old),\
             patch.object(m.r36,'extract_records',return_value=(make_lines(), [{'line_number':i+1} for i in range(5)])),\
             patch.object(m.r35,'link_tokens_from_pinned',return_value=[]),\
             patch.object(m.r36,'reconcile_records',return_value=([{'output':x} for x in OBJECTS],{})):
            out=m.analyze(b'fake')
        self.assertEqual(out['extra_objects_in_source_operand_position'],5)
        self.assertFalse(out['source_to_binary_reproducibility_verified'])
        self.assertFalse(out['historical_builder_toolchain_versions_verified'])
        self.assertNotIn('priv/',json.dumps(out))
    def test_missing_log_holds(self):
        with tempfile.TemporaryDirectory() as d:
            p=subprocess.run([sys.executable,'-B',m.__file__,str(Path(d)/'absent')],
                             check=False,capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        obj=json.loads(p.stdout)
        self.assertEqual(obj['result'],'HOLD')
        self.assertEqual(obj['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
        self.assertEqual(obj['immutable_hold'],'NOT_BOOTABLE')
    def test_no_guest_execution_in_analyzer_source(self):
        src=Path(m.__file__).read_text()
        for s in ('import subprocess','subprocess.run(', 'os.system(', 'ssh root@',
                  'docker run','eval(', 'exec('):
            self.assertNotIn(s,src)
    def test_symlink_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            x=Path(d)/'x';x.write_text('not log')
            y=Path(d)/'y';y.symlink_to(x)
            p=subprocess.run([sys.executable,'-B',m.__file__,str(y)],capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        self.assertEqual(json.loads(p.stdout)['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')

if __name__=='__main__':unittest.main()
