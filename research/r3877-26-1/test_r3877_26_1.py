"""R3877.26.1: exact-context relocation with no fuzzy matching; host-only."""
import io
import json
import unittest
from test_r3877_26 import GOOD_PATCH, NEW_PATCH, maketar
import pw3_r3877_26_aports_input_audit as a

class ExactContextRelocationTests(unittest.TestCase):
    def test_positive_offset_six_lines(self):
        prefix=b''.join(f'prefix {i}\n'.encode() for i in range(6))
        files={'src/example.c':prefix+b'a\nold\nz\n'}
        details=[]
        a.apply_patch_chunks(a.parse_patch(GOOD_PATCH),files,details,'fixture.patch')
        self.assertEqual(files['src/example.c'],prefix+b'a\nnew\nmore\nz\n')
        self.assertEqual(details[0]['offset_lines'],6)
    def test_negative_offset_four_lines(self):
        original=b'a\nold\nz\n'
        patch=GOOD_PATCH.replace(b'@@ -1,3 +1,4 @@',b'@@ -5,3 +5,4 @@')
        details=[];files={'src/example.c':original}
        a.apply_patch_chunks(a.parse_patch(patch),files,details,'fixture.patch')
        self.assertEqual(details[0]['offset_lines'],-4)
    def test_ambiguous_earlier_match_not_ignored(self):
        # Even if the later matching hunk is after the preceding edit,
        # a duplicate earlier in the file must still trigger a HOLD.
        patch=b"""diff --git a/src/f b/src/f
--- a/src/f
+++ b/src/f
@@ -1,1 +1,1 @@
-first
+done
@@ -4,2 +4,2 @@
 a
-b
+c
"""
        with self.assertRaisesRegex(a.AuditHold,'PATCH_HUNK_AMBIGUOUS'):
            a.apply_patch_chunks(a.parse_patch(patch),{'src/f':b'first\na\nb\na\nb\n'})
    def test_following_hunk_cannot_rewrite_previous(self):
        patch=b"""diff --git a/src/f b/src/f
--- a/src/f
+++ b/src/f
@@ -1,1 +1,1 @@
-first
+second
@@ -2,1 +2,1 @@
-second
+third
"""
        with self.assertRaisesRegex(a.AuditHold,'PATCH_HUNK_OUT_OF_ORDER'):
            a.apply_patch_chunks(a.parse_patch(patch),{'src/f':b'first\n'})
    def test_no_fuzz_changed_context_holds(self):
        with self.assertRaisesRegex(a.AuditHold,'PATCH_CONTEXT_NOT_EXACT'):
            a.apply_patch_chunks(a.parse_patch(GOOD_PATCH), {'src/example.c':b'a\nold\nNOT z\n'})
    def test_ambiguous_context_fails_closed(self):
        twin=b'a\nold\nz\n'
        with self.assertRaisesRegex(a.AuditHold,'PATCH_HUNK_AMBIGUOUS'):
            a.apply_patch_chunks(a.parse_patch(GOOD_PATCH), {'src/example.c':twin+twin})
    def test_out_of_range_shift_fails_closed(self):
        prefix=b'pad\n'*(a.MAX_HUNK_LINE_OFFSET+1)
        with self.assertRaisesRegex(a.AuditHold,'PATCH_HUNK_OFFSET_LIMIT'):
            a.apply_patch_chunks(a.parse_patch(GOOD_PATCH), {'src/example.c':prefix+b'a\nold\nz\n'})
    def test_no_empty_context_on_existing_file(self):
        patch=b'diff --git a/src/x b/src/x\n--- a/src/x\n+++ b/src/x\n@@ -1,0 +1,1 @@\n+danger\n'
        with self.assertRaisesRegex(a.AuditHold,'PATCH_EMPTY_CONTEXT_NOT_ALLOWED'):
            a.apply_patch_chunks(a.parse_patch(patch),{'src/x':b'safe\n'})
    def test_legitimate_create_still_works(self):
        contents={}
        a.apply_patch_chunks(a.parse_patch(NEW_PATCH), contents)
        self.assertEqual(contents['src/new.c'],b'#include <x>\nint x;\n')
    def test_pipeline_reports_shift_counts(self):
        tar=maketar({'src/example.c':b'padding\na\nold\nz\n'})
        result=a.inspect_source(tar,[('fixture.patch',GOOD_PATCH)])
        self.assertEqual(result['hunk_alignment']['relocated_hunks'],1)
        self.assertEqual(result['hunk_alignment']['mode'],'UNIQUE_FULL_CONTEXT_NO_FUZZ')
        self.assertEqual(result['hunk_alignment']['max_absolute_line_offset'],1)
    def test_in_memory_outputs_deterministic(self):
        raw=maketar({'src/example.c':b'padding\na\nold\nz\n'})
        p=[('fixture.patch',GOOD_PATCH)]
        x=a.inspect_source(raw,p)
        y=a.inspect_source(raw,p)
        self.assertEqual(x,y)
    def test_new_milestone_preflight_hold(self):
        import contextlib,io,tempfile
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()) as o:
            rc=a.main(['--source-dir',d])
        self.assertEqual(rc,2)
        result=json.loads(o.getvalue())
        self.assertEqual(result['milestone'],'R3877.26.1')
        self.assertEqual(result['immutable_hold'],'NOT_BOOTABLE')
        self.assertEqual(result['kindle_ssh_sessions'],0)

if __name__=='__main__': unittest.main()
