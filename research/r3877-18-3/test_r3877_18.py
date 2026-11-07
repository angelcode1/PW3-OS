"""Offline ELF32 ARM dynamic-binding fixtures; never connects to the Kindle."""
import io
import json
import struct
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import r3877_18_binding_parser as p
import pw3_r3877_18_relocation_candidates as runner


def synthetic(kind='need', *, reloc_type=22, symidx=1, missing_export=False,
              no_rel=False, bad_versym=False, weak=False, bad_reloc_link=False,
              version=True, hidden=False, nobits=False):
    """Build small minimal ARM ET_DYN with realistic .dynsym, GNU version and REL."""
    b=bytearray(4096)
    b[:7]=b'\x7fELF\x01\x01\x01'
    struct.pack_into('<H',b,16,3)   # ET_DYN
    struct.pack_into('<H',b,18,40)  # EM_ARM
    struct.pack_into('<I',b,20,1)
    struct.pack_into('<I',b,32,256)
    struct.pack_into('<H',b,46,40)
    sections=[(0,0,0,0,0,0)]
    dataoffset=1024
    def add_section(typ, flags, raw, link=0,info=0,entsize=0,off=None,size=None):
        nonlocal dataoffset
        if off is None: off=dataoffset
        if size is None: size=len(raw)
        if raw:
            b[off:off+len(raw)]=raw
            dataoffset=(off+len(raw)+7)&~7
        sections.append((typ,flags,off,size,link,info,entsize))
        return len(sections)-1
    strings=b'\0foo\0libc.so.6\0GLIBC_2.4\0'
    string_idx=add_section(3,0,strings)
    sname=1 if not missing_export else 0
    st_bind=2 if weak else 1
    table=b'\0'*16+struct.pack('<IIIBBH',sname,0,0,(st_bind<<4)|2,0,1 if kind=='def' else 0)
    dynidx=add_section(11,2,table,link=string_idx,entsize=16)
    indices=[0,2 if version else 1]
    veridx=add_section(p.SHT_VERSYM,2,struct.pack('<HH',*indices)+ (b'\0' if bad_versym else b''),link=dynidx,entsize=2)
    if version:
        if kind=='need':
            req=struct.pack('<HHIII',1,1,5,16,0)+struct.pack('<IHHII',0,0,2,15,0)
            add_section(p.SHT_VERNEED,2,req,link=string_idx,info=1)
        else:
            defs=struct.pack('<HHHHIII',1,0,2,1,0,20,0)+struct.pack('<II',15,0)
            add_section(p.SHT_VERDEF,2,defs,link=string_idx,info=1)
    if no_rel is False:
        data=struct.pack('<II',1280,(symidx<<8)|reloc_type)
        add_section(p.SHT_REL,2,data,link=string_idx if bad_reloc_link else dynidx,entsize=8)
    if nobits:
        add_section(8,2,b'',off=0x200000,size=100000)
    struct.pack_into('<H',b,48,len(sections))
    for i,s in enumerate(sections):
        if i==0:continue
        typ,flags,offset,size,link,info,entsize=s
        struct.pack_into('<IIIIIIIIII',b,256+i*40,0,typ,flags,0,offset,size,link,info,4,entsize)
    return bytes(b)

