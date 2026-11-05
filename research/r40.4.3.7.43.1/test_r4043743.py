"""R3743 synthetic-only tests: no original R13 stage, hardware or execution."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from collections import Counter

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pw3_r3743_unit', HERE/'R4043743-STAGED-ELF-WEAK-EXPORT-SURVEY-READONLY.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
r42=m.load_pinned_parent(HERE)
sp=importlib.util.spec_from_file_location('pw3_r3742_unit_fixture',HERE/'test_r4043742.py')
t42=importlib.util.module_from_spec(sp);sp.loader.exec_module(t42)


def fixtures():
    sources,providers,contexts=t42.fake()
    # R3742 Mac result: 42 local weak, of which nine match the direct providers.
    for i in range(1,10):
        sources[0]['symbols'][i]['name']=b'exported'
    # The two unversioned missing entries are also weak and STT_NOTYPE.
    for i in (43,44):
        sources[0]['symbols'][i]['binding']=2
        sources[0]['symbols'][i]['type']=0
    return sources,providers,contexts


def testobj(names):
    return {'symbols':[{'name':n,'defined':True,'binding':1,'visibility':0} for n in names]}


class TestPins(unittest.TestCase):
    def test_parent_checksum(self):
        self.assertEqual(hashlib.sha256((HERE/m.PARENT).read_bytes()).hexdigest(), m.PARENT_SHA256)
    def test_pinned_parent_import(self):
        self.assertTrue(callable(r42.audit))
    def test_missing_parent_hold(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.Hold):m.load_pinned_parent(Path(d))
    def test_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/m.PARENT).write_text('tampered')
            with self.assertRaises(m.Hold) as e:m.load_pinned_parent(Path(d))
            self.assertEqual(e.exception.category,'R3742_PARENT_SOURCE_SHA_HOLD')
    def test_historical_hold(self):
        self.assertEqual(r42.PARENT_SHA256,'596b21871833423a2050828457b7a52c823b87605d0c9839542a3ec582f970d0')

class TestTargetSelection(unittest.TestCase):
    def test_33_2_targets(self):
        src,prov,_=fixtures()
        names=m.missing_weak_targets(src,prov)
        self.assertEqual(Counter(k for k,_ in names),{'LOCAL_INDEX_ZERO':33,'UNVERSIONED_WEAK':2})
    def test_strong_unversioned_refuses(self):
        src,prov,_=fixtures();src[0]['symbols'][43]['binding']=1
        with self.assertRaises(m.Hold):m.missing_weak_targets(src,prov)
    def test_nonzero_local_type_refuses(self):
        src,prov,_=fixtures();src[0]['symbols'][10]['type']=2
        with self.assertRaises(m.Hold):m.missing_weak_targets(src,prov)
    def test_new_direct_provider_refuses(self):
        src,prov,_=fixtures();prov.append(testobj([b'weak_10']))
        with self.assertRaises(m.Hold):m.missing_weak_targets(src,prov)
    def test_version_length_refuses(self):
        src,prov,_=fixtures();src[0]['versym'].pop()
        with self.assertRaises(m.Hold):m.missing_weak_targets(src,prov)
    def test_name_bytes_not_exported(self):
        src,prov,_=fixtures()
        names=m.missing_weak_targets(src,prov)
        out=m.compare_extra_targets(names,src,{},{});
        self.assertNotIn('weak_10',str(out))
        self.assertNotIn('missing_43',str(out))
    def test_empty_undefined_name_holds(self):
        src,prov,_=fixtures();src[0]['symbols'][10]['name']=b''
        with self.assertRaises(m.Hold):m.missing_weak_targets(src,prov)

class TestVisibleExportFilter(unittest.TestCase):
    def test_eligible(self):
        xs=[{'name':b'foo','defined':True,'binding':1,'visibility':0},
            {'name':b'bar','defined':True,'binding':2,'visibility':3}]
        self.assertEqual(m.exported_names(xs),{b'foo',b'bar'})
    def test_gnu_unique_eligible(self):
        self.assertEqual(m.exported_names([{'name':b'x','defined':True,'binding':10,'visibility':0}]),{b'x'})
    def test_undefined_not_eligible(self):
        self.assertEqual(m.exported_names([{'name':b'foo','defined':False,'binding':1,'visibility':0}]),set())
    def test_local_not_eligible(self):
        self.assertEqual(m.exported_names([{'name':b'foo','defined':True,'binding':0,'visibility':0}]),set())
    def test_hidden_not_eligible(self):
        self.assertEqual(m.exported_names([{'name':b'foo','defined':True,'binding':1,'visibility':2}]),set())

class TestComparison(unittest.TestCase):
    def test_empty_additional_categorical(self):
        src,prov,_=fixtures(); names=m.missing_weak_targets(src,prov)
        out=m.compare_extra_targets(names,src,{}, {'additional_dynamic_elf_parser_refusals':0})
        self.assertEqual(out['additional_name_candidate_categories']['NO_NAME_CANDIDATE_IN_PARSED_ADDITIONAL_FILES'],35)
        self.assertTrue(out['all_additional_dynamic_elfs_parsed'])
    def test_some_other_export_names(self):
        src,prov,_=fixtures();names=m.missing_weak_targets(src,prov)
        with tempfile.TemporaryDirectory() as d:
            other={b'weak_10':{Path(d)/'x'},b'missing_43':{Path(d)/'x'}}
            out=m.compare_extra_targets(names,src,other, {'additional_dynamic_elf_parser_refusals':0})
            self.assertEqual(out['additional_name_candidate_categories']['OTHER_STAGE_ELF_EXPORT_NAME_ONLY'],2)
            self.assertEqual(out['additional_regular_elf_export_file_matches_across_target_entries'],2)
    def test_source_and_other(self):
        src,prov,_=fixtures();names=m.missing_weak_targets(src,prov)
        src[0]['symbols'].append({'name':b'weak_10','defined':True,'binding':1,'visibility':0})
        out=m.compare_extra_targets(names,src,{b'weak_10':{Path('elsewhere')}},{})
        self.assertEqual(out['additional_name_candidate_categories']['SOURCE_AND_OTHER_STAGE_EXPORT_NAME'],1)
    def test_source_only(self):
        src,prov,_=fixtures();names=m.missing_weak_targets(src,prov)
        src[0]['symbols'].append({'name':b'weak_10','defined':True,'binding':1,'visibility':0})
        out=m.compare_extra_targets(names,src,{}, {})
        self.assertEqual(out['additional_name_candidate_categories']['SOURCE_ELF_EXPORT_NAME_ONLY'],1)
    def test_not_complete_with_parser_refusals(self):
        src,prov,_=fixtures();names=m.missing_weak_targets(src,prov)
        out=m.compare_extra_targets(names,src,{}, {'additional_dynamic_elf_parser_refusals':3})
        self.assertFalse(out['all_additional_dynamic_elfs_parsed'])
        self.assertTrue(out['no_match_in_parsed_files_does_not_prove_absent_runtime_symbol'])
    def test_bad_target_count_holds(self):
        src,prov,_=fixtures();names=m.missing_weak_targets(src,prov)
        with self.assertRaises(m.Hold):m.compare_extra_targets(names[:-1],src,{}, {})
    def test_bad_group_count_holds(self):
        src,prov,_=fixtures();names=m.missing_weak_targets(src,prov)
        names[0]=('UNVERSIONED_WEAK',names[0][1])
        with self.assertRaises(m.Hold):m.compare_extra_targets(names,src,{}, {})
    def test_zero_private_strings(self):
        src,prov,_=fixtures();names=m.missing_weak_targets(src,prov)
        out=m.compare_extra_targets(names,src,{b'weak_10':{Path('PRIVATE_NAME')}},{})
        self.assertNotIn('PRIVATE_NAME',str(out))
        self.assertNotIn('weak_10',str(out))

class TestStageEnumeration(unittest.TestCase):
    def test_regular_non_elf_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'not_elf').write_bytes(b'ordinary')
            called=[]
            def parser(path):
                called.append(path)
                return testobj([])
            parser.hold_types=(ValueError,)
            exports,count=m.bounded_elf_inventory(root,t42.p26,set(),set(),parser)
            self.assertEqual(exports,{})
            self.assertEqual(count['other_regular_stage_files_seen'],1)
            self.assertFalse(called)
    def test_elf_without_dynamic_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'static.elf').write_bytes(t42.t40.fixture()[:52])
            # Truncated valid header with PH table but missing bytes must hold, not skip.
            with self.assertRaises(m.Hold):m.probe_arm32_dynamic(t42.p26,root/'static.elf')
    def test_no_follow_file_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'real').write_bytes(b'n')
            (root/'link').symlink_to('real')
            def parser(path):return testobj([])
            parser.hold_types=(ValueError,)
            _,counts=m.bounded_elf_inventory(root,t42.p26,set(),set(),parser)
            self.assertEqual(counts['other_regular_stage_files_seen'],1)
    def test_parser_refusal_not_miscounted_as_negative(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'elf').write_bytes(t42.t40.fixture())
            def parser(path):raise ValueError('fixture cannot parse')
            parser.hold_types=(ValueError,)
            _,counts=m.bounded_elf_inventory(root,t42.p26,set(),set(),parser)
            self.assertEqual(counts['additional_dynamic_elf_parser_refusals'],1)
            self.assertEqual(counts.get('additional_dynamic_elf_parsed',0),0)
    def test_valid_export_candidate_collected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'fixture';p.write_bytes(t42.t40.fixture())
            def parser(path):return testobj([b'target_name'])
            parser.hold_types=(ValueError,)
            exports,counts=m.bounded_elf_inventory(root,t42.p26,set(),set(),parser)
            self.assertEqual(exports[b'target_name'],{p})
            self.assertEqual(counts['additional_dynamic_elf_parsed'],1)
    def test_source_not_additional(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'fixture';p.write_bytes(t42.t40.fixture())
            def parser(path):raise AssertionError('must be skipped')
            parser.hold_types=(ValueError,)
            _,counts=m.bounded_elf_inventory(root,t42.p26,{p},set(),parser)
            self.assertEqual(counts.get('additional_dynamic_elf_parsed',0),0)
    def test_unexpected_parser_failure_propagates(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'fixture').write_bytes(t42.t40.fixture())
            def parser(path):raise RuntimeError('unexpected')
            parser.hold_types=(ValueError,)
            with self.assertRaises(RuntimeError):m.bounded_elf_inventory(root,t42.p26,set(),set(),parser)

if __name__=='__main__':unittest.main()
