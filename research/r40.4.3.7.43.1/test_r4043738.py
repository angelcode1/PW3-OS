"""R3738 synthetic host-only tests; never operate on real stage or hardware."""
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

ROOT=Path(__file__).parent
SPEC=importlib.util.spec_from_file_location('r3738_test',ROOT/'R4043738-NEEDED-LIBRARY-CANDIDATES-READONLY.py')
m=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(m)


def elf32(*, needed=(), source=False, missing_strtab=False,
          bad_string_offset=False, bad_strtab_mapping=False, unterminated=False,
          no_dynamic=False):
    raw=bytearray(1024)
    raw[:7]=b'\x7fELF\x01\x01\x01'
    struct.pack_into('<HHI',raw,16,3,40,1)
    struct.pack_into('<I',raw,28,52)
    struct.pack_into('<HHH',raw,40,52,32,2 if not no_dynamic else 1)
    struct.pack_into('<IIIIIIII',raw,52,1,0,0,0,1024,1024,5,4096)
    if not no_dynamic:
        names=b'\x00';offsets=[]
        for name in needed:
            offsets.append(len(names))
            names+=name + b'\x00'
        if unterminated and needed:names=names[:-1]
        tags=[(1,(1023 if bad_string_offset else off)) for off in offsets]
        if not missing_strtab:
            tags += [(5,1200 if bad_strtab_mapping else 640),(10,len(names))]
        tags.append((0,0))
        for i,(key,val) in enumerate(tags):struct.pack_into('<II',raw,128+8*i,key,val)
        struct.pack_into('<IIIIIIII',raw,84,2,128,128,0,len(tags)*8,len(tags)*8,6,4)
        raw[640:640+len(names)]=names
    if source:raw[960:966]=b'SOURCE'
    return bytes(raw)

class Fake26:
    class Hold(Exception):pass
    def elf_header(self,f):
        f.seek(0,2); length=f.tell();f.seek(0)
        if not f.read(4)==b'\x7fELF':return None
        return {'cls':1,'machine':40,'type':3,'phoff':52,'phnum':2,'phsize':32,
                'endian':'<','length':length}
    def read_at(self,f,off,length):
        if off<0 or length<0:raise self.Hold('negative')
        f.seek(off); b=f.read(length)
        if len(b)!=length:raise self.Hold('short')
        return b
    def open_regular_nofollow(self,path):return open(path,'rb')
    def inspect_elf(self,f):
        h=self.elf_header(f)
        if h is None:return None
        f.seek(960)
        return h, [('/lib/ld-demo.so',False)] if f.read(6)==b'SOURCE' else []
    def classify_guest_target(self,root,guest,hdr):
        path=root/guest.lstrip('/')
        if path.exists() and path.is_file() and path.read_bytes()[:4]==b'\x7fELF':
            return 'GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE',0
        return 'GUEST_ABSENT_HOLD',0

P26=Fake26()

class Fake27:
    class Hold(Exception):pass
    def inventory(self,root,p26):
        names={}; sources=[];reg=0;link=0
        for path in root.rglob('*'):
            if path.is_symlink():
                names.setdefault(path.name,[]).append((path,'link'));link+=1
            elif path.is_file():
                names.setdefault(path.name,[]).append((path,'regular'));reg+=1
                with open(path,'rb') as f:
                    item=p26.inspect_elf(f)
                if item is not None:
                    sources.extend([(x,item[0]) for x,_ in item[1]])
        return names,sources,reg,link

class Fake33:
    R3726='p26';R3727='p27'
    def import_parent(self,path,name):return P26 if name=='p26' else Fake27()
class Fake34:
    def import_r33(self,folder):return Fake33()
class Fake35:
    def import_parent(self,folder):return Fake34()
class Fake36:
    def import_parent(self,folder):return Fake35()
class Fake37:
    class Hold(Exception):pass
    def import_parent(self,folder):return Fake36()
    def audit(self,root,folder,p36):
        return {'result':'ARM_RELOCATION_TYPES_AND_SYMBOL_INDICES_STATIC_CLASSIFIED_ONLY',
                'requesting_elf_count':12,
                'requesting_elf_categories':m.EXPECTED_SOURCE_CATEGORY.copy(),
                'requesting_arm_relocation_type_counts':m.EXPECTED_TYPES.copy(),
                'candidate':{'arm_relocation_type_counts':{'21':4,'22':6,'23':17},'dt_needed_count':0},
                'requesting_symbol_index_and_dynsym_counts':{'dynsym_undefined':632},
                'stage_modified':False}

