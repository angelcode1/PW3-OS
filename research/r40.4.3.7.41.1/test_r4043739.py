"""R4043739 offline synthetic tests. Never writes a real stage or runs a loader."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

HERE=Path(__file__).parent

def module(name, filename):
    sp=importlib.util.spec_from_file_location(name,HERE/filename)
    m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m

m=module('r3739','R4043739-NEEDED-TRANSITIVE-SONAME-READONLY.py')
t38=module('r3738_tests','test_r4043738.py')
parent=m.load_parent(HERE)
p26=t38.P26


def elf32(*,needed=(),soname=None,source=False,bad_soname_offset=False,missing_strtab=False):
    raw=bytearray(1024)
    raw[:7]=b'\x7fELF\x01\x01\x01'
    struct.pack_into('<HHI',raw,16,3,40,1)
    struct.pack_into('<I',raw,28,52)
    struct.pack_into('<HHH',raw,40,52,32,2)
    struct.pack_into('<IIIIIIII',raw,52,1,0,0,0,1024,1024,5,4096)
    names=b'\0';offsets=[]
    for x in needed:
        offsets.append(len(names));names+=x+b'\0'
    so_offset=None
    if soname is not None:
        so_offset=len(names);names+=soname+b'\0'
    tags=[(1,x) for x in offsets]
    if soname is not None:
        tags.append((14,9999 if bad_soname_offset else so_offset))
    if not missing_strtab:tags.extend([(5,640),(10,len(names))])
    tags.append((0,0))
    for i,(k,v) in enumerate(tags):struct.pack_into('<II',raw,128+8*i,k,v)
    struct.pack_into('<IIIIIIII',raw,84,2,128,128,0,len(tags)*8,len(tags)*8,6,4)
    raw[640:640+len(names)]=names
    if source:raw[960:966]=b'SOURCE'
    return bytes(raw)

class TestPins(unittest.TestCase):
    def test_parent_pin(self):self.assertEqual(m.load_parent(HERE).PARENT_NAME, 'R4043737-ARM-RELOCATION-SYMBOL-READONLY.py')
    def test_bad_parent_hash(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/m.PARENT).write_text('no')
            with self.assertRaises(m.Hold) as e:m.load_parent(Path(t))
            self.assertEqual(e.exception.code,'PARENT_SOURCE_SHA256_HOLD')
    def test_no_parent(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(m.Hold):m.load_parent(Path(t))
    def test_parent_symlink_refused(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'ordinary').write_text('no');(p/m.PARENT).symlink_to('ordinary')
            with self.assertRaises(m.Hold):m.load_parent(p)

class TestSoname(unittest.TestCase):
    def read(self, **opts):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'test.so';p.write_bytes(elf32(**opts))
            return m.read_soname(p26,p)
    def test_soname_equal(self):self.assertEqual(self.read(soname=b'libtest.so'),b'libtest.so')
    def test_soname_with_needed(self):self.assertEqual(self.read(needed=[b'libc.so'],soname=b'libtest.so'),b'libtest.so')
    def test_no_soname(self):self.assertIsNone(self.read(needed=[b'libother.so']))
    def test_bad_soname_offset(self):
        with self.assertRaises(m.Hold) as e:self.read(soname=b'lib.so',bad_soname_offset=True)
        self.assertEqual(e.exception.code,'PROVIDER_SONAME_OFFSET_HOLD')
    def test_missing_strtab(self):
        with self.assertRaises(m.Hold) as e:self.read(soname=b'lib.so',missing_strtab=True)
        self.assertEqual(e.exception.code,'PROVIDER_SONAME_DESCRIPTOR_HOLD')
    def test_not_elf(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'bad';p.write_text('not an elf')
            with self.assertRaises(m.Hold):m.read_soname(p26,p)

class TestProviders(unittest.TestCase):
    def test_one_candidate(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'libx.so';p.write_bytes(elf32())
            self.assertEqual(m.providers_for_needed(root,{b'libx.so':[(p,'regular')]},b'libx.so',{},p26)[0],'ONE_REGULAR_HEADER_CANDIDATE')
    def test_missing_candidate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(m.providers_for_needed(Path(t),{},b'gone.so',{},p26)[0],'NO_BASENAME_PROVIDER_IN_STAGE')
    def test_path_bearing_name(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(m.providers_for_needed(Path(t),{},b'/lib/libx.so',{},p26)[0],'NAME_PATH_COMPONENT_REVIEW')
    def test_multiple_candidates(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'a').mkdir();(root/'b').mkdir()
            files=[root/x/'libx.so' for x in ('a','b')]
            for f in files:f.write_bytes(elf32())
            self.assertEqual(m.providers_for_needed(root,{b'libx.so':[(f,'regular') for f in files]},b'libx.so',{},p26)[0],'MULTIPLE_HEADER_CANDIDATES')
    def test_no_matching_elf(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'test.so';p.write_text('bad')
            self.assertEqual(m.providers_for_needed(root,{b'test.so':[(p,'regular')]},b'test.so',{},p26)[0],'BASENAME_PRESENT_NO_COMPATIBLE_PROVIDER')

class TestCycles(unittest.TestCase):
    def test_cycle_and_self_loop(self):
        g={'a':{'b'},'b':{'a'},'c':{'c'},'d':set()}
        self.assertEqual(m.cycle_stats(g),{'cyclic_strong_components':2,'nodes_in_cycles':3,'largest_cyclic_component_size':2})
    def test_acyclic(self):
        self.assertEqual(m.cycle_stats({'a':{'b'},'b':set()})['cyclic_strong_components'],0)

class TestSyntheticFullStage(unittest.TestCase):
    def test_12_sources_19_needed_6_providers_and_cycles(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'bin').mkdir();(root/'lib').mkdir()
            libs=[b'liba.so',b'libb.so',b'libc.so',b'libd.so',b'libe.so',b'libf.so']
            needed_graph={libs[0]:[libs[1]],libs[1]:[libs[0]],libs[2]:[b'gone.so'],libs[3]:[libs[3]],libs[4]:[],libs[5]:[libs[0]]}
            for name in libs:
                (root/'lib'/name.decode()).write_bytes(elf32(needed=needed_graph[name],soname=name))
            # 7*1 + 4*2 + 1*4 = 19 entries; all six distinct names referenced.
            requests=[[libs[i%6]] for i in range(7)]+[[libs[i%6],libs[(i+1)%6]] for i in range(4)]+[[libs[0],libs[1],libs[2],libs[3]]]
            self.assertEqual(sum(map(len,requests)),19)
            for i,names in enumerate(requests):
                (root/'bin'/f'req-{i:02d}').write_bytes(elf32(needed=names,source=True))
            for i in range(65):(root/'bin'/f'plain-{i:02d}').write_bytes(elf32())
            for i in range(1363):(root/f'data-{i:04d}').write_bytes(b'x')
            for i in range(335):(root/f'link-{i:03d}').symlink_to('missing')
            index,sources,nfiles,nlinks=t38.Fake27().inventory(root,p26)
            result=m.graph_audit(root,HERE,parent,require_baseline=False,
              overrides=(p26,t38.Fake27(),index,sources,nfiles,nlinks))
            self.assertEqual(result['result'],'STATIC_SONAME_AND_TRANSITIVE_BASENAME_GRAPH_CLASSIFIED_ONLY')
            self.assertEqual(result['source_elf_count'],12)
            self.assertEqual(result['direct_needed_edges'],19)
            self.assertEqual(result['distinct_direct_needed_literals'],6)
            self.assertEqual(result['unique_initial_provider_regular_files'],6)
            self.assertEqual(result['provider_soname_categories'],{'SONAME_EQUALS_REFERENCED_NEEDED_NAME':6})
            self.assertEqual(result['provider_needed_basename_candidate_categories'],{
                'ONE_REGULAR_HEADER_CANDIDATE':4,'NO_BASENAME_PROVIDER_IN_STAGE':1})
            self.assertEqual(result['provider_graph_cycles']['cyclic_strong_components'],2)
            self.assertEqual(result['provider_graph_cycles']['nodes_in_cycles'],3)
            self.assertFalse(result['full_dependency_closure_proven'])
            self.assertFalse(result['actual_dynamic_library_search_paths_verified'])
            self.assertFalse(result['boot_authorized'])
            self.assertFalse(result['stage_modified'])
            s=json.dumps(result)
            for name in libs:self.assertNotIn(name.decode(),s)
            self.assertNotIn('gone.so',s)

if __name__=='__main__':unittest.main()
