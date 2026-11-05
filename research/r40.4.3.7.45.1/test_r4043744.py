"""Synthetic-only R3744 ARM weak relocation-slot preflight tests. No R13 writes."""
from collections import Counter
from io import BytesIO
import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
SRC=HERE/'R4043744-WEAK-RELOCATION-SLOT-PREFLIGHT-READONLY.py'
spec=importlib.util.spec_from_file_location('r3744_synthetic',SRC)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
parent=m.import_pinned(HERE)
spec40=importlib.util.spec_from_file_location('r3740_fixture_for_r3744',HERE/'test_r4043740.py')
t40=importlib.util.module_from_spec(spec40)
spec40.loader.exec_module(t40)
p26=t40.p26


def fixture_bytes(*, writable=True, slot_value=0, slot_offset=0x500, now=False, relro=False, plt=False, flags_now=False, flags1_now=False):
    b=bytearray(t40.fixture())
    struct.pack_into('<I',b,52+24,6 if writable else 4)
    if slot_offset + 4 <= len(b):struct.pack_into('<I',b,slot_offset,slot_value)
    additions=[]
    if now:additions.append((m.DT_BIND_NOW,0))
    if flags_now:additions.append((m.DT_FLAGS,m.DF_BIND_NOW))
    if flags1_now:additions.append((m.DT_FLAGS_1,m.DF_1_NOW))
    if plt:additions.extend([(23,0x1400),(2,8),(20,17)])
    if additions:
        for j,(tag,val) in enumerate(additions):struct.pack_into('<II',b,0x100+(7+j)*8,tag,val)
        struct.pack_into('<II',b,0x100+(7+len(additions))*8,0,0)
        newlen=(8+len(additions))*8
        struct.pack_into('<I',b,84+16,newlen)
        struct.pack_into('<I',b,84+20,newlen)
    if relro:
        struct.pack_into('<H',b,44,3) # ELF e_phnum
        struct.pack_into('<IIIIIIII',b,52+64,m.PT_GNU_RELRO,0x500,0x1500,0,4,4,4,4)
    return bytes(b)


def fake_weak_groups():
    sym0={'name':b'', 'defined':False,'binding':0,'type':0}
    symbols=[sym0];versym=[0];context={}
    for i in range(1,45):
        name=b'in_provider' if i<=9 else ('weak_%02d'%i).encode()
        symbols.append({'name':name,'defined':False,'binding':2,'type':0})
        versym.append(0 if i<=42 else 1)
        n=2 if i<=18 else 1
        context[i]={('TABLE','REL'):n,('TYPE','21'):n,('SLOT','WRITABLE_INITIAL_WORD_ZERO'):n,('RELRO','RELRO_OUTSIDE'):n}
    source={'symbols':symbols,'versym':versym,'referenced_indices':set(range(1,45))}
    other={'symbols':[sym0],'versym':[0],'referenced_indices':set()}
    provider={'symbols':[{'name':b'in_provider','defined':True,'binding':1,'visibility':0}]}
    allsources=[source]+[other]*11
    allsites=[context]+[{} for _ in range(11)]
    flags=[{'bind_now':False,'gnu_relro':False,'relocation_records':3499}]+[{'bind_now':False,'gnu_relro':False,'relocation_records':0} for _ in range(11)]
    return allsources,[provider],allsites,flags


class TestPins(unittest.TestCase):
    def test_original_sha(self):self.assertEqual(hashlib.sha256((HERE/m.PARENT).read_bytes()).hexdigest(),m.PARENT_SHA256)
    def test_parent_imports(self):self.assertTrue(callable(parent.audit))
    def test_missing_parent_holds(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.Hold):m.import_pinned(Path(d))
    def test_corrupt_parent_holds(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/m.PARENT).write_bytes(b'corrupt')
            with self.assertRaises(m.Hold) as ctx:m.import_pinned(Path(d))
            self.assertEqual(ctx.exception.category,'R3743_1_SOURCE_SHA_HOLD')


