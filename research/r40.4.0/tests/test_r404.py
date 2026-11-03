import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(HERE))
from r404.elf_static import parse_elf, lua_literals, ELFHold
from r404 import static_graph as g


def fake_elf32(*,endian='<',machine=40,flags=0x400,soname='libsrc.so',needed='libfoo.so',interp='/lib/ld-linux.so.3'):
    data=bytearray(0x500)
    data[:16]=b'\x7fELF'+bytes([1,1 if endian=='<' else 2,1,0])+bytes(9)
    h=(3,machine,1,0,52,0,flags,52,32,3,0,0,0)
    struct.pack_into(endian+'HHIIIIIHHHHHH',data,16,*h)
    strings=(needed+'\0'+soname+'\0/usr/lib\0').encode()
    off_s=len(needed)+1
    off_r=off_s+len(soname)+1
    struct.pack_into(endian+'IIIIIIII',data,52,1,0x200,0x5000,0,0x180,0x180,4,0x100)
    struct.pack_into(endian+'IIIIIIII',data,84,2,0x160,0,0,6*8,6*8,4,4)
    struct.pack_into(endian+'IIIIIIII',data,116,3,0x390,0,0,len(interp)+1,len(interp)+1,4,1)
    for index,(tag,val) in enumerate([(5,0x5040),(10,len(strings)),(1,0),(14,off_s),(15,off_r),(0,0)]):
        struct.pack_into(endian+'iI',data,0x160+index*8,tag,val)
    data[0x240:0x240+len(strings)]=strings
    data[0x390:0x390+len(interp)+1]=interp.encode()+b'\0'
    return bytes(data)


def fake_elf64():
    blob=bytearray(0x600)
    blob[:16]=b'\x7fELF'+bytes([2,1,1,0])+bytes(9)
    struct.pack_into('<HHIQQQIHHHHHH',blob,16,3,183,1,0,64,0,0,64,56,2,0,0,0)
    struct.pack_into('<IIQQQQQQ',blob,64,1,4,0x300,0x6000,0,0x100,0x100,0x100)
    struct.pack_into('<IIQQQQQQ',blob,120,2,4,0x210,0,0,4*16,4*16,8)
    strings=b'libbar.so\0liborigin.so\0'
    blob[0x330:0x330+len(strings)]=strings
    for i,(t,v) in enumerate(((5,0x6030),(10,len(strings)),(1,0),(0,0))):
        struct.pack_into('<qQ',blob,0x210+i*16,t,v)
    return bytes(blob)


class ELFParser(unittest.TestCase):
    def test_arm32_needed(self):self.assertEqual(parse_elf(fake_elf32())['needed'],['libfoo.so'])
    def test_arm32_soname(self):self.assertEqual(parse_elf(fake_elf32())['soname'],'libsrc.so')
    def test_arm32_interpreter(self):self.assertEqual(parse_elf(fake_elf32())['interpreter'],'/lib/ld-linux.so.3')
    def test_arm32_rpath(self):self.assertEqual(parse_elf(fake_elf32())['rpath'],'/usr/lib')
    def test_arm32_hardfloat(self):self.assertEqual(parse_elf(fake_elf32())['arm_float_abi'],'hard')
    def test_arm32_softfloat(self):self.assertEqual(parse_elf(fake_elf32(flags=0x200))['arm_float_abi'],'soft')
    def test_arm32_unspecified_float(self):self.assertEqual(parse_elf(fake_elf32(flags=0))['arm_float_abi'],'unspecified')
    def test_arm32_big_endian(self):self.assertEqual(parse_elf(fake_elf32(endian='>'))['endianness'],'big')
    def test_arm64(self):self.assertEqual(parse_elf(fake_elf64())['machine'],183)
    def test_arm64_needed(self):self.assertEqual(parse_elf(fake_elf64())['needed'],['libbar.so'])
    def test_elf64_class(self):self.assertEqual(parse_elf(fake_elf64())['elf_class'],64)
    def test_reject_not_elf(self):
        with self.assertRaises(ELFHold):parse_elf(b'NOT_ELF' + bytes(200))
    def test_reject_short(self):
        with self.assertRaises(ELFHold):parse_elf(b'\x7fELF'+bytes(12))
    def test_reject_elf64_short(self):
        with self.assertRaises(ELFHold):parse_elf(fake_elf64()[:52])
    def test_reject_bad_class(self):
        b=bytearray(fake_elf32());b[4]=3
        with self.assertRaises(ELFHold):parse_elf(bytes(b))
    def test_reject_bad_data(self):
        b=bytearray(fake_elf32());b[5]=3
        with self.assertRaises(ELFHold):parse_elf(bytes(b))
    def test_reject_bad_program_header_offset(self):
        b=bytearray(fake_elf32());struct.pack_into('<I',b,28,0x9999)
        with self.assertRaises(ELFHold):parse_elf(bytes(b))
    def test_reject_too_many_program_headers(self):
        b=bytearray(fake_elf32());struct.pack_into('<H',b,44,5000)
        with self.assertRaises(ELFHold):parse_elf(bytes(b))
    def test_reject_unterminated_strtab(self):
        b=bytearray(fake_elf32());b[0x240:0x249]=b'ABCDEFGHI';struct.pack_into('<I',b,0x16c,9)
        with self.assertRaises(ELFHold):parse_elf(bytes(b))
    def test_reject_unmapped_strtab(self):
        b=bytearray(fake_elf32());struct.pack_into('<I',b,0x164,0x99999)
        with self.assertRaises(ELFHold):parse_elf(bytes(b))
    def test_reject_dynamic_missing_null(self):
        b=bytearray(fake_elf32());struct.pack_into('<iI',b,0x160+5*8,1,0)
        with self.assertRaises(ELFHold):parse_elf(bytes(b))
    def test_reject_multiple_dynamic(self):
        b=bytearray(fake_elf32());struct.pack_into('<I',b,116,2)
        with self.assertRaises(ELFHold):parse_elf(bytes(b))
    def test_reject_empty_cstring_offset(self):
        b=bytearray(fake_elf32());struct.pack_into('<I',b,0x160+2*8+4,12345)
        with self.assertRaises(ELFHold):parse_elf(bytes(b))


