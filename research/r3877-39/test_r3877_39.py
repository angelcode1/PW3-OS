"""R3877.39 synthetic-only regression tests; no log/network/Kindle required."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pw3_r3877_31_buildlog_audit as r31
import pw3_r3877_39_copy_dest_consumer_audit as m

OBJECTS=[f'private_src/obj{i}.o' for i in range(5)]
DESTS=[f'private_dst/stage{i}.o' for i in range(5)]


def fixture():
    lines=['']*556
    for i,x in enumerate(OBJECTS):
        lines[i]=f'cc -c private_src/s{i}.c -o {x}'
        lines[100+i]=f'cp -f {x} {DESTS[i]}'
    lines[110]='q'*270000  # intentionally unparsed, never truncated to infer absence
    return lines


def get_records(lines=None):
    return m.collect_destinations(lines or fixture(), OBJECTS, {1,2,3,4,5})


class R39Tests(unittest.TestCase):
    def test_collect_exact_objects_and_destinations(self):
        records, n=get_records()
        self.assertEqual(len(records),5)
        self.assertEqual(n,1)
        self.assertEqual([x['source'] for x in records],OBJECTS)
        self.assertEqual([x['dest'] for x in records],DESTS)
        self.assertEqual([x['line'] for x in records],list(range(101,106)))
        self.assertTrue(all(x['single_source'] for x in records))
    def test_duplicated_destination_holds(self):
        lines=fixture()
        lines[104]='cp '+OBJECTS[4]+' '+DESTS[0]
        with self.assertRaisesRegex(r31.AuditHold,'COPY_DESTINATION_UNIQUENESS_CHANGED'):
            get_records(lines)
    def test_missing_object_mention_holds(self):
        lines=fixture()
        lines[103]='cp missing.o '+DESTS[3]
        with self.assertRaisesRegex(r31.AuditHold,'FIVE_COPY_RECORDS_NOT_PRESENT'):
            get_records(lines)
    def test_explicit_untrusted_substitution_rejected(self):
        lines=fixture()
        lines[100]='cp '+OBJECTS[0]+' $(touch)'
        with self.assertRaisesRegex(r31.AuditHold,'ORPHAN_CP_SHAPE_CHANGED'):
            get_records(lines)
    def test_unparsed_huge_line_preserved(self):
        lines=fixture()
        records,n=get_records(lines)
        self.assertEqual((len(records),n),(5,1))
    def test_unparsed_line_count_changed_holds(self):
        lines=fixture();lines[110]='short'
        with self.assertRaisesRegex(r31.AuditHold,'NONMAIN_UNPARSED_COUNT_CHANGED'):
            get_records(lines)
    def test_wrong_log_length_holds(self):
        with self.assertRaisesRegex(r31.AuditHold,'NONMAIN_LINE_COUNT_CHANGED'):
            get_records(fixture()+[''])
    def test_wrong_object_count_holds(self):
        with self.assertRaisesRegex(r31.AuditHold,'EXPECTED_FIVE_DISTINCT'):
            m.collect_destinations(fixture(),OBJECTS[:4],set())
    def test_same_source_destination_holds(self):
        lines=fixture();lines[100]='cp '+OBJECTS[0]+' '+OBJECTS[0]
        with self.assertRaises(r31.AuditHold):
            get_records(lines)
    def test_noncopy_rejected(self):
        lines=fixture();lines[100]='mv '+OBJECTS[0]+' '+DESTS[0]
        with self.assertRaisesRegex(r31.AuditHold,'ORPHAN_MENTION_NONCOPY_CHANGED'):
            get_records(lines)
    def test_options_unresolved_hold(self):
        lines=fixture();lines[100]='cp -t target '+OBJECTS[0]
        with self.assertRaisesRegex(r31.AuditHold,'ORPHAN_CP_SHAPE_CHANGED'):
            get_records(lines)
    def test_multiple_sources_classified(self):
        lines=fixture();lines[100]='cp -f '+OBJECTS[0]+' private_src/other.o '+DESTS[0]
        records,_=get_records(lines)
        self.assertFalse(records[0]['single_source'])
    def test_sources_are_later_consumers(self):
        lines=fixture()
        lines[120]='strip '+DESTS[0]
        lines[130]='cp '+DESTS[1]+' output'
        records,_=get_records(lines)
        out=m.classify_destination_consumers(lines,records,
                [{'output':x} for x in OBJECTS], [])
        self.assertEqual(out['distinct_copy_destinations_with_later_full_token_mentions'],2)
        self.assertEqual(out['later_full_token_destination_mention_count'],2)
        self.assertEqual(out['later_printed_command_family_mention_counts'],
                         {'binary_tool':1,'copy':1})
    def test_before_copy_mention_not_consumer(self):
        lines=fixture()
        lines[75]='strip '+DESTS[0]
        records,_=get_records(lines)
        out=m.classify_destination_consumers(lines,records,[],[])
        self.assertEqual(out['distinct_copy_destinations_with_later_full_token_mentions'],0)
    def test_substring_not_match(self):
        lines=fixture();lines[120]='strip '+DESTS[0]+'suffix'
        records,_=get_records(lines)
        out=m.classify_destination_consumers(lines,records,[],[])
        self.assertEqual(out['later_full_token_destination_mention_count'],0)
    def test_compile_match_not_assumed_link(self):
        lines=fixture();records,_=get_records(lines)
        out=m.classify_destination_consumers(lines,records,
                [{'output':DESTS[0]}],[DESTS[1]])
        self.assertEqual(out['copy_destinations_matching_printed_compile_output_text'],1)
        # Link objects only recognized by full-name object classification.
        self.assertEqual(out['copy_destinations_matching_main_link_object_input_text'],1)
    def test_unparsed_log_line_caveat(self):
        lines=fixture();records,_=get_records(lines)
        out=m.classify_destination_consumers(lines,records,[],[])
        self.assertEqual(out['other_unparsed_log_lines_for_destination_mentions'],1)
        self.assertTrue(out['unparsed_lines_could_contain_additional_references'])
        self.assertTrue(out['absence_of_printed_mentions_does_not_prove_no_actual_consumers'])
    def test_no_path_leakage(self):
        lines=fixture();records,_=get_records(lines)
        out=m.classify_destination_consumers(lines,records,[],[])
        raw=json.dumps(out)
        self.assertNotIn('private_src',raw)
        self.assertNotIn('private_dst',raw)
        self.assertNotIn('stage0',raw)
    def test_suffix_classes_allowlisted(self):
        self.assertEqual(m.destination_class('private/a.o'),'object_o')
        self.assertEqual(m.destination_class('private/a.lo'),'object_lo')
        self.assertEqual(m.destination_class('private/lib.a'),'archive_a')
        self.assertEqual(m.destination_class('private/lib.so.1'),'shared_library_like')
        self.assertEqual(m.destination_class('private/dir/'),'directory_syntax')
        self.assertEqual(m.destination_class('private/out'),'other_or_unresolved')
    def test_malicious_line_never_evaluated(self):
        s='$(touch /tmp/something)'
        lines=fixture();lines[120]='echo '+s+' '+DESTS[0]
        records,_=get_records(lines)
        # If lexical parse accepts the string, it is still just data.
        out=m.classify_destination_consumers(lines,records,[],[])
        self.assertNotIn(s,json.dumps(out))
    def test_prior_hold_propagated(self):
        with patch.object(m.r38,'analyze',side_effect=r31.AuditHold('PIN_MISMATCH')):
            with self.assertRaisesRegex(r31.AuditHold,'PIN_MISMATCH'):
                m.analyze(b'unsafe')
    def test_prior_count_changed_hold(self):
        with patch.object(m.r38,'analyze',return_value={'extra_objects_in_source_operand_position':4}):
            with self.assertRaisesRegex(r31.AuditHold,'PRIOR_R3877_38_'):
                m.analyze(b'unsafe')
    def test_integration_all_output_redacted(self):
        prior={'extra_objects_in_source_operand_position':5,
            'extra_objects_in_destination_operand_position':0,
            'distinct_printed_destination_texts_for_supported_copy_shapes':5,
            'printed_cp_syntax_classes':{'supported_cp_positional_shape':5},
            'nonmain_lines_not_lexically_parsed':1}
        with patch.object(m.r38,'analyze',return_value=prior),\
             patch.object(m.r36,'extract_records',return_value=(fixture(),
                   [{'output':x, 'line_number':i+1} for i,x in enumerate(OBJECTS)])),\
             patch.object(m.r35,'link_tokens_from_pinned',return_value=[]),\
             patch.object(m.r36,'reconcile_records',return_value=([{'output':x} for x in OBJECTS],{})):
            result=m.analyze(b'fake')
        self.assertEqual(result['distinct_extra_copy_destinations'],5)
        self.assertFalse(result['printed_copy_commands_executed_verified'])
        self.assertFalse(result['source_to_binary_reproducibility_verified'])
        self.assertFalse(result['binary_execution_performed'])
        self.assertNotIn('private_',json.dumps(result))
    def test_missing_log_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=subprocess.run([sys.executable,'-B',str(Path(m.__file__)),
                    str(Path(td)/'absent')],capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        d=json.loads(p.stdout)
        self.assertEqual(d['result'],'HOLD')
        self.assertEqual(d['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
        self.assertEqual(d['immutable_hold'],'NOT_BOOTABLE')
        self.assertEqual(d['kindle_ssh_sessions'],0)
    def test_symlink_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/'a';src.write_text('bad')
            link=Path(td)/'b';link.symlink_to(src)
            p=subprocess.run([sys.executable,'-B',str(Path(m.__file__)),str(link)],
                             capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        self.assertEqual(json.loads(p.stdout)['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
    def test_no_host_execution_imports(self):
        code=Path(m.__file__).read_text()
        for s in ('import subprocess','os.system(', 'eval(', 'exec(', 'ssh root@','docker run'):
            self.assertNotIn(s,code)

if __name__=='__main__':unittest.main()