class ParserTests(unittest.TestCase):
    def test_versioned_import_and_reloc(self):
        v=p.parse(synthetic())
        self.assertEqual(v['reloc_count'],1)
        self.assertEqual(v['relocated_imports'][0]['name'],'foo')
        self.assertEqual(v['relocated_imports'][0]['version'],'GLIBC_2.4')
        self.assertEqual(v['relocated_imports'][0]['version_provider'],'libc.so.6')
    def test_export_has_expected_version(self):
        e=p.parse(synthetic('def',no_rel=True))['exports'][0]
        self.assertEqual((e['name'],e['version']),('foo','GLIBC_2.4'))
    def test_unversioned_import(self):
        self.assertIsNone(p.parse(synthetic(version=False))['relocated_imports'][0]['version'])
    def test_weak_import(self):
        self.assertEqual(p.parse(synthetic(weak=True))['relocated_imports'][0]['bind'],2)
    def test_malformed_relocation_index_rejected(self):
        with self.assertRaisesRegex(p.BindingHold,'RELOC_SYMBOL_INDEX_OUT_OF_BOUNDS'):
            p.parse(synthetic(symidx=33))
    def test_non_dynsym_alloc_reloc_rejected(self):
        with self.assertRaisesRegex(p.BindingHold,'ALLOC_RELOC_NOT_LINKED_TO_DYNSYM'):
            p.parse(synthetic(bad_reloc_link=True))
    def test_bad_versym_size_rejected(self):
        with self.assertRaisesRegex(p.BindingHold,'VERSYM_SIZE_MISMATCH'):
            p.parse(synthetic(bad_versym=True))
    def test_nobits_memory_size_not_file_bytes(self):
        self.assertEqual(p.parse(synthetic(nobits=True))['reloc_count'],1)
    def test_missing_arm_machine_rejected(self):
        data=bytearray(synthetic());struct.pack_into('<H',data,18,183)
        with self.assertRaisesRegex(p.BindingHold,'ARM_MACHINE_REQUIRED'):p.parse(bytes(data))
    def test_malformed_file_backed_section_rejected(self):
        data=bytearray(synthetic());struct.pack_into('<I',data,256+40+20,0xffffffff)
        with self.assertRaisesRegex(p.BindingHold,'SECTION_DATA_OUT_OF_BOUNDS'):p.parse(bytes(data))
    def test_only_alloc_relocations_counted(self):
        data=bytearray(synthetic());
        # final section is relocation; clear SHF_ALLOC
        last=struct.unpack_from('<H',data,48)[0]-1
        struct.pack_into('<I',data,256+last*40+8,0)
        self.assertEqual(p.parse(bytes(data))['reloc_count'],0)

class AnalyzerTests(unittest.TestCase):
    def ctx(self,appkind='need', missing_export=False, weak=False):
        af={'luajit':('file',synthetic(appkind,weak=weak)), 'fbink':('file',synthetic(appkind,weak=weak))}
        sf={'lib/libc.so.6':synthetic('def',missing_export=missing_export,no_rel=True)}
        baseline={'version_requirements_statically_satisfied':True,'app_elf_count':2,'stock_provider_elf_count':1}
        def inspect(data):
            return {'needed':['libc.so.6'] if data in (af['luajit'][1],af['fbink'][1]) else [],
                    'soname':['libc.so.6'] if data==sf['lib/libc.so.6'] else []}
        return af,sf,baseline,inspect
    def test_matching_export_candidate(self):
        af,sf,base,inspect=self.ctx()
        with patch.object(runner.earlier,'analyze',return_value=base),patch.object(runner.app,'inspect_elf',side_effect=inspect):
            r=runner.analyze(af,sf)
        self.assertTrue(r['all_strong_relocation_imports_have_static_candidates'])
        self.assertEqual(r['strong_imports_with_export_candidates'],2)
        self.assertEqual(r['strong_imports_without_export_candidates'],0)
        self.assertFalse(r['runtime_bindings_verified'])
    def test_missing_required_export_is_reported(self):
        af,sf,base,inspect=self.ctx(missing_export=True)
        with patch.object(runner.earlier,'analyze',return_value=base),patch.object(runner.app,'inspect_elf',side_effect=inspect):
            r=runner.analyze(af,sf)
        self.assertFalse(r['all_strong_relocation_imports_have_static_candidates'])
        self.assertEqual(r['strong_imports_without_export_candidates'],2)
    def test_missing_weak_export_not_a_hard_mismatch(self):
        af,sf,base,inspect=self.ctx(missing_export=True,weak=True)
        with patch.object(runner.earlier,'analyze',return_value=base),patch.object(runner.app,'inspect_elf',side_effect=inspect):
            r=runner.analyze(af,sf)
        self.assertTrue(r['all_strong_relocation_imports_have_static_candidates'])
        self.assertEqual(r['weak_imports_without_export_candidates'],2)
    def test_preflight_never_calls_ssh(self):
        output=io.StringIO()
        with patch.object(runner.transport,'one_session_collect',side_effect=AssertionError('SSH attempted')),redirect_stdout(output):
            code=runner.main([])
        self.assertEqual(code,2)
        self.assertEqual(json.loads(output.getvalue())['immutable_hold'],'NOT_BOOTABLE')
    def test_unexpected_target_is_held_before_ssh(self):
        output=io.StringIO()
        with patch.object(runner.transport,'one_session_collect',side_effect=AssertionError('SSH attempted')),redirect_stdout(output):
            code=runner.main(['--target','root@unexpected','--authorize-live-readonly-ssh'])
        self.assertEqual(code,2)
        self.assertEqual(json.loads(output.getvalue())['hold_category'],'UNEXPECTED_SSH_TARGET')

if __name__=='__main__':unittest.main()
