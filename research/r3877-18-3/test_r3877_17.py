import unittest, struct, io, json, hashlib
from unittest.mock import patch
from contextlib import redirect_stdout
import r3877_17_version_parser as v
import pw3_r3877_17_symbol_version_audit as m

def fixture(mode='need', version='GLIBC_2.13'):
    b=bytearray(512)
    b[:7]=b'\x7fELF\x01\x01\x01'
    struct.pack_into('<H',b,18,40)
    strtab=b'\0libc.so.6\0'+version.encode()+b'\0'
    b[64:64+len(strtab)]=strtab
    struct.pack_into('<I',b,32,256) # e_shoff
    struct.pack_into('<HH',b,46,40,3) # e_shentsize e_shnum
    # section 0 zero, section 1 strings, section 2 GNU
    struct.pack_into('<IIIIIIIIII',b,256+40,0,3,0,0,64,len(strtab),0,0,1,0)
    if mode=='need':
        offset=128
        struct.pack_into('<HHIII',b,offset,1,1,1,16,0)
        struct.pack_into('<IHHII',b,offset+16,0,0,2,11,0)
        struct.pack_into('<IIIIIIIIII',b,256+80,0,v.SHT_VERNEED,0,0,offset,32,1,1,4,0)
    else:
        offset=128
        struct.pack_into('<HHHHIII',b,offset,1,0,2,1,0,20,0)
        struct.pack_into('<II',b,offset+20,11,0)
        struct.pack_into('<IIIIIIIIII',b,256+80,0,v.SHT_VERDEF,0,0,offset,28,1,1,4,0)
    return bytes(b)

