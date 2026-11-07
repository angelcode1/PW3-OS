"""Synthetic-only, host-only R3877.36 regression tests. No actual Alpine log needed."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pw3_r3877_31_buildlog_audit as r31
import pw3_r3877_35_object_link_consistency as r35
import pw3_r3877_36_unlinked_compile_triage as m


class PrintedObjectClassTests(unittest.TestCase):
    def test_compile_source_c(self):
        r=m.printed_compile_record(['cc','-O2','-fPIC','-c','private/foo.c','-o','secret/foo.o'],205)
        self.assertEqual(r['source_suffix_class'],'.c')
        self.assertEqual(r['object_suffix_class'],'.o')
        self.assertEqual(r['printed_flags'],('-O2','-fPIC'))
        self.assertEqual(r['line_number'],205)
    def test_assembly_types(self):
        for suffix in ('.S','.s'):
            r=m.printed_compile_record(['cc','-c','private/a'+suffix,'-o','private/a.o'],205)
            self.assertEqual(r['source_suffix_class'],suffix)
    def test_other_source_extension_stays_unknown(self):
        r=m.printed_compile_record(['cc','-c','private/unknown.x','-o','private/thing.lo'],205)
        self.assertEqual(r['source_suffix_class'],'other_or_unresolved')
        self.assertEqual(r['object_suffix_class'],'.lo')
    def test_multiple_compile_source_switches_unknown(self):
        r=m.printed_compile_record(['cc','-c','a.c','-c','b.c','-o','private/b.o'],205)
        self.assertEqual(r['source_suffix_class'],'other_or_unresolved')
    def test_unresolved_o_is_hold(self):
        with self.assertRaisesRegex(r31.AuditHold,'UNRECOGNIZED_COMPILE_OUTPUT'):
            m.printed_compile_record(['cc','-c','a.c'],205)
    def test_reconcile_one_orphan_privately(self):
        inputs=[
          {'output':'private/a.o','source_suffix_class':'.c','object_suffix_class':'.o','printed_flags':('-O2',),'line_number':205},
          {'output':'private/b.o','source_suffix_class':'.S','object_suffix_class':'.o','printed_flags':('-O2','-fPIC'),'line_number':1668},
          {'output':'private/c.lo','source_suffix_class':'other_or_unresolved','object_suffix_class':'.lo','printed_flags':(),'line_number':235},
        ]
        orphan,data=m.reconcile_records(inputs,['cc','private/a.o'], expected_compile=3,expected_link=1,expected_unlinked=2)
        self.assertEqual([x['output'] for x in orphan],['private/b.o','private/c.lo'])
        self.assertEqual(data['unlinked_output_source_suffix_classes'],{'.S':1,'other_or_unresolved':1})
        self.assertEqual(data['unlinked_output_object_suffix_classes'],{'.lo':1,'.o':1})
        self.assertEqual(data['unlinked_compile_lines_before_main_link'],1)
        self.assertEqual(data['unlinked_compile_lines_after_main_link'],1)
        self.assertNotIn('private/',json.dumps(data))
    def test_unmatched_link_refuses(self):
        inputs=[{'output':'a.o','source_suffix_class':'.c','object_suffix_class':'.o','printed_flags':(), 'line_number':1}]
        with self.assertRaisesRegex(r31.AuditHold,'PRINTED_LINK_OBJECT_WITHOUT_COMPILE_OUTPUT'):
            m.reconcile_records(inputs,['cc','other.o'],expected_compile=1,expected_link=1,expected_unlinked=0)
    def test_count_mismatch_refuses(self):
        with self.assertRaises(r31.AuditHold):
            m.reconcile_records([],[],expected_compile=1,expected_link=0,expected_unlinked=1)
    def test_classification_uses_exact_tokens_not_substrings(self):
        orphans=['private/x.o','private/y.o','private/z.o','private/v.o','private/w.o']
        lines=['cc -O2 -c private/z.c -o private/z.o',
               'ar -r archive.a private/x.o',
               'something private/x.o-extra',
               'install private/y.o elsewhere',
               'notes have private/w.o: malformed token',
               'cc -shared private/v.o -o target.so',
               'not actually command private/w.o']
        data=m.classify_other_references(lines,orphans,{1})
        self.assertEqual(data['unlinked_outputs_with_full_token_mentions_outside_compile_or_main_link'],4)
        self.assertEqual(data['unlinked_outputs_without_such_observed_mentions'],1)
        self.assertEqual(data['extra_printed_token_mentions_by_generic_context']['archive_tool_like'],1)
        self.assertEqual(data['extra_printed_token_mentions_by_generic_context']['compiler_linker_like'],1)
        self.assertEqual(data['extra_printed_token_mentions_by_generic_context']['copy_install_or_binary_tool_like'],1)
        self.assertEqual(data['extra_printed_token_mentions_by_generic_context']['other_printed_context'],1)
        self.assertNotIn('private/', json.dumps(data))
    def test_skips_exact_main_link_physical_lines(self):
        orphan=['x.o','y.o','z.o','v.o','w.o']
        lines=['']*1667
        lines[1665]='cc -shared x.o -o libc.so'
        lines[1666]='x.o y.o z.o v.o w.o'
        data=m.classify_other_references(lines,orphan,set())
        self.assertEqual(data['unlinked_outputs_with_full_token_mentions_outside_compile_or_main_link'],0)
    def test_unparsed_long_line_not_claimed_no_use_proof(self):
        orphan=['x.o','y.o','z.o','v.o','w.o']
        lines=['xx'*150000+' x.o']
        data=m.classify_other_references(lines,orphan,set())
        self.assertEqual(data['other_printed_lines_not_lexically_parsed'],1)
        self.assertTrue(data['absence_of_printed_token_mentions_is_not_proof_of_unused_artifacts'])
    def test_other_line_counts_refuse_unbounded(self):
        with self.assertRaisesRegex(r31.AuditHold,'OTHER_LINE_COUNT_BUDGET'):
            m.classify_other_references(['x']*3001, ['a.o','b.o','c.o','d.o','e.o'], set())
    def test_unrecognized_count_refuses(self):
        with self.assertRaisesRegex(r31.AuditHold,'EXPECTED_FIVE_UNLINKED_OUTPUTS'):
            m.classify_other_references([],['a.o'],set())
    def test_r35_failure_precedes_analysis(self):
        with patch.object(r35,'analyze',side_effect=r31.AuditHold('PINNED_HASH_INVALID')):
            with self.assertRaisesRegex(r31.AuditHold,'PINNED_HASH_INVALID'):
                m.analyze(b'unknown')
    def test_full_synthetic_integration_preserves_privacy(self):
        prior={'printed_compile_output_occurrences_not_in_link_candidate':5,
               'printed_link_object_occurrences_without_compile_output_match':0}
        rec=[{'output':f'private/{i}.o','source_suffix_class':'.c','object_suffix_class':'.o','printed_flags':('-O2',),'line_number':i+1} for i in range(1428)]
        link=['cc']+[f'private/{i}.o' for i in range(1423)]
        lines=['no data']*1981
        with patch.object(r35,'analyze',return_value=prior), \
             patch.object(m,'extract_records',return_value=(lines,rec)), \
             patch.object(r35,'link_tokens_from_pinned',return_value=link):
            data=m.analyze(b'not-real-public-log')
        self.assertEqual(data['printed_compile_outputs_not_in_main_link'],5)
        self.assertEqual(data['unmatched_printed_main_link_objects'],0)
        self.assertEqual(data['unlinked_output_source_suffix_classes'],{'.c':5})
        self.assertFalse(data['source_to_binary_reproducibility_verified'])
        self.assertFalse(data['historical_builder_toolchain_versions_verified'])
        self.assertNotIn('private/',json.dumps(data))
    def test_report_does_not_emit_tokens(self):
        s=Path(m.__file__).read_text()
        for forbidden in ('import subprocess','import os\n','eval(', 'exec(', 'os.system(', 'Popen(', 'subprocess.run(', 'docker run', 'ssh root@'):
            self.assertNotIn(forbidden,s)
    def test_missing_log_returns_immutable_hold(self):
        with tempfile.TemporaryDirectory() as td:
            proc=subprocess.run([sys.executable,'-B',m.__file__,str(Path(td)/'missing')],
                                capture_output=True,text=True,check=False)
        self.assertEqual(proc.returncode,2)
        data=json.loads(proc.stdout)
        self.assertEqual(data['result'],'HOLD')
        self.assertEqual(data['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
        self.assertEqual(data['immutable_hold'],'NOT_BOOTABLE')
        self.assertEqual(data['kindle_ssh_sessions'],0)
    def test_symlink_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            real=Path(td)/'log'; real.write_text('fake')
            link=Path(td)/'link'; link.symlink_to(real)
            result=subprocess.run([sys.executable,'-B',m.__file__,str(link)],
                                  capture_output=True,text=True,check=False)
        self.assertEqual(json.loads(result.stdout)['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
    def test_tampered_log_holds(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'log';p.write_text('fake')
            result=subprocess.run([sys.executable,'-B',m.__file__,str(p)],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['result'],'HOLD')
    def test_base_never_bootable(self):
        b=m.base()
        self.assertEqual(b['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(b['binary_execution_performed'])
        self.assertFalse(b['historical_builder_machine_identity_verified'])
        self.assertFalse(b['source_to_binary_reproducibility_verified'])

if __name__=='__main__':
    unittest.main()
