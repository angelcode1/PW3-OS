"""R3740 synthetic read-only regression tests; never use real PW3 stage."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
SCRIPT=HERE/'R4043740-SYMBOL-NAME-VERSION-READONLY.py'
spec=importlib.util.spec_from_file_location('r3740_unit',SCRIPT)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
p39=m.import_parent(HERE)
p38=p39.load_parent(HERE)
p37=p38.load_parent(HERE)
p36=p37.import_parent(HERE)
p35=p36.import_parent(HERE)
p34=p35.import_parent(HERE)
p33=p34.import_r33(HERE)
p26=p33.import_parent(HERE/p33.R3726,p33.R3726)


def fixture(*,version=False,sym_index=2,sym_name=b'bar',dynsym_addr_delta=0, bad_section_link=False,
            missing_cstr=False, bad_reloc=False, reloc_type=22):
    buf=bytearray(0x700)
    buf[:7]=b'\x7fELF\x01\x01\x01'
    struct.pack_into('<HHI',buf,16,3,40,1)
    struct.pack_into('<I',buf,28,52)
    struct.pack_into('<I',buf,32,0x600)
    struct.pack_into('<HHH',buf,40,52,32,2)
    struct.pack_into('<HHH',buf,46,40,3,0)
    # PT_LOAD covers all bytes; PT_DYNAMIC lies entirely inside.
    struct.pack_into('<IIIIIIII',buf,52,1,0,0x1000,0,0x700,0x700,5,0x1000)
    tags=[(5,0x1200),(6,0x1300+dynsym_addr_delta),(10,0x90),(11,16),
          (17,0x1400),(18,8),(19,8)]
    if version:tags.append((0x6ffffff0,0x1500))
    tags.append((0,0))
    struct.pack_into('<IIIIIIII',buf,84,2,0x100,0x1100,0,len(tags)*8,len(tags)*8,4,4)
    for i,(tag,val) in enumerate(tags):struct.pack_into('<II',buf,0x100+8*i,tag,val)
    names=b'\x00foo\x00'+sym_name+b'\x00'
    buf[0x200:0x200+len(names)]=names
    if missing_cstr:
        buf[0x200:0x290]=b'x'*0x90
    # 4 symbols: undef 0, defined foo 1, undefined bar 2, weak undefined bar 3
    struct.pack_into('<IIIBBH',buf,0x300+16*1,1,0,0,0x12,0,1)
    struct.pack_into('<IIIBBH',buf,0x300+16*2,5,0,0,0x12,0,0)
    struct.pack_into('<IIIBBH',buf,0x300+16*3,5,0,0,0x22,0,0)
    struct.pack_into('<II',buf,0x400,0x1500,(sym_index<<8)|reloc_type)
    if bad_reloc:
        struct.pack_into('<I',buf,0x400+4,(100<<8)|22)
    # Section 1 is SHT_DYNSYM, linked with section 2 SHT_STRTAB.
    struct.pack_into('<IIIIIIIIII',buf,0x600+40,0,11,0,0x1300,0x300,64,
                     99 if bad_section_link else 2,0,4,16)
    struct.pack_into('<IIIIIIIIII',buf,0x600+80,0,3,0,0x1200,0x200,0x90,0,0,1,0)
    return bytes(buf)


class TestHelpers(unittest.TestCase):
    def test_parent_pin(self):self.assertTrue(callable(m.import_parent(HERE).graph_audit))
    def test_parent_wrong_sha(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/m.PARENT).write_text('tampered')
            with self.assertRaises(m.Hold):m.import_parent(Path(d))
    def test_checked_cstr(self):self.assertEqual(m.checked_cstr(b'\0foo\0',1),b'foo')
    def test_cstr_bad_offset(self):
        with self.assertRaises(m.Hold):m.checked_cstr(b'foo\0',8)
    def test_cstr_unterminated(self):
        with self.assertRaises(m.Hold):m.checked_cstr(b'foo',0)
    def test_map_success(self):self.assertEqual(m.map_filebacked([(0x1000,0,0x500)],0x1100,16),0x100)
    def test_map_unbacked(self):
        with self.assertRaises(m.Hold):m.map_filebacked([(0x1000,0,0x200)],0x1300,8)
    def test_map_overflow(self):
        with self.assertRaises(m.Hold):m.map_filebacked([(0x1000,0,0x200)],0xffffffff,8)


class TestElfDynsym(unittest.TestCase):
    def load(self, **kw):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'sample.elf';p.write_bytes(fixture(**kw))
            return m.parse_dynamic_and_sections(p26,p)
    def test_elf_valid(self):
        a=self.load()
        self.assertEqual(len(a['symbols']),4)
        self.assertEqual(a['referenced_indices'],{2})
        self.assertEqual(a['symbols'][2]['name'],b'bar')
        self.assertFalse(a['symbols'][2]['defined'])
        self.assertEqual(a['relocation_entries'],1)
    def test_elf_version_metadata(self):self.assertTrue(self.load(version=True)['metadata'][0x6ffffff0])
    def test_no_version_metadata(self):self.assertFalse(self.load()['metadata'][0x6ffffff0])
    def test_reloc_index_out_of_dynsym(self):
        with self.assertRaises(m.Hold):self.load(bad_reloc=True)
    def test_mismatched_symtab_runtime_address(self):
        with self.assertRaises(m.Hold):self.load(dynsym_addr_delta=1)
    def test_invalid_section_link(self):
        with self.assertRaises(m.Hold):self.load(bad_section_link=True)
    def test_missing_symbol_terminator(self):
        with self.assertRaises(m.Hold):self.load(missing_cstr=True)
    def test_reloc_index_zero_not_reference(self):self.assertEqual(self.load(sym_index=0)['referenced_indices'],set())


class TestCandidateNameSemantics(unittest.TestCase):
    def src(self, *,name=b'foo',defined=False):
        return {'symbols':[{'name':b'','defined':False,'binding':0,'visibility':0},
                           {'name':name,'defined':defined,'binding':1,'visibility':0}],
                'referenced_indices':{1},'metadata':{0x6ffffff0:False,0x6ffffffe:False}}
    def provider(self, *,name=b'foo',binding=1,visibility=0):
        return {'symbols':[{'name':name,'defined':True,'binding':binding,'visibility':visibility}]}
    def test_one_matching_provider(self):
        out=m.classify_candidate_names([self.src()],[self.provider()])
        self.assertEqual(out['undefined_symbol_candidate_categories'],{'ONE_STAGED_PROVIDER_NAME_CANDIDATE':1})
    def test_no_matching_provider(self):
        out=m.classify_candidate_names([self.src()],[self.provider(name=b'other')])
        self.assertEqual(out['undefined_symbol_candidate_categories'],{'NO_STAGED_PROVIDER_NAME_CANDIDATE':1})
    def test_multiple_matches(self):
        out=m.classify_candidate_names([self.src()],[self.provider(),self.provider()])
        self.assertEqual(out['undefined_symbol_candidate_categories'],{'MULTIPLE_STAGED_PROVIDER_NAME_CANDIDATES':1})
    def test_hidden_not_provider(self):
        out=m.classify_candidate_names([self.src()],[self.provider(visibility=2)])
        self.assertEqual(out['undefined_symbol_candidate_categories'],{'NO_STAGED_PROVIDER_NAME_CANDIDATE':1})
    def test_local_not_provider(self):
        out=m.classify_candidate_names([self.src()],[self.provider(binding=0)])
        self.assertEqual(out['undefined_symbol_candidate_categories'],{'NO_STAGED_PROVIDER_NAME_CANDIDATE':1})
    def test_defined_not_undefined(self):
        out=m.classify_candidate_names([self.src(defined=True)],[self.provider()])
        self.assertEqual(out['referenced_undefined_dynsym_entries'],0)
        self.assertEqual(out['referenced_defined_or_special_dynsym_entries'],1)
    def test_no_export_of_names(self):
        out=m.classify_candidate_names([self.src(name=b'private_symbol')],[self.provider(name=b'private_symbol')])
        self.assertNotIn('private_symbol',str(out))

if __name__=='__main__':unittest.main()