class TestSlotGeometry(unittest.TestCase):
    def read(self,loads,relro,vaddr,content=b'\0'*64,endian='<'):
        return m.classify_word_location(loads,relro,vaddr,BytesIO(content),p26,endian)
    def test_zero_word_file(self):
        self.assertEqual(self.read([(0x1000,0,32,64,6)],[],0x1000),('WRITABLE_INITIAL_WORD_ZERO','RELRO_OUTSIDE'))
    def test_nonzero_word_file(self):
        self.assertEqual(self.read([(0x1000,0,32,64,6)],[],0x1000,struct.pack('<I',100)+b'\0'*60)[0], 'WRITABLE_INITIAL_WORD_NONZERO')
    def test_big_endian_word(self):
        self.assertEqual(self.read([(0x1000,0,32,64,6)],[],0x1000,b'\0\0\0\x01'+b'\0'*60,'>')[0], 'WRITABLE_INITIAL_WORD_NONZERO')
    def test_bss_word(self):
        self.assertEqual(self.read([(0x1000,0,32,64,6)],[],0x1020)[0], 'WRITABLE_BSS_ZERO_INITIALIZED')
    def test_crosses_file_bss(self):
        self.assertEqual(self.read([(0x1000,0,17,64,6)],[],0x1010)[0], 'WRITABLE_CROSSES_FILE_BSS_BOUNDARY_REVIEW')
    def test_readonly_location(self):
        self.assertEqual(self.read([(0x1000,0,32,64,4)],[],0x1000)[0], 'NONWRITABLE_REVIEW_INITIAL_WORD_ZERO')
    def test_relro(self):
        self.assertEqual(self.read([(0x1000,0,32,64,6)],[(0x1000,16)],0x1000)[1],'RELRO_INSIDE')
    def test_outside_load(self):
        self.assertEqual(self.read([(0x1000,0,32,64,6)],[],0x3000)[0],'NO_CONTAINING_PT_LOAD_REVIEW')
    def test_unaligned(self):
        self.assertEqual(self.read([(0x1000,0,32,64,6)],[],0x1002)[0],'UNALIGNED_SLOT_REVIEW')
    def test_overlap(self):
        self.assertEqual(self.read([(0x1000,0,32,64,6),(0x1000,0,32,64,6)],[],0x1000)[0],'AMBIGUOUS_OVERLAPPING_PT_LOAD_REVIEW')
    def test_duplicate_relro_review(self):
        self.assertEqual(self.read([(0x1000,0,32,64,6)],[(0x1000,8),(0x1000,8)],0x1000)[1],'OVERLAPPING_RELRO_REVIEW')


