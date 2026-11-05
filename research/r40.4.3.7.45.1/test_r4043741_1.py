"""R3741.1 offline regressions: only synthetic ELF fixtures, never stage/device."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    'pw3_r3741_1_local_index_review', HERE / 'R4043741-1-LOCAL-VERSION-REVIEW-READONLY.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
old = m.load_original(HERE)
OLDTEST = importlib.util.spec_from_file_location('pw3_r3741_older_test', HERE / 'test_r4043741.py')
t = importlib.util.module_from_spec(OLDTEST)
OLDTEST.loader.exec_module(t)


def source(version=0, name=b'foo', binding=1, symtype=2):
    v=t.source(version=version,name=name)
    v['symbols'][1]['binding'] = binding
    v['symbols'][1]['type'] = symtype
    return v


def one(src=None, providers=None):
    return m.classify_with_local_review(
        [src if src is not None else source()],
        providers if providers is not None else [t.provider()])


class TestSHAAndOriginalHold(unittest.TestCase):
    def test_original_source_sha_pinned(self):
        import hashlib
        actual=hashlib.sha256((HERE/m.ORIGINAL).read_bytes()).hexdigest()
        self.assertEqual(actual,m.ORIGINAL_SHA256)
    def test_wrong_sha_refused(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/m.ORIGINAL).write_text('tampered')
            with self.assertRaises(m.Hold) as exc:
                m.load_original(Path(d))
            self.assertEqual(exc.exception.code,'ORIGINAL_R3741_SOURCE_SHA_HOLD')
    def test_missing_original_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.Hold):m.load_original(Path(d))
    def test_original_still_holds_local_version(self):
        with self.assertRaises(old.Hold) as exc:
            old.classify_version_candidates([source()],[t.provider()])
        self.assertEqual(exc.exception.code,'UNDEFINED_LOCAL_VERSION_HOLD')


class TestZeroVersionReview(unittest.TestCase):
    def test_global_undefined_local_version_is_review_not_accept(self):
        data=one()
        self.assertEqual(data['version_filtered_static_candidate_categories'],
                         {'UNDEFINED_LOCAL_VERSION_INDEX_REVIEW':1})
        self.assertTrue(data['local_version_index_review']['remains_unresolved'])
        self.assertTrue(data['local_version_index_zero_is_never_counted_as_resolved'])
        self.assertEqual(data['local_version_index_review']['binding_categories'],{'STB_GLOBAL':1})
    def test_stb_local_undefined_local_version_remains_unresolved(self):
        data=one(source(binding=0))
        self.assertEqual(data['local_version_index_review']['binding_categories'],{'STB_LOCAL':1})
        self.assertNotIn('ONE_DEFAULT_OR_UNVERSIONED_NAME_CANDIDATE',
                         data['version_filtered_static_candidate_categories'])
    def test_weak_undefined_local_version_remains_unresolved(self):
        data=one(source(binding=2))
        self.assertEqual(data['local_version_index_review']['binding_categories'],{'STB_WEAK':1})
    def test_unsupported_binding_counts_other(self):
        data=one(source(binding=12))
        self.assertEqual(data['local_version_index_review']['binding_categories'],{'STB_OTHER':1})
    def test_hidden_bit_is_counted_not_accepted(self):
        data=one(source(version=0x8000))
        self.assertEqual(data['local_version_index_review']['hidden_bit_set'],1)
    def test_empty_name_local_remains_review(self):
        data=one(source(name=b''))
        self.assertEqual(data['local_version_index_review']['empty_symbol_name_entries'],1)
        self.assertEqual(data['distinct_undefined_names_reverified'],0)
        self.assertEqual(data['version_filtered_static_candidate_categories'],
                         {'LOCAL_VERSION_INDEX_EMPTY_NAME_REVIEW':1})
    def test_local_name_not_exported(self):
        data=one(source(name=b'secret_loader_name'),[t.provider(name=b'secret_loader_name')])
        self.assertNotIn('secret_loader_name',repr(data))
        self.assertNotIn('LIB_1',repr(data))
    def test_mixed_local_explicit_and_global_accounting(self):
        src=source(name=b'local')
        src['symbols'] += [t.record(b'needed',False), t.record(b'plain',False)]
        src['symbols'][2]['type']=2;src['symbols'][3]['type']=2
        src['versym'] += [2,1]
        src['referenced_indices']={1,2,3}
        providers=[t.provider(name=b'needed'),t.provider(version=1,name=b'plain')]
        data=one(src,providers)
        self.assertEqual(data['referenced_undefined_entries_reclassified'],3)
        self.assertEqual(sum(data['version_filtered_static_candidate_categories'].values()),3)
        self.assertEqual(sum(data['source_symbol_version_requirement_categories'].values()),3)
        self.assertEqual(data['source_symbol_version_requirement_categories'],
            {'EXPLICIT_GNU_VERSION_REQUIREMENT':1,'LOCAL_VERSION_INDEX_REQUIRES_REVIEW':1,
             'UNVERSIONED_OR_GLOBAL_REFERENCE':1})
        self.assertEqual(data['version_filtered_static_candidate_categories'],
            {'ONE_DEFAULT_OR_UNVERSIONED_NAME_CANDIDATE':1,
             'ONE_GNU_VERSION_NAME_MATCHING_CANDIDATE':1,
             'UNDEFINED_LOCAL_VERSION_INDEX_REVIEW':1})
        self.assertEqual(data['distinct_undefined_names_reverified'],3)


class TestOtherVersionRulesPreserved(unittest.TestCase):
    def test_named_requirement_exact(self):
        self.assertEqual(one(source(version=2))['version_filtered_static_candidate_categories'],
                         {'ONE_GNU_VERSION_NAME_MATCHING_CANDIDATE':1})
    def test_named_requirement_different(self):
        self.assertEqual(one(source(version=2),[t.provider(vername=b'other')])['version_filtered_static_candidate_categories'],
                         {'NAME_CANDIDATE_BUT_NO_EQUAL_GNU_VERSION_NAME':1})
    def test_unversioned_default_candidate(self):
        self.assertEqual(one(source(version=1))['version_filtered_static_candidate_categories'],
                         {'ONE_DEFAULT_OR_UNVERSIONED_NAME_CANDIDATE':1})
    def test_unversioned_nondefault_review(self):
        self.assertEqual(one(source(version=1),[t.provider(hidden=True)])['version_filtered_static_candidate_categories'],
                         {'ONLY_NONDEFAULT_VERSIONED_NAME_CANDIDATES':1})
    def test_nonlocal_undefined_empty_name_holds(self):
        with self.assertRaises(m.Hold):one(source(version=1,name=b''))
    def test_missing_required_version_holds(self):
        with self.assertRaises(m.Hold):one(source(version=3))
    def test_provider_version_definition_missing_holds(self):
        p=t.provider();p['verdef']={}
        with self.assertRaises(m.Hold):one(source(version=2),[p])
    def test_source_versym_count_mismatch_holds(self):
        v=source();v['versym']=[]
        with self.assertRaises(m.Hold):one(v)
    def test_provider_versym_count_mismatch_holds(self):
        v=t.provider();v['versym']=[]
        with self.assertRaises(m.Hold):one(providers=[v])
    def test_oversized_source_symbol_index_holds(self):
        v=source();v['referenced_indices']={55}
        with self.assertRaises(m.Hold):one(v)


class TestActualVersionRecordFixture(unittest.TestCase):
    def test_filebacked_version_requirements(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fixture.elf';path.write_bytes(t.fixture(needed=True))
            data=old.parse_version_file(t.parent_tests.p26,t.p40,path)
            self.assertEqual(data['verneed'][2]['version'],b'LIB_1')
    def test_filebacked_version_definition(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'fixture.elf';path.write_bytes(t.fixture(needed=False))
            data=old.parse_version_file(t.parent_tests.p26,t.p40,path)
            self.assertEqual(data['verdef'][2],b'LIB_1')


if __name__=='__main__':unittest.main()