class TestNeededDecoder(unittest.TestCase):
    def scan(self,**kw):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source'
            path.write_bytes(elf32(**kw))
            return m.elf_needed_literals(P26,path)[0]
    def test_two_needed_strings(self):
        self.assertEqual(self.scan(needed=[b'libx.so',b'liby.so']),[b'libx.so',b'liby.so'])
    def test_zero_needed(self):self.assertEqual(self.scan(),[])
    def test_no_dynamic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'no-dyn';path.write_bytes(elf32(no_dynamic=True))
            self.assertEqual(m.elf_needed_literals(P26,path)[0],[])
    def test_missing_string_table_holds(self):
        with self.assertRaises(m.Hold) as c:self.scan(needed=[b'libx.so'],missing_strtab=True)
        self.assertEqual(c.exception.code,'SOURCE_DYNAMIC_STRTAB_DESCRIPTORS_HOLD')
    def test_out_of_bounds_needed_offset(self):
        with self.assertRaises(m.Hold) as c:self.scan(needed=[b'libx.so'],bad_string_offset=True)
        self.assertEqual(c.exception.code,'NEEDED_STRING_OFFSET_HOLD')
    def test_unmapped_dynamic_strings(self):
        with self.assertRaises(m.Hold) as c:self.scan(needed=[b'libx.so'],bad_strtab_mapping=True)
        self.assertEqual(c.exception.code,'SOURCE_DYNAMIC_STRTAB_MAPPING_HOLD')
    def test_unterminated_string(self):
        with self.assertRaises(m.Hold) as c:self.scan(needed=[b'libx.so'],unterminated=True)
        self.assertEqual(c.exception.code,'NEEDED_STRING_NOT_TERMINATED_HOLD')
    def test_library_names_not_in_published_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);(r/'libfun.so').write_bytes(elf32())
            index={b'libfun.so':[(r/'libfun.so','regular')]}
            x=m.category_for_needed(r,index,b'libfun.so',{},P26)
            self.assertEqual(x[0],'ONE_REGULAR_ABI_HEADER_BASENAME_CANDIDATE')
            self.assertNotIn('libfun.so',str(x))
    def test_path_bearing_name_is_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(m.category_for_needed(Path(tmp),{},b'/usr/lib/libx.so',{},P26)[0],
                             'PATH_BEARING_NEEDED_LITERAL_REVIEW_HOLD')
    def test_no_basename(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(m.category_for_needed(Path(tmp),{},b'libnone.so',{},P26)[0],
                             'NO_BASENAME_ENTRY_IN_STAGE')
    def test_incompatible_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp); (r/'libx.so').write_bytes(b'NOT AN ELF')
            self.assertEqual(m.category_for_needed(r,{b'libx.so':[(r/'libx.so','regular')]},b'libx.so',{},P26)[0],
                             'BASENAME_ENTRIES_BUT_NO_ABI_HEADER_CANDIDATE')
    def test_multiple_compatible_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp)
            for d in ('a','b'):
                (r/d).mkdir(); (r/d/'libx.so').write_bytes(elf32())
            index={b'libx.so':[(r/d/'libx.so','regular') for d in ('a','b')]}
            self.assertEqual(m.category_for_needed(r,index,b'libx.so',{},P26)[0],
                             'MULTIPLE_ABI_HEADER_BASENAME_CANDIDATES')
    def test_refuses_modified_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/m.PARENT_NAME).write_text('modified')
            with self.assertRaises(m.Hold) as c:m.load_parent(Path(tmp))
            self.assertEqual(c.exception.code,'PARENT_SOURCE_SHA256_HOLD')
    def test_exact_pinned_parent_import(self):
        self.assertTrue(hasattr(m.load_parent(ROOT),'audit'))

class TestFullSyntheticStage(unittest.TestCase):
    def test_mock_replay_83_elf_19_needed_335_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp)
            (r/'lib').mkdir();(r/'bin').mkdir()
            (r/'lib/libgood.so').write_bytes(elf32())
            for i in range(12):
                needed=[b'libgood.so',b'libgone.so'] if i<7 else [b'libgood.so']
                (r/'bin'/('req-%02d'%i)).write_bytes(elf32(needed=needed,source=True))
            for i in range(70): (r/'bin'/('plain-%02d'%i)).write_bytes(elf32())
            for i in range(1363): (r/('ordinary-%04d'%i)).write_bytes(b'\x00')
            for i in range(335): (r/('link-%03d'%i)).symlink_to('absent')
            result=m.audit(r,ROOT,Fake37())
            self.assertEqual(result['result'],'REQUESTER_NEEDED_BASENAME_STATIC_CANDIDATES_ONLY')
            self.assertEqual(result['source_elf_count'],12)
            self.assertEqual(result['dt_needed_entries'],19)
            self.assertEqual(result['distinct_dt_needed_name_literals'],2)
            self.assertEqual(result['dt_needed_same_basename_candidate_categories'],{
                'ONE_REGULAR_ABI_HEADER_BASENAME_CANDIDATE':12,
                'NO_BASENAME_ENTRY_IN_STAGE':7})
            self.assertEqual(result['per_source_dt_needed_entry_count_histogram'],{'1':5,'2':7})
            self.assertFalse(result['stage_modified'])
            self.assertFalse(result['needed_library_runtime_resolution_verified'])
            self.assertFalse(result['boot_authorized'])
            self.assertNotIn('libgood',json.dumps(result))
            self.assertNotIn('libgone',json.dumps(result))
    def test_parent_counts_refusal(self):
        class Changed(Fake37):
            def audit(self,root,folder,p36):
                x=super().audit(root,folder,p36);x['requesting_elf_count']=11;return x
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(m.Hold) as c:m.audit(Path(tmp),ROOT,Changed())
            self.assertEqual(c.exception.code,'R3737_COUNTS_AND_TYPES_REPLAY_HOLD')

if __name__=='__main__':unittest.main()
