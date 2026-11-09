"""Offline-only fixtures for R3877.27 canonical source tree fingerprint."""
import gzip
import io
import json
import pathlib
import subprocess
import sys
import tarfile
import unittest

import pw3_r3877_27_patched_tree_fingerprint as r27
from pw3_r3877_26_aports_input_audit import AuditHold


def make_tree(members):
    """members = [(name, kind, body)]; kind in file|dir|symlink"""
    b=io.BytesIO()
    with tarfile.open(fileobj=b, mode='w:gz') as tf:
        for name,kind,data in members:
            i=tarfile.TarInfo(name)
            if kind=='file':
                i.size=len(data)
                i.mode=0o644
                tf.addfile(i,io.BytesIO(data))
            elif kind=='dir':
                i.type=tarfile.DIRTYPE
                i.mode=0o755
                tf.addfile(i)
            elif kind=='symlink':
                i.type=tarfile.SYMTYPE
                i.linkname=data
                tf.addfile(i)
            else:
                raise ValueError(kind)
    return b.getvalue()


BASE=[('musl-1.2.6','dir',b''), ('musl-1.2.6/a','file',b'abc'),
      ('musl-1.2.6/dir','dir',b''),('musl-1.2.6/link','symlink','a')]


class CanonicalTreeTests(unittest.TestCase):
    def test_deterministic(self):
        a=make_tree(BASE)
        x=r27.source_tree_manifest(a,{})
        y=r27.source_tree_manifest(a,{})
        self.assertEqual(x,y)
        self.assertEqual(x['regular_files'],1)
        self.assertEqual(x['directories'],2)
        self.assertEqual(x['symlinks_not_followed'],1)

    def test_source_order_canonical(self):
        a=r27.source_tree_manifest(make_tree(BASE),{})
        b=r27.source_tree_manifest(make_tree(BASE[::-1]),{})
        self.assertEqual(a['canonical_patched_source_tree_sha256'],b['canonical_patched_source_tree_sha256'])

    def test_patched_content_changes_fingerprint(self):
        a=make_tree(BASE)
        original=r27.source_tree_manifest(a,{})
        patched=r27.source_tree_manifest(a,{'a':b'abd'})
        self.assertNotEqual(original['canonical_patched_source_tree_sha256'],patched['canonical_patched_source_tree_sha256'])

    def test_created_source_file(self):
        a=r27.source_tree_manifest(make_tree(BASE),{'dir/created':b'hello'})
        self.assertEqual(a['regular_files'],2)
        self.assertEqual(a['new_patch_created_file_count'],1)

    def test_duplicate_path_rejected(self):
        with self.assertRaisesRegex(AuditHold,'SOURCE_DUPLICATE_MEMBER'):
            r27.source_tree_manifest(make_tree(BASE+[BASE[1]]),{})

    def test_wrong_prefix_rejected(self):
        with self.assertRaisesRegex(AuditHold,'SOURCE_WRONG_ARCHIVE_PREFIX'):
            r27.source_tree_manifest(make_tree(BASE+[('evil','file',b'')]),{})

    def test_dotdot_rejected(self):
        with self.assertRaisesRegex(AuditHold,'SOURCE_UNSAFE_MEMBER_NAME'):
            r27.source_tree_manifest(make_tree(BASE+[('musl-1.2.6/../bad','file',b'')]),{})

    def test_archive_cap(self):
        with self.assertRaisesRegex(AuditHold,'SOURCE_ARCHIVE_TOO_LARGE'):
            r27.source_tree_manifest(make_tree(BASE),{},max_archive=100)

    def test_symlink_not_followed_or_overwritten(self):
        with self.assertRaisesRegex(AuditHold,'PATCH_REPLACED_SYMLINK'):
            r27.source_tree_manifest(make_tree(BASE),{'link':b'new'})

    def test_directory_not_overwritten(self):
        with self.assertRaisesRegex(AuditHold,'PATCH_REPLACED_NONFILE'):
            r27.source_tree_manifest(make_tree(BASE),{'dir':b'new'})

    def test_unsafe_created_filename(self):
        with self.assertRaisesRegex(AuditHold,'PATCH_UNSAFE_TARGET'):
            r27.source_tree_manifest(make_tree(BASE),{'../unsafe':b'hi'})

    def test_missing_input_refuses_without_ssh(self):
        p=subprocess.run([sys.executable,'-B',str(pathlib.Path(r27.__file__).resolve()),
                         '--source-dir','/definitely/missing/r3877-27'],capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        d=json.loads(p.stdout)
        self.assertEqual(d['result'],'HOLD')
        self.assertEqual(d['kindle_ssh_sessions'],0)
        self.assertEqual(d['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(d['patched_source_to_binary_reproducibility_verified'])

    def test_recreate_same_bytes(self):
        buf=make_tree(BASE)
        one=r27.source_tree_manifest(buf,{'a':b'z'})
        two=r27.source_tree_manifest(buf,{'a':b'z'})
        self.assertEqual(one['canonical_patched_source_tree_sha256'],two['canonical_patched_source_tree_sha256'])

    def test_bad_symlink_target_rejected(self):
        with self.assertRaisesRegex(AuditHold,'SOURCE_BAD_SYMLINK_TARGET'):
            r27.source_tree_manifest(make_tree(BASE+[('musl-1.2.6/huge','symlink','x'*1025)]),{})

    def test_excludes_incorrect_source_root(self):
        with self.assertRaisesRegex(AuditHold,'SOURCE_ROOT_NOT_DIRECTORY'):
            r27.source_tree_manifest(make_tree([('musl-1.2.6','file',b'data')]),{})

if __name__=='__main__':
    unittest.main()
