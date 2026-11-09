import io,json,struct,tarfile,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import pw3_r3877_16_system_elf_audit as m

def elf(soft=True):
    b=bytearray(52);b[:7]=b'\x7fELF\x01\x01\x01'
    struct.pack_into('<H',b,18,40);struct.pack_into('<I',b,28,52)
    struct.pack_into('<I',b,36,0x05000200 if soft else 0x05000400)
    struct.pack_into('<HH',b,42,32,0)
    return bytes(b)

def tar(items):
    b=io.BytesIO()
    with tarfile.open(fileobj=b,mode='w') as tf:
        for path,blob in items:
            ti=tarfile.TarInfo(path);ti.size=len(blob);tf.addfile(ti,io.BytesIO(blob))
    return b.getvalue()

class Regression(unittest.TestCase):
    def test_preflight(self):
        with patch('sys.stdout',new_callable=io.StringIO) as out:self.assertEqual(m.main([]),2)
        d=json.loads(out.getvalue());self.assertEqual(d['immutable_hold'],'NOT_BOOTABLE')
    def test_target_gate(self):
        with patch('sys.stdout',new_callable=io.StringIO) as out:
            self.assertEqual(m.main(['--target','other','--authorize-live-readonly-ssh']),2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'UNEXPECTED_SSH_TARGET')
    def test_port_gate(self):
        with patch('sys.stdout',new_callable=io.StringIO) as out:
            self.assertEqual(m.main(['--target',m.EXPECTED_TARGET,'--port','0','--authorize-live-readonly-ssh']),2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'SSH_PORT_INVALID')
    def test_allowed(self):
        self.assertTrue(m.allowed_member('lib/libc.so.6'))
        for p in ['etc/shadow','usr/lib/../libc.so.6','lib/other.so.1']:
            self.assertFalse(m.allowed_member(p))
    def test_reject_bad_tar(self):
        with self.assertRaises(m.Hold):m.parse_archive(b'bad')
    def test_reject_oversized(self):
        with self.assertRaises(m.Hold):m.parse_archive(b'a'*(m.MAX_ARCHIVE+1))
    def test_reject_other(self):
        with self.assertRaises(m.Hold):m.parse_archive(tar([('etc/passwd',elf())]))
    def test_reject_duplicate(self):
        with self.assertRaises(m.Hold):m.parse_archive(tar([('lib/libc.so.6',elf()),('lib/libc.so.6',elf())]))
    def test_all_parse(self):
        self.assertEqual(len(m.parse_archive(tar([('lib/'+n,elf()) for n in m.NAMES]))),7)
    def test_missing_and_no_closure(self):
        d=m.summarize({'lib/libc.so.6':elf()},None)
        self.assertIn('ld-linux.so.3',d['provider_names_absent'])
        self.assertFalse(d['koreader_dependency_closure_verified'])
    def test_all_soft(self):
        d=m.summarize({'lib/'+n:elf() for n in m.NAMES},None)
        self.assertTrue(d['all_provider_elf_headers_match_koreader_soft_float'])
    def test_hard_float_rejected(self):
        d=m.summarize({'lib/'+n:elf(False) for n in m.NAMES},None)
        self.assertEqual(len(d['provider_abi_mismatch']),7)
    def test_good_evidence(self):
        raw={'milestone':'R3877.15','result':'PASS_KOREADER_APP_ELF_METADATA_ONLY','inventory':{'arm_elf_file_count':38,'float_abi_declarations':['SOFT'],'external_or_unverified_library_names':list(m.NAMES)}}
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'r15.json';p.write_text(json.dumps(raw))
            self.assertTrue(m.load_koreader_evidence(p)['r3877_15_evidence_checked'])
    def test_bad_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'r15.json';p.write_text('{}')
            with self.assertRaises(m.Hold):m.load_koreader_evidence(p)
    def test_mock_success(self):
        with patch.object(m,'remote_tar',return_value=tar([('lib/'+n,elf()) for n in m.NAMES])):
            with patch('sys.stdout',new_callable=io.StringIO) as out:
                rc=m.main(['--target',m.EXPECTED_TARGET,'--authorize-live-readonly-ssh'])
        self.assertEqual(rc,0)
        d=json.loads(out.getvalue())
        self.assertEqual(d['result'],'PASS_SYSTEM_ELF_METADATA_ONLY')
        self.assertFalse(d['device_files_written'])
    def test_mock_partial(self):
        with patch.object(m,'remote_tar',return_value=tar([('lib/libc.so.6',elf())])):
            with patch('sys.stdout',new_callable=io.StringIO) as out:
                rc=m.main(['--target',m.EXPECTED_TARGET,'--authorize-live-readonly-ssh'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'SYSTEM_PROVIDER_ABSENT_OR_ABI_MISMATCH')
    def test_ssh_argv(self):
        calls=[]
        def run(argv,**kw):
            calls.append((argv,kw));return type('CP',(),{'returncode':0,'stdout':tar([('lib/libc.so.6',elf())])})
        with patch.object(m.subprocess,'run',side_effect=run):m.remote_tar(m.EXPECTED_TARGET,2222)
        argv,kw=calls[0]
        self.assertEqual(argv[:4],['ssh','-T','-p','2222'])
        self.assertEqual(argv[-2:],[m.EXPECTED_TARGET,'sh -s'])
        self.assertIn('tar -chf -',kw['input'].decode())
    def test_even_success_does_not_prove_glibc(self):
        d=m.summarize({'lib/'+n:elf() for n in m.NAMES},None)
        self.assertFalse(d['glibc_symbol_versions_verified'])
        self.assertFalse(d['library_resolution_at_runtime_verified'])

if __name__=='__main__': unittest.main()
