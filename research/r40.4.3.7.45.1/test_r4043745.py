"""Synthetic-only R3745 PLT/GOT original-word geometry tests. No Kindle access."""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import struct
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent
S=ROOT/'R4043745-WEAK-PLT-INITIAL-TARGET-READONLY.py'
spec=importlib.util.spec_from_file_location('r3745',S)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p44=m.load_parent(ROOT)
oldspec=importlib.util.spec_from_file_location('r3744tests_for_r3745',ROOT/'test_r4043744.py')
t44=importlib.util.module_from_spec(oldspec);oldspec.loader.exec_module(t44)
p26=t44.p26


def sample(raw,groups=None):
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/'sample.elf';path.write_bytes(raw)
        return m.read_weak_plt_words(p26,p44,path,{2:'LOCAL_ZERO_NAME_IN_SIX'} if groups is None else groups)


def with_pltgot(raw,value):
    b=bytearray(raw)
    # R3744 fixture has seven baseline dynamic descriptors, and three PLT descriptors.
    struct.pack_into('<II',b,0x100+10*8,3,value)
    struct.pack_into('<II',b,0x100+11*8,0,0)
    struct.pack_into('<I',b,84+16,12*8)
    struct.pack_into('<I',b,84+20,12*8)
    return bytes(b)


class TestR3745Pins(unittest.TestCase):
    def test_parent_exact_sha(self):
        self.assertEqual(hashlib.sha256((ROOT/m.PARENT).read_bytes()).hexdigest(),m.PARENT_SHA256)
    def test_parent_audit_callable(self):
        self.assertTrue(callable(p44.audit))
    def test_bad_parent_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            x=Path(t)/m.PARENT;x.write_bytes(b'tampered')
            with self.assertRaises(m.Hold):m.load_parent(Path(t))
    def test_missing_parent_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(m.Hold):m.load_parent(Path(t))


class TestWordGeometry(unittest.TestCase):
    def setUp(self):
        self.l=[(0x1000,0,0x100,0x100,5),(0x2000,0x100,0x100,0x200,6)]
    def test_executable(self):self.assertEqual(m.classify_plt_original_word(0x1040,self.l)[0],'ORIGINAL_WORD_IN_OWN_EXEC_PT_LOAD')
    def test_thumb_lowbit(self):self.assertEqual(m.classify_plt_original_word(0x1041,self.l),('ORIGINAL_WORD_IN_OWN_EXEC_PT_LOAD','LOW_BIT_SET'))
    def test_nonexec(self):self.assertEqual(m.classify_plt_original_word(0x2100,self.l)[0],'ORIGINAL_WORD_IN_OWN_NONEXEC_PT_LOAD')
    def test_outside(self):self.assertEqual(m.classify_plt_original_word(0x9000,self.l)[0],'ORIGINAL_WORD_OUTSIDE_OWN_PT_LOAD')
    def test_zero(self):self.assertEqual(m.classify_plt_original_word(0,self.l)[0],'ORIGINAL_WORD_ZERO_REVIEW')
    def test_overlap(self):self.assertEqual(m.classify_plt_original_word(0x1040,self.l+self.l[:1])[0],'ORIGINAL_WORD_AMBIGUOUS_OWN_PT_LOAD')
    def test_overflow(self):
        with self.assertRaises(m.Hold):m.classify_plt_original_word(0x100000000,self.l)
    def test_negative(self):
        with self.assertRaises(m.Hold):m.classify_plt_original_word(-1,self.l)
    def test_empty_load(self):self.assertEqual(m.classify_plt_original_word(0x1040,[])[0],'ORIGINAL_WORD_OUTSIDE_OWN_PT_LOAD')
    def test_no_private_word_export(self):self.assertNotIn('0x1040',str(m.classify_plt_original_word(0x1040,self.l)))


class TestPltgot(unittest.TestCase):
    def setUp(self):self.l=[(0x1000,0,0x100,0x100,5),(0x2000,0x100,0x100,0x100,6)]
    def test_absent(self):self.assertEqual(m.classify_pltgot_tag({},self.l),'DT_PLTGOT_ABSENT')
    def test_writable(self):self.assertEqual(m.classify_pltgot_tag({3:0x2000},self.l),'DT_PLTGOT_IN_WRITABLE_LOAD')
    def test_nonwritable(self):self.assertEqual(m.classify_pltgot_tag({3:0x1000},self.l),'DT_PLTGOT_IN_NONWRITABLE_LOAD_REVIEW')
    def test_outside(self):self.assertEqual(m.classify_pltgot_tag({3:0x7000},self.l),'DT_PLTGOT_OUTSIDE_LOAD_REVIEW')
    def test_ambiguous(self):self.assertEqual(m.classify_pltgot_tag({3:0x2000},self.l+[self.l[1]]),'DT_PLTGOT_AMBIGUOUS_LOAD_REVIEW')