class Tests(unittest.TestCase):
    def test_synthetic_provider_version_compatible(self):
        appfiles={'fbink':('file',fixture('need')), 'luajit':('file',fixture('def'))}
        for i in range(36): appfiles['libs/lib%d.so'%i]=('file',fixture('def'))
        systemfiles={'lib/'+n:fixture('def') for n in m.syslib.NAMES}
        ha=hashlib.sha256(fixture('need')).hexdigest()
        hd=hashlib.sha256(fixture('def')).hexdigest()
        with patch.object(m,'EXPECTED_SHA',{'fbink':ha,'luajit':hd,'libc.so.6':hd}),\
             patch.object(m.app,'inspect_elf',return_value={'kind':'ELF32_ARM','eabi_version':5,'float_abi':'SOFT','soname':[],'needed':[]}),\
             patch.object(m,'normalize_interp',return_value=None):
            result=m.analyze(appfiles,systemfiles)
        self.assertTrue(result['version_requirements_statically_satisfied'])
        self.assertEqual(result['provider_names_absent'],{})
        self.assertEqual(result['required_version_names_absent'],{})
        self.assertEqual(result['app_elf_count'],38)
        self.assertEqual(result['stock_provider_elf_count'],7)
    def test_synthetic_missing_provider_version(self):
        appfiles={'fbink':('file',fixture('need','GLIBC_9.99')), 'luajit':('file',fixture('def'))}
        for i in range(36): appfiles['libs/lib%d.so'%i]=('file',fixture('def'))
        systemfiles={'lib/'+n:fixture('def') for n in m.syslib.NAMES}
        ha=hashlib.sha256(fixture('need','GLIBC_9.99')).hexdigest()
        hd=hashlib.sha256(fixture('def')).hexdigest()
        with patch.object(m,'EXPECTED_SHA',{'fbink':ha,'luajit':hd,'libc.so.6':hd}),\
             patch.object(m.app,'inspect_elf',return_value={'kind':'ELF32_ARM','eabi_version':5,'float_abi':'SOFT','soname':[],'needed':[]}),\
             patch.object(m,'normalize_interp',return_value=None):
            result=m.analyze(appfiles,systemfiles)
        self.assertFalse(result['version_requirements_statically_satisfied'])
        self.assertIn('libc.so.6', result['required_version_names_absent'])
    def test_need(self):
        out=v.parse_version_sections(fixture('need'))
        self.assertEqual(out['needs'],{'libc.so.6':[('GLIBC_2.13',False)]})
        self.assertEqual(out['sections_seen']['verneed'],1)
    def test_def(self):
        out=v.parse_version_sections(fixture('def'))
        self.assertEqual(out['defines'],['GLIBC_2.13'])
    def test_wrong_abi(self):
        b=bytearray(fixture()); b[4]=2
        with self.assertRaises(v.VersionHold):v.parse_version_sections(b)
    def test_wrong_machine(self):
        b=bytearray(fixture()); struct.pack_into('<H',b,18,3)
        with self.assertRaises(v.VersionHold):v.parse_version_sections(b)
    def test_bad_shoff(self):
        b=bytearray(fixture()); struct.pack_into('<I',b,32,10000)
        with self.assertRaises(v.VersionHold):v.parse_version_sections(b)
    def test_bad_str_link(self):
        b=bytearray(fixture()); struct.pack_into('<I',b,256+80+24,9)
        with self.assertRaises(v.VersionHold):v.parse_version_sections(b)
    def test_missing_vn_aux(self):
        b=bytearray(fixture()); struct.pack_into('<I',b,128+8,1)
        with self.assertRaises(v.VersionHold):v.parse_version_sections(b)
    def test_truncated_verneed(self):
        b=bytearray(fixture()); struct.pack_into('<I',b,256+80+20,15)
        with self.assertRaises(v.VersionHold):v.parse_version_sections(b)
    def test_unterminated_string(self):
        b=bytearray(fixture()); b[64+11:64+len(b'\0libc.so.6\0GLIBC_2.13\0')]=b'A'*len('GLIBC_2.13\0')
        with self.assertRaises(v.VersionHold):v.parse_version_sections(b)
    def test_interpreter_double_nul(self):
        b=bytearray(512);b[:7]=b'\x7fELF\x01\x01\x01';struct.pack_into('<H',b,18,40)
        struct.pack_into('<I',b,28,80);struct.pack_into('<HH',b,42,32,1)
        path=b'/lib/ld-linux.so.3\0\0';b[176:176+len(path)]=path
        struct.pack_into('<IIIIIIII',b,80,3,176,0,0,len(path),len(path),0,0)
        self.assertEqual(v.normalize_interp(bytes(b)),'/lib/ld-linux.so.3')
    def test_interpreter_nonzero_padding(self):
        b=bytearray(512);b[:7]=b'\x7fELF\x01\x01\x01';struct.pack_into('<H',b,18,40)
        struct.pack_into('<I',b,28,80);struct.pack_into('<HH',b,42,32,1)
        path=b'/lib/ld-linux.so.3\0X';b[176:176+len(path)]=path
        struct.pack_into('<IIIIIIII',b,80,3,176,0,0,len(path),len(path),0,0)
        with self.assertRaises(v.VersionHold):v.normalize_interp(bytes(b))
    def test_preflight_gate(self):
        stdout=io.StringIO()
        with redirect_stdout(stdout):rc=m.main([])
        self.assertEqual(rc,2)
        parsed=json.loads(stdout.getvalue())
        self.assertEqual(parsed['hold_category'],'EXPLICIT_READONLY_SSH_AUTHORIZATION_REQUIRED')
        self.assertEqual(parsed['immutable_hold'],'NOT_BOOTABLE')
    def test_unexpected_target_precedes_ssh(self):
        stdout=io.StringIO()
        with redirect_stdout(stdout):rc=m.main(['--target','root@another','--authorize-live-readonly-ssh'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(stdout.getvalue())['hold_category'],'UNEXPECTED_SSH_TARGET')
    def test_invalid_port_precedes_ssh(self):
        stdout=io.StringIO()
        with redirect_stdout(stdout):rc=m.main(['--target',m.EXPECTED_TARGET,'-p','66000','--authorize-live-readonly-ssh'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(stdout.getvalue())['hold_category'],'SSH_PORT_INVALID')

if __name__=='__main__':unittest.main()