class LuaRefTest(unittest.TestCase):
    def test_require_with_parens(self):self.assertEqual(lua_literals('require("frontend/ui")')[0]['literal'],'frontend/ui')
    def test_require_without_parens(self):self.assertEqual(lua_literals("local x=require 'foo.bar'")[0]['literal'],'foo.bar')
    def test_dofile(self):self.assertEqual(lua_literals("dofile('setup.lua')")[0]['operation'],'dofile')
    def test_loadfile(self):self.assertEqual(lua_literals('loadfile("script.lua")')[0]['operation'],'loadfile')
    def test_single_line_comments_ignored(self):self.assertEqual(lua_literals('-- require("phantom")\nrequire("real")')[0]['literal'],'real')
    def test_empty_source(self):self.assertEqual(lua_literals(''),[])
    def test_wrong_type(self):
        with self.assertRaises(ValueError):lua_literals(b'require "abc"')
    def test_dynamic_require_is_not_literal(self):self.assertEqual(lua_literals('require(mypath)'),[])
    def test_module_candidate(self):
        x,s=g.lua_candidates('require','foo.bar',{'rootfs/opt/app/frontend/foo/bar.lua'})
        self.assertEqual(len(x),1);self.assertEqual(s,'STATIC_NAME_CANDIDATES_ONLY')
    def test_module_init_candidate(self):
        x,s=g.lua_candidates('require','foo.bar',{'rootfs/app/foo/bar/init.lua'})
        self.assertEqual(len(x),1);self.assertEqual(s,'STATIC_NAME_CANDIDATES_ONLY')
    def test_dofile_candidate(self):
        x,s=g.lua_candidates('dofile','frontend/test.lua',{'rootfs/app/frontend/test.lua'})
        self.assertEqual(len(x),1);self.assertEqual(s,'STATIC_NAME_CANDIDATES_ONLY')
    def test_missing_candidate(self):
        x,s=g.lua_candidates('require','phantom',{'rootfs/app/foo.lua'})
        self.assertEqual(x,[]);self.assertEqual(s,'NO_STAGED_LEXICAL_CANDIDATE_HOLD')
    def test_unsafe_parent(self):self.assertTrue(g.lua_candidates('loadfile','../file.lua',set())[1].endswith('HOLD'))
    def test_unsafe_absolute(self):self.assertTrue(g.lua_candidates('dofile','/etc/secret',set())[1].endswith('HOLD'))
    def test_unsafe_backslash(self):self.assertTrue(g.lua_candidates('require','a\\b',set())[1].endswith('HOLD'))
    def test_unsafe_require_slash(self):self.assertEqual(g.lua_candidates('require','a/b',set())[0],[])


class SafetyAndIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.outer=self.root/'stage';self.stage=self.outer/'rootfs';self.stage.mkdir(parents=True)
        (self.root/'output').mkdir()

    def mk(self,rel,body):
        p=self.outer/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)
        return p

    def test_read_regular(self):
        p=self.mk('rootfs/app/file.lua',b'hello');self.assertEqual(g.read_exact_file(p,5),b'hello')
    def test_read_regular_limit(self):
        p=self.mk('rootfs/app/file.lua',b'hello')
        with self.assertRaises(g.FileTooLarge):g.read_exact_file(p,4)
    def test_read_nofollow_symlink(self):
        p=self.mk('rootfs/app/file.lua',b'hi');(p.parent/'alias').symlink_to(p)
        with self.assertRaises(OSError):g.read_exact_file(p.parent/'alias',100)
    def test_read_directory_rejected(self):
        with self.assertRaises((ValueError,OSError)):g.read_exact_file(self.stage,100)
    def test_refuse_output_inside_stage(self):
        p=self.mk('rootfs/a.json',b'x')
        with self.assertRaises(ValueError):g.refuse_paths(self.stage,[p],[self.stage/'new.json'])
    def test_refuse_existing_output(self):
        p=self.mk('rootfs/a.json',b'x');out=self.root/'output/o.json';out.write_text('x')
        with self.assertRaises(ValueError):g.refuse_paths(self.stage,[self.root/'output/o.json'],[out])
    def test_refuse_same_outputs(self):
        with self.assertRaises(ValueError):g.refuse_paths(self.stage,[],[self.root/'output/x',self.root/'output/x'])
    def test_refuse_symlink_output(self):
        inp=self.root/'outside';inp.write_text('x');out=self.root/'output/sym';out.symlink_to(inp)
        with self.assertRaises(ValueError):g.refuse_paths(self.stage,[inp],[out])
    def test_refuse_symlink_parent(self):
        inp=self.root/'outside';inp.write_text('x');(self.root/'link').symlink_to(self.stage, target_is_directory=True)
        with self.assertRaises(ValueError):g.refuse_paths(self.stage,[inp],[self.root/'link/o.json'])
    def test_source_pin_valid(self):
        p=self.root/'check.json';p.write_bytes((HERE/'tests/fixtures/R40.3-R26-HASH-SUMMARY.json').read_bytes())
        # GitHub versioned vendored R40.3 source and observed report pins.
        g.src_pins(p)
    def test_source_pin_mutated(self):
        p=self.root/'check.json';p.write_text('{}')
        with self.assertRaises(ValueError):g.src_pins(p)
    def test_report_exclusive(self):
        p=self.root/'output/report.json';g.create_report(p,{'safe_to_prune_inferred':False})
        with self.assertRaises(FileExistsError):g.create_report(p,{'unsafe':True})
    def test_static_with_one_candidate(self):
        src=self.mk('rootfs/app/main.so',fake_elf32())
        dep=self.mk('rootfs/usr/lib/libfoo.so',fake_elf32(soname='libfoo.so'))
        lua=self.mk('rootfs/app/main.lua',b'local a=require "something"\n')
        mod=self.mk('rootfs/app/something.lua',b'return {}')
        links=self.outer/'rootfs/usr/lib/alias.so';links.symlink_to(dep.name)
        rr={};r26={}
        for rel,p in [('rootfs/app/main.so',src),('rootfs/usr/lib/libfoo.so',dep),('rootfs/app/main.lua',lua),('rootfs/app/something.lua',mod)]:
            rr[rel]={'type':'regular'};r26[rel]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        rr['rootfs/usr/lib/alias.so']={'type':'symlink'}
        pub,priv=g.inspect_static(self.stage,rr,r26,{'rootfs/app/main.so','rootfs/app/main.lua'},expected_counts=None)
        self.assertEqual(pub['static_elf_objects_parsed'],2)
        self.assertEqual(pub['lua_literal_reference_edges'],1)
        self.assertEqual(pub['elf_dt_needed_edges'],2)
        self.assertEqual(pub['runtime_observed_open_distinct_regular'],2)
        self.assertFalse(pub['safe_to_prune_inferred'])
        self.assertEqual(priv['elf_candidate_edges'][0]['choices'][0]['candidate_path'],'rootfs/usr/lib/libfoo.so')
        self.assertNotIn('rootfs/app/main.so',json.dumps(pub))
    def test_static_count_drift_refused(self):
        p=self.mk('rootfs/app/file.txt',b'not elf')
        rr={'rootfs/app/file.txt':{'type':'regular'}}
        r26={'rootfs/app/file.txt':{'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}}
        with self.assertRaises(ValueError):g.inspect_static(self.stage,rr,r26,set())
    def test_static_rejects_hash_drift(self):
        p=self.mk('rootfs/app/file.lua',b'require "a"')
        with self.assertRaises(ValueError):g.inspect_static(self.stage,{'rootfs/app/file.lua':{'type':'regular'}}, {'rootfs/app/file.lua':{'sha256':'0'*64}},set(),expected_counts=None)
    def test_static_invalid_elf_stays_hold(self):
        p=self.mk('rootfs/app/fault.so',b'\x7fELF'+bytes(52))
        r='rootfs/app/fault.so'
        pub,priv=g.inspect_static(self.stage,{r:{'type':'regular'}},{r:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}},set(),expected_counts=None)
        self.assertEqual(pub['static_elf_parse_or_size_holds'],1)
        self.assertTrue(pub['complete_dependency_closure_proven'] is False)
    def test_static_symlink_never_read(self):
        p=self.mk('rootfs/app/a.lua',b'require "a"');l=self.outer/'rootfs/app/link.lua';l.symlink_to(p)
        r='rootfs/app/a.lua'
        rr={r:{'type':'regular'},'rootfs/app/link.lua':{'type':'symlink'}}
        pub,pr=g.inspect_static(self.stage,rr,{r:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}},{r},expected_counts=None)
        self.assertEqual(pub['lua_files_scanned'],1)
        self.assertTrue(pub['all_unobserved_staged_files_retained'])
    def test_static_library_name_missing_not_proven(self):
        p=self.mk('rootfs/app/main.so',fake_elf32(needed='libghost.so'))
        r='rootfs/app/main.so';record={r:{'type':'regular'}};manifest={r:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}}
        pub,priv=g.inspect_static(self.stage,record,manifest,{r},expected_counts=None)
        self.assertEqual(pub['elf_candidate_status_counts']['NO_STAGE_NAME_CANDIDATE_HOLD'],1)
        self.assertFalse(pub['runtime_edge_resolution_proven'])

    def test_elf_incompatible_static_candidate_marked(self):
        src=self.mk('rootfs/app/main.so',fake_elf32())
        cand=self.mk('rootfs/usr/lib/libfoo.so',fake_elf32(machine=62))
        paths=['rootfs/app/main.so','rootfs/usr/lib/libfoo.so']
        rr={p:{'type':'regular'} for p in paths}
        orig={p:{'sha256':hashlib.sha256((self.outer/p).read_bytes()).hexdigest()} for p in paths}
        pub,priv=g.inspect_static(self.stage,rr,orig,set(paths),expected_counts=None)
        edge=next(e for e in priv['elf_candidate_edges'] if e['source']=='rootfs/app/main.so')
        self.assertFalse(edge['choices'][0]['parsed_elf_abi_compatible'])
        self.assertIn('NOT_RUNTIME_PROVEN',edge['status'])

    def test_interpreter_symlink_remains_hold(self):
        src=self.mk('rootfs/app/main.so',fake_elf32())
        libdir=self.stage/'lib';libdir.mkdir()
        (libdir/'ld-linux.so.3').symlink_to('fake-dynamic-loader')
        p='rootfs/app/main.so'
        rr={p:{'type':'regular'},'rootfs/lib/ld-linux.so.3':{'type':'symlink'}}
        orig={p:{'sha256':hashlib.sha256(src.read_bytes()).hexdigest()}}
        pub,priv=g.inspect_static(self.stage,rr,orig,{p},expected_counts=None)
        self.assertEqual(priv['elf'][p]['interpreter_candidate']['status'],'INTERPRETER_STAGE_SYMLINK_NOT_RUNTIME_PROVEN')

    def test_lua_module_ambiguous_candidates_not_proof(self):
        code=self.mk('rootfs/app/main.lua',b'require "ghost"')
        a=self.mk('rootfs/app/ghost.lua',b'return 1')
        b=self.mk('rootfs/opt/ghost.lua',b'return 2')
        keys=['rootfs/app/main.lua','rootfs/app/ghost.lua','rootfs/opt/ghost.lua']
        rr={k:{'type':'regular'} for k in keys}
        orig={k:{'sha256':hashlib.sha256((self.outer/k).read_bytes()).hexdigest()} for k in keys}
        pub,priv=g.inspect_static(self.stage,rr,orig,{'rootfs/app/main.lua'},expected_counts=None)
        self.assertEqual(len(priv['lua_candidate_edges'][0]['choices']),2)
        self.assertTrue(pub['static_candidates_not_required_dependency_proof'])

    def test_static_report_does_not_expose_elf_source_names(self):
        p=self.mk('rootfs/secret-project/custom-app.lua',b'require "test.secret"')
        k='rootfs/secret-project/custom-app.lua'
        pub,_=g.inspect_static(self.stage,{k:{'type':'regular'}},{k:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}},set(),expected_counts=None)
        self.assertNotIn('secret-project',json.dumps(pub))
        self.assertNotIn('custom-app.lua',json.dumps(pub))

    def test_static_puzzle_hold(self):
        p=self.mk('rootfs/app/foo.txt',b'nothing');r='rootfs/app/foo.txt'
        pub,priv=g.inspect_static(self.stage,{r:{'type':'regular'}},{r:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}},set(),expected_counts=None)
        self.assertEqual(pub['future_optional_puzzle_feature'],'FUTURE_OPTIONAL_NOT_BUILT_NOT_TESTED_HOLD')
        self.assertEqual(pub['older_unknown_hold_entries_preserved'],976)

if __name__=='__main__':unittest.main()