class TestReloParser(unittest.TestCase):
    def classify(self,raw,index_set={2}):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.elf';p.write_bytes(raw)
            return m.read_relocation_sites(p26,p,index_set)
    def test_fixture_zero_word(self):
        sites,settings=self.classify(fixture_bytes())
        self.assertEqual(sites[2][('SLOT','WRITABLE_INITIAL_WORD_ZERO')],1)
        self.assertEqual(sites[2][('TYPE','22')],1)
        self.assertEqual(settings['relocation_records'],1)
    def test_fixture_nonzero_word(self):
        sites,_=self.classify(fixture_bytes(slot_value=0x12345678))
        self.assertEqual(sites[2][('SLOT','WRITABLE_INITIAL_WORD_NONZERO')],1)
    def test_nonwritable_pt_load_review(self):
        sites,_=self.classify(fixture_bytes(writable=False))
        self.assertEqual(sites[2][('SLOT','NONWRITABLE_REVIEW_INITIAL_WORD_ZERO')],1)
    def test_relro_and_now_flags(self):
        sites,settings=self.classify(fixture_bytes(relro=True,now=True))
        self.assertTrue(settings['bind_now'])
        self.assertTrue(settings['gnu_relro'])
        self.assertEqual(sites[2][('RELRO','RELRO_INSIDE')],1)
    def test_plt_relocation_record_counted_separately(self):
        sites, settings=self.classify(fixture_bytes(plt=True))
        self.assertEqual(settings['relocation_records'],2)
        self.assertEqual(sites[2][('TABLE','REL')],1)
        self.assertEqual(sites[2][('TABLE','PLT')],1)
    def test_dt_flags_bind_now(self):
        _,policy=self.classify(fixture_bytes(flags_now=True))
        self.assertTrue(policy['bind_now'])
    def test_dt_flags_1_now(self):
        _,policy=self.classify(fixture_bytes(flags1_now=True))
        self.assertTrue(policy['bind_now'])
    def test_relocation_target_outside_load_review(self):
        b=bytearray(fixture_bytes())
        struct.pack_into('<I',b,0x400,0x4000)
        sites,_=self.classify(bytes(b))
        self.assertEqual(sites[2][('SLOT','NO_CONTAINING_PT_LOAD_REVIEW')],1)
    def test_relocation_target_bss(self):
        b=bytearray(fixture_bytes())
        struct.pack_into('<I',b,52+20,0x800) # increase PT_LOAD memsz
        struct.pack_into('<I',b,0x400,0x1700)
        sites,_=self.classify(bytes(b))
        self.assertEqual(sites[2][('SLOT','WRITABLE_BSS_ZERO_INITIALIZED')],1)
    def test_not_targeted_symbol(self):
        sites,settings=self.classify(fixture_bytes(),{1})
        self.assertFalse(sites)
        self.assertEqual(settings['relocation_records'],1)
    def test_index_zero_is_not_referenced_weak(self):
        raw=bytearray(fixture_bytes())
        struct.pack_into('<I',raw,0x400+4,22)
        sites,_=self.classify(bytes(raw),{2})
        self.assertFalse(sites)
    def test_malformed_elf_holds(self):
        with self.assertRaises((m.Hold,t40.p26.Hold)):self.classify(b'not an ELF')
    def test_overflowing_reloc_table_holds(self):
        raw=bytearray(fixture_bytes())
        # DT_RELSZ at dynamic entry 5; set too large.
        struct.pack_into('<I',raw,0x100+5*8+4,65537*8)
        with self.assertRaises(m.Hold):self.classify(bytes(raw))
    def test_wrong_plt_descriptor_holds(self):
        raw=bytearray(fixture_bytes())
        # DT_RELENT at entry 6 -> 16, incompatible with REL.
        struct.pack_into('<I',raw,0x100+6*8+4,16)
        with self.assertRaises(m.Hold):self.classify(bytes(raw))


class TestGroupAggregation(unittest.TestCase):
    def test_groups_and_62_sites(self):
        result=m.aggregate(*fake_weak_groups())
        self.assertEqual(result['weak_reference_symbol_group_counts'],{'LOCAL_ZERO_NAME_IN_SIX':9,'LOCAL_ZERO_NAME_NOT_IN_SIX':33,'UNVERSIONED_WEAK_NAME_NOT_IN_SIX':2})
        self.assertEqual(result['weak_relocation_site_total'],62)
        self.assertEqual(result['requester_relocation_sites_reverified'],3499)
        self.assertEqual(result['weak_relocation_slot_categories_by_group']['LOCAL_ZERO_NAME_IN_SIX']['TYPE'],{'21':18})
    def test_no_paths_names_or_addresses(self):
        result=str(m.aggregate(*fake_weak_groups()))
        self.assertNotIn('in_provider',result)
        self.assertNotIn('weak_01',result)
        self.assertNotIn('4096',result)
    def test_missing_site_holds(self):
        s,p,sites,settings=fake_weak_groups();sites[0].pop(1)
        with self.assertRaises(m.Hold):m.aggregate(s,p,sites,settings)
    def test_wrong_weak_binding_holds(self):
        s,p,sites,settings=fake_weak_groups();s[0]['symbols'][1]['binding']=1
        with self.assertRaises(m.Hold):m.aggregate(s,p,sites,settings)
    def test_wrong_group_count_holds(self):
        s,p,sites,settings=fake_weak_groups();s[0]['symbols'][1]['name']=b'not_in_provider'
        with self.assertRaises(m.Hold):m.aggregate(s,p,sites,settings)
    def test_site_total_mismatch_holds(self):
        s,p,sites,settings=fake_weak_groups();sites[0][1][('TABLE','REL')]+=1
        with self.assertRaises(m.Hold):m.aggregate(s,p,sites,settings)
    def test_source_count_holds(self):
        s,p,sites,settings=fake_weak_groups()
        with self.assertRaises(m.Hold):m.aggregate(s[:-1],p,sites,settings)
    def test_root_missing_holds(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.Hold):m.audit(Path(d)/'missing',HERE,parent)

if __name__=='__main__':unittest.main()
