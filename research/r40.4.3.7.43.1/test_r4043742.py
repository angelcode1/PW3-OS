"""Synthetic-only R3742 regression tests, no user stage or Kindle device."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pw3_r3742_test',HERE/'R4043742-UNRESOLVED-WEAK-RELOCATION-READONLY.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p11=m.load_parent(HERE)
original=p11.load_original(HERE)
p40=original.load_parent(HERE)
testspec=importlib.util.spec_from_file_location('pw3_test_r3740_for_r3742',HERE/'test_r4043740.py')
t40=importlib.util.module_from_spec(testspec);testspec.loader.exec_module(t40)
p26=t40.p26


def fake():
    """632 synthetic undefined refs, split 42 local / 2 absent / 588 present."""
    symbols=[{'name':b'', 'defined':False,'binding':0,'type':0,'visibility':0}]
    versym=[0]; refs=set(); contexts={}
    for i in range(1,633):
        if i<=42:
            sym={'name':('weak_'+str(i)).encode(),'defined':False,'binding':2,'type':0,'visibility':0}
            ver=0;reloc=23
        elif i<=44:
            sym={'name':('missing_'+str(i)).encode(),'defined':False,'binding':1,'type':2,'visibility':0}
            ver=1;reloc=22
        else:
            sym={'name':b'exported','defined':False,'binding':1,'type':2,'visibility':0}
            ver=2;reloc=21
        symbols.append(sym);versym.append(ver);refs.add(i);contexts[i]={('REL',reloc):1}
    source={'symbols':symbols,'versym':versym,'referenced_indices':refs,'verneed':{2:{'version':b'V'}}}
    provider={'symbols':[{'name':b'exported','defined':True,'binding':1,'type':2,'visibility':0}]}
    return [source],[provider],[contexts]


class TestPin(unittest.TestCase):
    def test_exact_parent_sha(self):
        import hashlib
        self.assertEqual(hashlib.sha256((HERE/m.PARENT).read_bytes()).hexdigest(),m.PARENT_SHA256)
    def test_missing_parent_holds(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.Hold):m.load_parent(Path(d))
    def test_tampered_parent_holds(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/m.PARENT).write_bytes(b'tampered')
            with self.assertRaises(m.Hold) as e:m.load_parent(Path(d))
            self.assertEqual(e.exception.code,'PARENT_SOURCE_OR_SHA_HOLD')
    def test_original_historical_hold_unchanged(self):
        self.assertEqual(p11.ORIGINAL_SHA256,'d598134eb1709be0a8b0729834ee6bfe837663f2aabb4341b73aaa46b6e86e69')


class TestRelocationReader(unittest.TestCase):
    def read(self, **params):
        b=t40.fixture(**params)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.elf';p.write_bytes(b)
            return m.relocation_context(p26,p40,p,4,1)
    def test_valid_rel_record(self):
        refs,totals=self.read()
        self.assertEqual(refs,{2:{('REL',22):1}})
        self.assertEqual(totals['TOTAL'],1)
    def test_zero_symbol_index_not_tracked(self):
        refs,counts=self.read(sym_index=0)
        self.assertEqual(refs,{})
        self.assertEqual(counts['TOTAL'],1)
    def test_relocation_type_kept_as_numeric(self):
        refs,_=self.read(reloc_type=19)
        self.assertEqual(refs[2][('REL',19)],1)
    def test_index_out_of_bounds_holds(self):
        with self.assertRaises(m.Hold) as e:self.read(bad_reloc=True)
        self.assertEqual(e.exception.code,'RELOCATION_SYMBOL_INDEX_HOLD')
    def test_wrong_expected_record_count_holds(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.elf';p.write_bytes(t40.fixture())
            with self.assertRaises(m.Hold) as e:m.relocation_context(p26,p40,p,4,2)
            self.assertEqual(e.exception.code,'R3740_RELOCATION_TOTAL_REPLAY_HOLD')
    def test_bad_elf_holds(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.elf';p.write_bytes(b'not an ELF')
            with self.assertRaises((m.Hold, p26.Hold)):m.relocation_context(p26,p40,p,4,1)
    def test_no_private_symbol_names_from_relocation_reader(self):
        output=self.read()
        self.assertNotIn('bar',str(output))


class TestWeakTriage(unittest.TestCase):
    def test_accounting(self):
        src,prov,ctx=fake()
        result=m.compare_review_relocations(src,prov,ctx)
        self.assertEqual(result['local_index_weak_symbol_entries'],42)
        self.assertEqual(result['local_index_weak_relocation_sites'],42)
        self.assertEqual(result['no_staged_provider_name_entries'],2)
        self.assertEqual(result['no_staged_provider_name_relocation_sites'],2)
        self.assertTrue(result['weak_local_version_zero_remains_review'])
    def test_weak_relocation_types(self):
        src,prov,ctx=fake()
        result=m.compare_review_relocations(src,prov,ctx)
        self.assertEqual(result['local_index_weak_relocation_type_counts'],{'23':42})
    def test_unmatched_relocation_type(self):
        src,prov,ctx=fake()
        self.assertEqual(m.compare_review_relocations(src,prov,ctx)['no_staged_provider_name_relocation_type_counts'],{'22':2})
    def test_weak_binds_no_candidates_without_match(self):
        src,prov,ctx=fake()
        results=m.compare_review_relocations(src,prov,ctx)
        self.assertEqual(results['local_index_weak_relocation_context_categories']['LOCAL_NAME_ZERO_PROVIDER'],42)
    def test_mismatch_context_length_holds(self):
        src,prov,ctx=fake()
        with self.assertRaises(m.Hold):m.compare_review_relocations(src,prov,[])
    def test_not_referenced_symbol_holds(self):
        src,prov,ctx=fake()
        ctx[0].pop(1)
        with self.assertRaises(m.Hold):m.compare_review_relocations(src,prov,ctx)
    def test_wrong_weak_binding_holds(self):
        src,prov,ctx=fake()
        src[0]['symbols'][1]['binding']=1
        with self.assertRaises(m.Hold):m.compare_review_relocations(src,prov,ctx)
    def test_wrong_local_type_holds(self):
        src,prov,ctx=fake()
        src[0]['symbols'][1]['type']=2
        with self.assertRaises(m.Hold):m.compare_review_relocations(src,prov,ctx)
    def test_nonlocal_weak_index_without_provider_counted_separately(self):
        src,prov,ctx=fake()
        src[0]['symbols'][43]['binding']=2
        self.assertEqual(m.compare_review_relocations(src,prov,ctx)['no_staged_provider_name_symbol_categories']['STB_2'],1)
    def test_private_names_are_not_exported(self):
        src,prov,ctx=fake()
        src[0]['symbols'][1]['name']=b'private_secret_identifier'
        out=str(m.compare_review_relocations(src,prov,ctx))
        self.assertNotIn('private_secret_identifier',out)
        self.assertNotIn('exported',out)
    def test_local_with_provider_name_is_still_review(self):
        src,prov,ctx=fake()
        src[0]['symbols'][1]['name']=b'exported'
        out=m.compare_review_relocations(src,prov,ctx)
        self.assertEqual(out['local_index_weak_relocation_context_categories']['LOCAL_NAME_ONE_PROVIDER'],1)
        self.assertTrue(out['weak_local_version_zero_remains_review'])
    def test_extra_relocation_sites_counts_independently(self):
        src,prov,ctx=fake()
        ctx[0][1][('PLT',22)]=2
        out=m.compare_review_relocations(src,prov,ctx)
        self.assertEqual(out['local_index_weak_relocation_sites'],44)
        self.assertEqual(out['local_index_weak_relocation_type_counts']['22'],2)

if __name__=='__main__':unittest.main()
