"""Synthetic offline tests. No historical build log, command execution or Kindle."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import pw3_r3877_31_buildlog_audit as r31
import pw3_r3877_34_pinned_link_structure as r34
import pw3_r3877_35_object_link_consistency as m


class ReconcileTests(unittest.TestCase):
    def test_exact_path_matches_and_nonmatches(self):
        o=m.summarize_printed_names(['/private/o1.o','/private/o2.o','/private/o3.o'],
          ['cc','-shared','/private/o1.o','/private/o2.o','/else/special.o'])
        self.assertEqual(o['exact_text_object_occurrences_matched'],2)
        self.assertEqual(o['printed_link_object_occurrences_without_compile_output_match'],1)
        self.assertEqual(o['printed_compile_output_occurrences_not_in_link_candidate'],1)
        self.assertNotIn('/private/',json.dumps(o))
        self.assertNotIn('special',json.dumps(o))
    def test_no_basename_equivalence(self):
        d=m.summarize_printed_names(['a/same.o'],['cc','b/same.o'])
        self.assertEqual(d['exact_text_object_occurrences_matched'],0)
    def test_no_options_counted_as_objects(self):
        d=m.summarize_printed_names(['a/b.o'],['cc','-Wl,a/b.o','-a/b.o'])
        self.assertEqual(d['link_object_like_input_tokens'],0)
    def test_duplicate_inputs_and_outputs_preserve_multiplicity(self):
        d=m.summarize_printed_names(['a.o','a.o','b.o'],['cc','a.o','a.o','a.o','b.o'])
        self.assertEqual(d['exact_text_object_occurrences_matched'],3)
        self.assertEqual(d['link_duplicate_object_text_occurrences'],2)
        self.assertEqual(d['printed_link_object_occurrences_without_compile_output_match'],1)
        self.assertEqual(d['compile_output_duplicate_text_occurrences'],1)
    def test_one_output_required(self):
        self.assertEqual(m.output_from_compile(['cc','-O2','-c','src.c','-o','obj/a.o']),'obj/a.o')
        self.assertIsNone(m.output_from_compile(['cc','-c','a.c']))
        self.assertIsNone(m.output_from_compile(['cc','-c','a.c','-o','b.o','-o','c.o']))
        self.assertIsNone(m.output_from_compile(['cc','-c','a.c','-o','-fPIC']))
        self.assertIsNone(m.output_from_compile(['cc','-c','a.c','-o','lib.so']))
    def test_compile_switch_enforced(self):
        with self.assertRaisesRegex(r31.AuditHold,'COMPILE_SWITCH_MISSING'):
            m.output_from_compile(['cc','-o','obj.o'])
    def test_printed_compile_collect_synthetic(self):
        s=b'cc -O2 -fPIC -c src/secret.c -o /private/obj.o\n'
        with patch.object(m,'EXPECTED_PRINTED_COMPILE',1):
            names,metadata=m.collect_compiles(s)
        self.assertEqual(names,['/private/obj.o'])
        self.assertEqual(metadata['compile_lines_reconciled'],1)
        self.assertTrue(metadata['all_compile_drivers_printed_cc'])
    def test_non_cc_printed_compile_refused(self):
        s=b'gcc -O2 -fPIC -c src/a.c -o x.o\n'
        with patch.object(m,'EXPECTED_PRINTED_COMPILE',1):
            with self.assertRaisesRegex(r31.AuditHold,'DRIVERS_CHANGED'):
                m.collect_compiles(s)
    def test_malformed_printed_compile_refused(self):
        s=b'cc -O2 -c src/a.c -o "broken\n'
        with patch.object(m,'EXPECTED_PRINTED_COMPILE',1):
            with self.assertRaisesRegex(r31.AuditHold,'NOT_FULLY_TOKENIZED'):
                m.collect_compiles(s)
    def test_fake_prefix_disallowed(self):
        raw=b'fake'
        with self.assertRaises(r31.AuditHold):
            m.analyze(raw)
    def test_missing_path_holds(self):
        with tempfile.TemporaryDirectory() as td:
            cmd=[sys.executable,'-B',m.__file__,str(Path(td)/'missing')]
            p=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        d=json.loads(p.stdout)
        self.assertEqual(d['result'],'HOLD')
        self.assertEqual(d['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
        self.assertEqual(d['immutable_hold'],'NOT_BOOTABLE')
    def test_symlink_path_holds(self):
        with tempfile.TemporaryDirectory() as td:
            t=Path(td)/'raw';t.write_text('fake')
            p=Path(td)/'link';p.symlink_to(t)
            result=subprocess.run([sys.executable,'-B',m.__file__,str(p)],capture_output=True,text=True)
        self.assertEqual(result.returncode,2)
        self.assertEqual(json.loads(result.stdout)['hold_category'],'LOG_FILE_MISSING_OR_SYMLINK')
    def test_no_shell_or_subprocess_in_audit(self):
        s=Path(m.__file__).read_text()
        for bad in ('import subprocess','import os\n','eval(', 'exec(', 'os.system(', 'Popen(', 'subprocess.run','docker ','ssh '):
            self.assertNotIn(bad,s)
    def test_immutable_provenance_holds(self):
        b=m.base()
        self.assertFalse(b['source_to_binary_reproducibility_verified'])
        self.assertFalse(b['historical_builder_complete_link_invocation_verified'])
        self.assertFalse(b['target_musl_runtime_verified'])
        self.assertEqual(b['kindle_ssh_sessions'],0)
    def test_r34_pin_constants(self):
        self.assertEqual(m.EXPECTED_LINK_OBJECT_LIKE,1423)
        self.assertEqual(m.EXPECTED_PRINTED_COMPILE,1428)
        self.assertEqual(m.EXPECTED_LINK_TOKENS,1494)
        self.assertEqual(r34.PINNED_JOINED_CHARS,40671)
    def test_missing_compile_output_not_fatal_and_no_paths_in_report(self):
        with patch.object(m,'EXPECTED_PRINTED_COMPILE',1):
            names, meta=m.collect_compiles(b'cc -O2 -c x.c\n')
        self.assertEqual(names,[])
        self.assertEqual(meta['compile_lines_without_single_literally_recognized_object_output'],1)
        r=m.summarize_printed_names(names,['cc','a.o'])
        self.assertEqual(r['printed_link_object_occurrences_without_compile_output_match'],1)
    def test_r34_pin_failure_precedes_comparison(self):
        with patch.object(r34,'analyze',side_effect=r31.AuditHold('MISMATCH')):
            with self.assertRaisesRegex(r31.AuditHold,'MISMATCH'):
                m.analyze(b'bad')
    def test_no_blank_source_path_leak(self):
        d=m.summarize_printed_names(['/home/user/VIP.o'],['/home/user/VIP.o'])
        s=json.dumps(d)
        self.assertNotIn('VIP',s)
        self.assertNotIn('/home',s)

if __name__=='__main__': unittest.main()

# Additional independent contract test for the integration summary.
class IntegrationContract(unittest.TestCase):
    def test_valid_pinned_candidate_remains_unverified_historical_build(self):
        baseline={'lexically_recognized_candidate_token_count':1494,
                  'token_classes':{'object_like':1423},
                  'explicit_output_switch_count':1}
        comp=(['obj/a.o','obj/b.o'],{
            'compile_lines_reconciled':1428,
            'compile_argv_parse_failures':0,
            'compile_lines_without_single_literally_recognized_object_output':1426,
            'all_compile_drivers_printed_cc':True})
        with patch.object(r34,'analyze',return_value=baseline), \
             patch.object(m,'collect_compiles',return_value=comp), \
             patch.object(m,'link_tokens_from_pinned',return_value=['cc','obj/a.o','obj/b.o','unseen.o']):
            result=m.analyze(b'public-log-synthetic-data')
        self.assertEqual(result['exact_text_object_occurrences_matched'],2)
        self.assertEqual(result['printed_link_object_occurrences_without_compile_output_match'],1)
        self.assertFalse(result['historical_builder_complete_link_invocation_verified'])
        self.assertFalse(result['source_to_binary_reproducibility_verified'])
        self.assertFalse(result['raw_command_lines_disclosed'])
