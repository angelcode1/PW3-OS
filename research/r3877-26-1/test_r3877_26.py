"""Pure host-only R3877.26 regression tests; no external network or Kindle."""
import io
import json
import pathlib
import tarfile
import tempfile
import unittest

import pw3_r3877_26_aports_input_audit as a

HERE=pathlib.Path(__file__).resolve().parent

def maketar(files,duplicate=False,extra=None):
    out=io.BytesIO()
    with tarfile.open(fileobj=out,mode='w:gz') as tf:
        root=tarfile.TarInfo('musl-1.2.6')
        root.type=tarfile.DIRTYPE
        tf.addfile(root)
        for name,b in files.items():
            for _ in range(2 if duplicate else 1):
                ti=tarfile.TarInfo('musl-1.2.6/'+name)
                ti.size=len(b);ti.mode=0o644
                tf.addfile(ti,io.BytesIO(b))
        if extra:
            ti=tarfile.TarInfo(extra)
            ti.size=1
            tf.addfile(ti,io.BytesIO(b'x'))
    return out.getvalue()

GOOD_PATCH=b'''From nobody\ndiff --git a/src/example.c b/src/example.c\nindex aa..bb 100644\n--- a/src/example.c\n+++ b/src/example.c\n@@ -1,3 +1,4 @@\n a\n-old\n+new\n+more\n z\n'''
NEW_PATCH=b'''diff --git a/src/new.c b/src/new.c\nnew file mode 100644\n--- /dev/null\n+++ b/src/new.c\n@@ -0,0 +1,2 @@\n+#include <x>\n+int x;\n'''
MULTI=b'''diff --git a/src/example.c b/src/example.c\n--- a/src/example.c\n+++ b/src/example.c\n@@ -1,2 +1,3 @@\n a\n+insert\n old\n@@ -3,1 +4,1 @@\n-z\n+done\n'''

