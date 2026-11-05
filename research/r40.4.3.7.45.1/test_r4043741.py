"""R3741 synthetic tests; stage, physical Kindle and original image not touched."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('r3741test',HERE/'R4043741-GNU-SYMBOL-VERSION-CANDIDATES-READONLY.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
p40=m.load_parent(HERE)
t=importlib.util.spec_from_file_location('r3740test_original',HERE/'test_r4043740.py')
parent_tests=importlib.util.module_from_spec(t);t.loader.exec_module(parent_tests)


def record(name=b'foo',defined=False,binding=1,visibility=0):
    return dict(name=name,defined=defined,binding=binding,visibility=visibility)


def source(version=2,name=b'foo',weak=False):
    return dict(symbols=[record(b'',False,0),record(name)],referenced_indices={1},
                versym=[0,version],verneed={2:dict(version=b'LIB_1',weak=weak)},verdef={})


def provider(version=2,name=b'foo',vername=b'LIB_1',hidden=False):
    return dict(symbols=[record(b'',False,0),record(name,True)],referenced_indices=set(),
                versym=[0,version|(0x8000 if hidden else 0)],verdef={2:vername} if version>1 else {},verneed={})


def fixture(needed=False,versionname=b'LIB_1',wrong_count=False,bad_versym_length=False):
    buf=bytearray(0xa00)
    original=parent_tests.fixture(sym_index=2,sym_name=b'foo')
    buf[:len(original)]=original
    # Extend PT_LOAD; place version tables in its file-backed area.
    struct.pack_into('<II',buf,52+16,0xa00,0xa00)
    struct.pack_into('<I',buf,32,0x800)
    struct.pack_into('<HHH',buf,46,40,5,0)
    # Rebuild PT_DYNAMIC, including version structures.
    tags=[(5,0x1200),(6,0x1300),(10,0x90),(11,16),(17,0x1400),(18,8),(19,8),
          (m.DT_VERSYM,0x1500)]
    if needed:
        tags.extend([(m.DT_VERNEED,0x1580),(m.DT_VERNEEDNUM,2 if wrong_count else 1)])
    else:
        tags.extend([(m.DT_VERDEF,0x1540),(m.DT_VERDEFNUM,2 if wrong_count else 1)])
    tags.append((0,0))
    struct.pack_into('<II',buf,84+16,len(tags)*8,len(tags)*8)
    for i,(tag,val) in enumerate(tags):struct.pack_into('<II',buf,0x100+i*8,tag,val)
    # String table offsets: 0=''; 1=foo; 5=foo, append version at 9.
    nameoff=9
    buf[0x200+nameoff:0x200+nameoff+len(versionname)+1]=versionname+b'\0'
    liboff=0x20
    buf[0x200+liboff:0x200+liboff+7]=b'lib.so\0'
    struct.pack_into('<HHHH',buf,0x500,0,1,2,2)
    if needed:
        struct.pack_into('<HHIII',buf,0x580,1,1,liboff,16,0)
        struct.pack_into('<IHHII',buf,0x590,0x1234,0,2,nameoff,0)
    else:
        struct.pack_into('<HHHHIII',buf,0x540,1,0,2,1,0,20,0)
        struct.pack_into('<II',buf,0x554,nameoff,0)
    for i,entry in enumerate([
        (0,0,0,0,0,0,0,0,0,0),
        (0,11,0,0x1300,0x300,64,2,0,4,16),
        (0,3,0,0x1200,0x200,0x90,0,0,1,0),
        (0,m.SHT_VERSYM,0,0x1500,0x500,6 if bad_versym_length else 8,1,0,2,2),
        (0,m.SHT_VERNEED if needed else m.SHT_VERDEF,0,0x1580 if needed else 0x1540,
         0x580 if needed else 0x540,32 if needed else 28,2,1,4,0)]):
        struct.pack_into('<IIIIIIIIII',buf,0x800+i*40,*entry)
    return bytes(buf)


class TestVersionRecordParsers(unittest.TestCase):
    def test_parent_sha(self):self.assertTrue(callable(m.load_parent(HERE).audit))
    def test_wrong_parent(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/m.PARENT).write_text('bad')
            with self.assertRaises(m.Hold):m.load_parent(Path(d))
    def test_read_u16(self):self.assertEqual(m.u16(b'\x02\x00',0,'<'),2)
    def test_u32_bounded(self):
        with self.assertRaises(m.Hold):m.u32(b'123',0,'<')
    def test_verdef_valid(self):
        d=bytearray(28);struct.pack_into('<HHHHIII',d,0,1,0,2,1,0,20,0)
        struct.pack_into('<II',d,20,1,0)
        self.assertEqual(m.parse_verdef(d,b'\0V\0',1,'<',p40),{2:b'V'})
    def test_verdef_truncated(self):
        with self.assertRaises(m.Hold):m.parse_verdef(b'abc',b'\0v\0',1,'<',p40)
    def test_verdef_bad_aux(self):
        d=bytearray(28);struct.pack_into('<HHHHIII',d,0,1,0,2,1,0,200,0)
        with self.assertRaises(m.Hold):m.parse_verdef(d,b'\0V\0',1,'<',p40)
    def test_verdef_more_than_count(self):
        with self.assertRaises(m.Hold):m.parse_verdef(bytes(28),b'\0',4097,'<',p40)
    def test_verneed_valid(self):
        d=bytearray(32);struct.pack_into('<HHIII',d,0,1,1,1,16,0)
        struct.pack_into('<IHHII',d,16,0,0,2,5,0)
        self.assertEqual(m.parse_verneed(d,b'\0lib\0VER\0',1,'<',p40)[2]['version'],b'VER')
    def test_verneed_bad_index(self):
        d=bytearray(32);struct.pack_into('<HHIII',d,0,1,1,1,16,0)
        struct.pack_into('<IHHII',d,16,0,0,1,5,0)
        with self.assertRaises(m.Hold):m.parse_verneed(d,b'\0lib\0VER\0',1,'<',p40)
    def test_verneed_truncated(self):
        with self.assertRaises(m.Hold):m.parse_verneed(b'\0'*18,b'\0lib\0',1,'<',p40)
    def test_verneed_duplicate_index(self):
        d=bytearray(48);struct.pack_into('<HHIII',d,0,1,2,1,16,0)
        struct.pack_into('<IHHII',d,16,0,0,2,5,16)
        struct.pack_into('<IHHII',d,32,0,0,2,5,0)
        with self.assertRaises(m.Hold):m.parse_verneed(d,b'\0lib\0VER\0',1,'<',p40)


class TestCandidateVersionSemantics(unittest.TestCase):
    def classified(self,src=None,provs=None):
        return m.classify_version_candidates([src or source()],provs if provs is not None else [provider()])
    def test_exact_named_version(self):self.assertEqual(self.classified()['version_filtered_static_candidate_categories'],{'ONE_GNU_VERSION_NAME_MATCHING_CANDIDATE':1})
    def test_wrong_named_version(self):self.assertEqual(self.classified(provs=[provider(vername=b'WRONG')])['version_filtered_static_candidate_categories'],{'NAME_CANDIDATE_BUT_NO_EQUAL_GNU_VERSION_NAME':1})
    def test_no_name_candidate(self):self.assertEqual(self.classified(provs=[provider(name=b'other')])['version_filtered_static_candidate_categories'],{'NO_STAGED_PROVIDER_NAME_CANDIDATE':1})
    def test_multiple_exact_named_version(self):self.assertEqual(self.classified(provs=[provider(),provider()])['version_filtered_static_candidate_categories'],{'MULTIPLE_GNU_VERSION_NAME_MATCHING_CANDIDATES':1})
    def test_unversioned_global_provider(self):self.assertEqual(self.classified(src=source(version=1),provs=[provider(version=1)])['version_filtered_static_candidate_categories'],{'ONE_DEFAULT_OR_UNVERSIONED_NAME_CANDIDATE':1})
    def test_unversioned_default_versioned_provider(self):self.assertEqual(self.classified(src=source(version=1))['version_filtered_static_candidate_categories'],{'ONE_DEFAULT_OR_UNVERSIONED_NAME_CANDIDATE':1})
    def test_unversioned_nondflt_versioned_provider(self):self.assertEqual(self.classified(src=source(version=1),provs=[provider(hidden=True)])['version_filtered_static_candidate_categories'],{'ONLY_NONDEFAULT_VERSIONED_NAME_CANDIDATES':1})
    def test_unknown_requirement_holds(self):
        with self.assertRaises(m.Hold):self.classified(src=source(version=3))
    def test_version_zero_holds(self):
        with self.assertRaises(m.Hold):self.classified(src=source(version=0))
    def test_missing_provider_definition_holds(self):
        p=provider();p['verdef']={}
        with self.assertRaises(m.Hold):self.classified(provs=[p])
    def test_private_names_not_exported(self):
        o=self.classified(src=source(name=b'sensitive'),provs=[provider(name=b'sensitive')])
        self.assertNotIn('sensitive',str(o))
        self.assertNotIn('LIB_1',str(o))


class TestRealisticELF(unittest.TestCase):
    def parse(self,**kw):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'sample.elf';p.write_bytes(fixture(**kw))
            return m.parse_version_file(parent_tests.p26,p40,p)
    def test_provider_version_record_filebacked(self):
        o=self.parse();self.assertEqual(o['verdef'][2],b'LIB_1');self.assertEqual(o['versym'][2],2)
    def test_request_verneed_filebacked(self):
        o=self.parse(needed=True);self.assertEqual(o['verneed'][2]['version'],b'LIB_1')
    def test_bad_section_size_holds(self):
        with self.assertRaises(m.Hold):self.parse(bad_versym_length=True)
    def test_bad_record_count_holds(self):
        with self.assertRaises(m.Hold):self.parse(wrong_count=True)

if __name__=='__main__':unittest.main()
