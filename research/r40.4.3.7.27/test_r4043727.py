"""Synthetic-only R4043727 host tests, never execute the real stage."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

script = Path(__file__).with_name('R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py')
spec = importlib.util.spec_from_file_location('r3727', script)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FakeParent:
    class Hold(Exception):
        pass

    def scan(self, root, n):
        return {'result': 'STATIC_INTERP_GUEST_PATH_CLASSIFICATION_ONLY',
                'counts': m.EXPECTED.copy(), 'source_parse_holds': {},
                'path_resolution_counts': m.EXPECTED_PATHS.copy()}

    def open_regular_nofollow(self, path):
        return open(path, 'rb')

    def inspect_elf(self, stream):
        data = stream.read()
        if data.startswith(b'SOURCE'):
            return ({'cls': 1, 'machine': 40}, [('/lib/ld-missing.so', False)])
        return None

    def classify_guest_target(self, root, guest, header):
        physical = root.joinpath(*guest.split('/')[1:])
        if not physical.exists():
            return 'GUEST_ABSENT_HOLD', 0
        if physical.is_file() and physical.read_bytes().startswith(b'ARM'):
            return 'GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE', 0
        if physical.is_file() and physical.read_bytes().startswith(b'X86'):
            return 'GUEST_ELF_ABI_HEADER_MISMATCH_HOLD', 0
        return 'GUEST_REGULAR_NONELF_HOLD', 0


class TestR3727(unittest.TestCase):
    def test_expected_baseline_counts(self):
        self.assertEqual(m.EXPECTED['interp_segments'], 19)
        self.assertEqual(m.EXPECTED_PATHS['GUEST_ABSENT_HOLD'], 12)

    def test_parent_pin_refuses_missing(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.Hold) as ctx:
                m.verify_parent(Path(d) / m.PARENT_BASENAME)
            self.assertEqual(ctx.exception.category, 'PARENT_FILE_INVALID')

    def test_parent_pin_refuses_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / m.PARENT_BASENAME
            path.write_bytes(b'wrong')
            with self.assertRaises(m.Hold) as ctx:
                m.verify_parent(path)
            self.assertEqual(ctx.exception.category, 'PARENT_SHA256_MISMATCH')

    def test_parent_pin_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'real').write_bytes(b'wrong')
            alias = root / m.PARENT_BASENAME
            alias.symlink_to('real')
            with self.assertRaises(m.Hold) as ctx:
                m.verify_parent(alias)
            self.assertEqual(ctx.exception.category, 'PARENT_FILE_INVALID')

    def test_parent_baseline_valid(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(m.verified_baseline(Path(d), FakeParent())['counts'], m.EXPECTED)

    def test_parent_rejects_changed_path_counts(self):
        class Altered(FakeParent):
            def scan(self, root, n):
                output = super().scan(root, n)
                output['path_resolution_counts']['GUEST_ABSENT_HOLD'] -= 1
                return output
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.Hold) as ctx:
                m.verified_baseline(Path(d), Altered())
            self.assertEqual(ctx.exception.category, 'PARENT_PATH_COUNTS_HOLD')

    def test_no_same_basename(self):
        with tempfile.TemporaryDirectory() as d:
            cat, a, b, entries = m.candidate_category(Path(d), {}, '/lib/ld-missing.so', {}, FakeParent())
            self.assertEqual((cat,a,b,entries), ('NO_SAME_BASENAME_IN_STAGE',0,0,0))

    def test_one_regular_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'ld-missing.so').write_bytes(b'ARM')
            v=m.candidate_category(root, {'ld-missing.so':[(root/'ld-missing.so','regular')]}, '/lib/ld-missing.so', {}, FakeParent())
            self.assertEqual(v,('ONE_REGULAR_SAME_BASENAME_ABI_HEADER_CANDIDATE',1,0,1))

    def test_one_symlink_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'loader').write_bytes(b'ARM')
            (root/'ld-missing.so').symlink_to('loader')
            v=m.candidate_category(root,{'ld-missing.so':[(root/'ld-missing.so','link')]},'/lib/ld-missing.so',{},FakeParent())
            self.assertEqual(v[0],'ONE_SYMLINK_SAME_BASENAME_ABI_HEADER_CANDIDATE')

    def test_multiple_candidates(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'a').mkdir();(root/'b').mkdir()
            for sub in ('a','b'):
                (root/sub/'ld-missing.so').write_bytes(b'ARM')
            index={'ld-missing.so':[(root/'a/ld-missing.so','regular'),(root/'b/ld-missing.so','regular')]}
            v=m.candidate_category(root,index,'/lib/ld-missing.so',{},FakeParent())
            self.assertEqual(v,('MULTIPLE_SAME_BASENAME_ABI_HEADER_CANDIDATES',2,0,2))

    def test_incompatible_header(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'ld-missing.so').write_bytes(b'X86')
            v=m.candidate_category(root,{'ld-missing.so':[(root/'ld-missing.so','regular')]},'/lib/ld-missing.so',{},FakeParent())
            self.assertEqual(v[0],'SAME_BASENAME_ONLY_INCOMPATIBLE_ELF_HEADER')

    def test_nonelf_only(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'ld-missing.so').write_bytes(b'TEXT')
            v=m.candidate_category(root,{'ld-missing.so':[(root/'ld-missing.so','regular')]},'/lib/ld-missing.so',{},FakeParent())
            self.assertEqual(v[0],'SAME_BASENAME_ONLY_NONMATCHING_OR_UNRESOLVED')

    def test_no_path_leak_and_12_segments(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            # One source in a synthetic 1446-file stage, but FakeParent baseline
            # expects exactly 12 absent segments; independently replay holds.
            (root/'elf').write_bytes(b'SOURCE')
            for i in range(1445):
                (root/('regular-%04d' % i)).write_bytes(b'TEXT')
            with self.assertRaises(m.Hold) as ctx:
                m.audit(root, FakeParent())
            self.assertEqual(ctx.exception.category,'INDEPENDENT_REPLAY_HOLD')

    def test_synthetic_integration_twelve_absent_segments(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'bin').mkdir()
            (root/'usr/lib').mkdir(parents=True)
            # Same basename in the wrong guest directory is not an actual
            # resolution, even if an alternative ELF header would be compatible.
            (root/'usr/lib/ld-missing.so').write_bytes(b'ARM')
            for i in range(12):
                (root/'bin'/('elf-%02d' % i)).write_bytes(b'SOURCE')
            for i in range(1433):
                (root/('ordinary-%04d' % i)).write_bytes(b'TEXT')
            result=m.audit(root, FakeParent())
            self.assertEqual(result['result'],'ABSENT_INTERP_SAME_BASENAME_ALTERNATIVES_CLASSIFIED_ONLY')
            self.assertEqual(result['absent_interp_segments'],12)
            self.assertEqual(result['rootfs_regular_files'],1446)
            self.assertEqual(result['distinct_absent_guest_path_literals'],1)
            self.assertEqual(result['same_basename_alternative_categories'],{
                'ONE_REGULAR_SAME_BASENAME_ABI_HEADER_CANDIDATE':12})
            self.assertFalse(result['missing_guest_paths_resolved'])
            self.assertFalse(result['boot_authorized'])
            self.assertFalse(result['runtime_loader_resolved'])
            self.assertNotIn('ld-missing.so',json.dumps(result))

    def test_no_runtime_claims_in_status(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            self.assertEqual(m.EXPECTED_PATHS['GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE'],7)
            self.assertNotIn('execute',m.candidate_category(root,{},'/lib/x.so',{},FakeParent())[0].lower())


if __name__=='__main__':
    unittest.main()