class SourcePatchUnitTests(unittest.TestCase):
    def test_pinned_manifest(self):
        m=a.load_manifest(HERE/a.MANIFEST_NAME)
        self.assertEqual(len(m['entries']),12)
        self.assertEqual(sum(e['role']=='patch' for e in m['entries']),6)
    def test_pin_cannot_be_substituted(self):
        with tempfile.TemporaryDirectory() as d:
            m=json.loads((HERE/a.MANIFEST_NAME).read_text())
            m['aports_commit']='0'*40
            p=pathlib.Path(d)/'bad.json';p.write_text(json.dumps(m))
            with self.assertRaisesRegex(a.AuditHold,'MANIFEST_SNAPSHOT_MISMATCH'):
                a.load_manifest(p)
    def test_invalid_manifest_digest(self):
        with tempfile.TemporaryDirectory() as d:
            m=json.loads((HERE/a.MANIFEST_NAME).read_text())
            m['entries'][0]['sha512']='foo'
            p=pathlib.Path(d)/'bad.json';p.write_text(json.dumps(m))
            with self.assertRaisesRegex(a.AuditHold,'MANIFEST_BAD_SHA512'):
                a.load_manifest(p)
    def test_simple_patch(self):
        changes=a.apply_patch_chunks(a.parse_patch(GOOD_PATCH),{'src/example.c':b'a\nold\nz\n'})
        self.assertEqual(changes,['src/example.c'])
    def test_patch_changes_correct(self):
        b={'src/example.c':b'a\nold\nz\n'}
        a.apply_patch_chunks(a.parse_patch(GOOD_PATCH),b)
        self.assertEqual(b['src/example.c'],b'a\nnew\nmore\nz\n')
    def test_new_file(self):
        b={}
        a.apply_patch_chunks(a.parse_patch(NEW_PATCH),b)
        self.assertEqual(b['src/new.c'],b'#include <x>\nint x;\n')
    def test_new_file_refuses_existing(self):
        with self.assertRaisesRegex(a.AuditHold,'PATCH_CREATE_TARGET_EXISTS'):
            a.apply_patch_chunks(a.parse_patch(NEW_PATCH),{'src/new.c':b'data'})
    def test_context_drift_holds(self):
        with self.assertRaisesRegex(a.AuditHold,'PATCH_CONTEXT_NOT_EXACT'):
            a.apply_patch_chunks(a.parse_patch(GOOD_PATCH),{'src/example.c':b'a\nother\nz\n'})
    def test_multi_hunk_offsets(self):
        b={'src/example.c':b'a\nold\nz\n'}
        a.apply_patch_chunks(a.parse_patch(MULTI),b)
        self.assertEqual(b['src/example.c'],b'a\ninsert\nold\ndone\n')
    def test_consecutive_patch_blocks(self):
        bb=GOOD_PATCH+GOOD_PATCH.replace(b'old',b'new').replace(b'new\n+more',b'final\n+more',1)
        # Blocks parse independently; a repeated context in the same input is deterministic.
        self.assertEqual(len(a.parse_patch(bb)),2)
    def test_reject_path_traversal(self):
        evil=GOOD_PATCH.replace(b'src/example.c',b'../etc/shadow')
        with self.assertRaisesRegex(a.AuditHold,'PATCH_UNSAFE_TARGET_PATH'):
            a.parse_patch(evil)
    def test_reject_patch_rename(self):
        evil=GOOD_PATCH.replace(b'diff --git a/src/example.c b/src/example.c',b'diff --git a/src/example.c b/src/different.c')
        with self.assertRaisesRegex(a.AuditHold,'PATCH_RENAME_NOT_SUPPORTED'):
            a.parse_patch(evil)
    def test_reject_hunk_truncation(self):
        with self.assertRaisesRegex(a.AuditHold,'PATCH_HUNK_TRUNCATED'):
            a.parse_patch(GOOD_PATCH.replace(b'@@ -1,3 +1,4 @@',b'@@ -1,30 +1,40 @@'))
    def test_bad_hunk_counts(self):
        with self.assertRaisesRegex(a.AuditHold,'PATCH_HUNK_COUNTS_OVERFLOW'):
            a.parse_patch(GOOD_PATCH.replace(b'@@ -1,3 +1,4 @@',b'@@ -1,2 +1,4 @@'))
    def test_missing_unified_header(self):
        with self.assertRaises(a.AuditHold):
            a.parse_patch(GOOD_PATCH.replace(b'+++ b/src/example.c',b'+++x b/src/example.c'))
    def test_archive_target_read(self):
        buf=maketar({'src/example.c':b'a\nold\nz\n'})
        found,n=a.tar_source_files(buf,{'src/example.c'})
        self.assertEqual(found['src/example.c'],b'a\nold\nz\n')
        self.assertGreater(n,1)
    def test_archive_disallows_duplicates(self):
        with self.assertRaisesRegex(a.AuditHold,'SOURCE_TARBALL_DUPLICATE_PATH'):
            a.tar_source_files(maketar({'src/example.c':b'x'},duplicate=True),{'src/example.c'})
    def test_archive_disallows_escape(self):
        with self.assertRaisesRegex(a.AuditHold,'SOURCE_TARBALL_UNSAFE_PATH'):
            a.tar_source_files(maketar({},extra='musl-1.2.6/../../escape'),set())
    def test_archive_target_must_exist(self):
        with self.assertRaisesRegex(a.AuditHold,'SOURCE_PATCH_TARGET_MISSING'):
            a.tar_source_files(maketar({}),{'src/no.c'})
    def test_archive_requires_prefix(self):
        with self.assertRaisesRegex(a.AuditHold,'SOURCE_TARBALL_BAD_PREFIX'):
            a.tar_source_files(maketar({},extra='unrelated.c'),set())
    def test_archive_corrupt(self):
        with self.assertRaises(a.AuditHold):
            a.tar_source_files(b'not an archive',set())
    def test_in_memory_full_pipeline(self):
        tar=maketar({'src/example.c':b'a\nold\nz\n'})
        r=a.inspect_source(tar,[('first.patch',GOOD_PATCH),('new.patch',NEW_PATCH)])
        self.assertEqual(len(r['changed_files']),2)
        self.assertEqual(r['patches'][0]['patch'],'first.patch')
    def test_missing_input_is_hold(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(a.main(['--source-dir',d]),2)
    def test_no_target_execution_on_no_args(self):
        # argparse requires an explicit local source directory.
        with self.assertRaises(SystemExit) as cm:
            a.main([])
        self.assertEqual(cm.exception.code,2)

if __name__=='__main__':
    unittest.main()