class TestStaticPltParser(unittest.TestCase):
    def test_one_target(self):
        rows,got,n=sample(t44.fixture_bytes(plt=True,slot_value=0x1100))
        self.assertEqual((got,n),('DT_PLTGOT_ABSENT',1))
        self.assertEqual(rows['LOCAL_ZERO_NAME_IN_SIX'][('WORD','ORIGINAL_WORD_IN_OWN_NONEXEC_PT_LOAD')],1)
    def test_zero_original(self):
        rows,_,n=sample(t44.fixture_bytes(plt=True))
        self.assertEqual(rows['LOCAL_ZERO_NAME_IN_SIX'][('WORD','ORIGINAL_WORD_ZERO_REVIEW')],1)
    def test_non_target(self):
        rows,_,n=sample(t44.fixture_bytes(plt=True),{3:'LOCAL_ZERO_NAME_IN_SIX'})
        self.assertEqual((rows,n),({},0))
    def test_no_plt_can_contain_rel_target(self):
        rows,_,n=sample(t44.fixture_bytes(),{2:'LOCAL_ZERO_NAME_IN_SIX'})
        self.assertEqual((rows,n),({},0))
    def test_present_pltgot(self):
        raw=with_pltgot(t44.fixture_bytes(plt=True),0x1500)
        rows,got,n=sample(raw)
        self.assertEqual(got,'DT_PLTGOT_IN_WRITABLE_LOAD')
        self.assertEqual(n,1)
    def test_plt_no_needed_target(self):
        rows,got,n=sample(t44.fixture_bytes(plt=True),{})
        self.assertEqual(n,0)
    def test_nonwritable_slot_rejected(self):
        with self.assertRaises(m.Hold):sample(t44.fixture_bytes(plt=True,writable=False))
    def test_invalid_plt_reloc_type_rejected(self):
        raw=bytearray(t44.fixture_bytes(plt=True));struct.pack_into('<I',raw,0x404,(2<<8)|21)
        with self.assertRaises(m.Hold):sample(bytes(raw))
    def test_missing_plt_descriptor_rejected(self):
        raw=bytearray(t44.fixture_bytes(plt=True))
        # Remove DT_PLTREL but keep DT_JMPREL and DT_PLTRELSZ.
        struct.pack_into('<II',raw,0x100+9*8,0,0)
        with self.assertRaises(m.Hold):sample(bytes(raw))
    def test_plt_offset_not_writable_rejected(self):
        raw=bytearray(t44.fixture_bytes(plt=True))
        struct.pack_into('<I',raw,0x400,0x9000)
        with self.assertRaises(m.Hold):sample(bytes(raw))
    def test_plt_bad_index_not_targeted(self):
        rows,_,n=sample(t44.fixture_bytes(plt=True),{10:'LOCAL_ZERO_NAME_IN_SIX'})
        self.assertEqual(n,0)


class TestWeakTargetGrouping(unittest.TestCase):
    def test_local_present(self):
        src={'symbols':[{'name':b'', 'defined':False,'binding':0,'type':0},{'name':b'x','defined':False,'binding':2,'type':0}],
             'referenced_indices':{1},'versym':[0,0]}
        self.assertEqual(m.choose_weak_targets(src,{b'x'}),{1:'LOCAL_ZERO_NAME_IN_SIX'})
    def test_local_absent(self):
        src={'symbols':[{'name':b'', 'defined':False,'binding':0,'type':0},{'name':b'x','defined':False,'binding':2,'type':0}],
             'referenced_indices':{1},'versym':[0,0]}
        self.assertEqual(m.choose_weak_targets(src,set()),{1:'LOCAL_ZERO_NAME_NOT_IN_SIX'})
    def test_unversioned_absent(self):
        src={'symbols':[{'name':b'', 'defined':False,'binding':0,'type':0},{'name':b'x','defined':False,'binding':2,'type':0}],
             'referenced_indices':{1},'versym':[0,1]}
        self.assertEqual(m.choose_weak_targets(src,set()),{1:'UNVERSIONED_WEAK_NAME_NOT_IN_SIX'})
    def test_versioned_skipped(self):
        src={'symbols':[{'name':b'', 'defined':False,'binding':0,'type':0},{'name':b'x','defined':False,'binding':2,'type':0}],
             'referenced_indices':{1},'versym':[0,2]}
        self.assertEqual(m.choose_weak_targets(src,set()),{})
    def test_wrong_binding_rejected(self):
        src={'symbols':[{'name':b'', 'defined':False,'binding':0,'type':0},{'name':b'x','defined':False,'binding':1,'type':0}],
             'referenced_indices':{1},'versym':[0,0]}
        with self.assertRaises(m.Hold):m.choose_weak_targets(src,set())

if __name__=='__main__':unittest.main()
