"""R3877.18.3 offline provider-type diagnostic tests; no SSH or Kindle access."""
import io, json, struct, unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import r3877_18_3_provider_types as c
import pw3_r3877_18_3_provider_type_diagnostic as runner
import r3877_18_1_ssh_diagnostic as sshdiag

def im(name, typ=2, version=None, provider=None):
    return {'name':name,'typ':typ,'version':version,'version_provider':provider,
            'bind':1,'version_weak':False,'version_hidden':False,'symidx':1}

def ex(name,typ=2,version=None):
    return {'name':name,'typ':typ,'version':version,'version_hidden':False,'bind':1}

def fixture(provider_type=10, exe_type=2):
    exe=bytearray(b'\x00'*52);exe[0:7]=b'\x7fELF\x01\x01\x01';struct.pack_into('<H',exe,16,exe_type)
    af={'libs/mod.so':('file',b'mod'),'luajit':('file',bytes(exe))}
    sf={'librt.so.1':b'librt','libc.so.6':b'libc'}
    records={
        b'mod':{'exports':[],'relocated_imports':[im('lua_pcall',typ=0),im('clock_gettime',2,'GLIBC_2.4','librt.so.1')], 'needed':['librt.so.1'],'soname':['mod.so']},
        bytes(exe):{'exports':[ex('lua_pcall')],'relocated_imports':[], 'needed':[],'soname':[]},
        b'librt':{'exports':[ex('clock_gettime',provider_type,'GLIBC_2.4')],'relocated_imports':[],'needed':[], 'soname':['librt.so.1']},
        b'libc':{'exports':[],'relocated_imports':[],'needed':[], 'soname':['libc.so.6']},
    }
    baseline={'classified_strong_import_count':2,'missing_strong_reason_counts':{
        'main_luajit_executable_export_candidate_outside_strict_scope':1,
        'named_provider_symbol_type_mismatch':1},'files_parsed':4}
    return af,sf,records,baseline

class TypeHelpersTests(unittest.TestCase):
    def test_arm_tfunc_number(self):self.assertEqual(c.type_label(13),'STT_ARM_TFUNC')
    def test_ifunc_number(self):self.assertEqual(c.type_label(10),'STT_GNU_IFUNC')
    def test_function_number(self):self.assertEqual(c.type_label(2),'STT_FUNC')
    def test_notype_number(self):self.assertEqual(c.type_label(0),'STT_NOTYPE')
    def test_type_unknown(self):self.assertEqual(c.type_label(15),'STT_UNKNOWN_15')
    def test_ifunc_is_conditional(self):self.assertEqual(c.type_hypothesis(2,10),'FUNCTION_IMPORT_TO_GNU_IFUNC_EXPORT_CONDITIONAL')
    def test_tfunc_is_conditional(self):self.assertEqual(c.type_hypothesis(2,13),'FUNCTION_IMPORT_TO_ARM_THUMB_FUNCTION_EXPORT_CONDITIONAL')
    def test_object_mismatch_is_not_conditional(self):self.assertEqual(c.type_hypothesis(2,1),'FUNCTION_IMPORT_TO_OBJECT_EXPORT_TYPE_MISMATCH')
    def test_notype_is_generic_mismatch(self):self.assertEqual(c.type_hypothesis(1,2),'OTHER_IMPORT_EXPORT_TYPE_MISMATCH')

class AnalyzerTests(unittest.TestCase):
    def inspect(self,prov=10,exe=2,baseline_override=None):
        af,sf,rs,baseline=fixture(prov,exe)
        if baseline_override: baseline.update(baseline_override)
        with patch.object(c.scope,'analyze',return_value=baseline),\
             patch.object(c.parser,'parse',side_effect=lambda raw:rs[raw]),\
             patch.object(c.app,'inspect_elf',side_effect=lambda raw:rs[raw]):
            return c.analyze(af,sf,expected_counts=False)
    def test_ifunc_is_candidate_only(self):
        d=self.inspect()
        self.assertEqual(d['prior_strict_scope_missing_count'],2)
        self.assertEqual(d['main_luajit_export_candidates_outside_strict_scope'],1)
        self.assertEqual(d['type_mismatch_count'],1)
        self.assertEqual(d['type_mismatch_pairs'][0]['provider_export_types'][0]['type'],'STT_GNU_IFUNC')
        self.assertFalse(d['runtime_bindings_verified'])
        self.assertFalse(d['full_koreader_dependency_closure_verified'])
        self.assertEqual(d['immutable_hold'],'NOT_BOOTABLE')
    def test_thumb_tfunc_is_not_runtime_proven(self):
        d=self.inspect(13)
        self.assertIn('ARM_THUMB',d['type_mismatch_pairs'][0]['provider_export_types'][0]['hypothesis'])
    def test_object_mismatch_is_not_accepted(self):
        d=self.inspect(1)
        self.assertIn('OBJECT',d['type_mismatch_pairs'][0]['provider_export_types'][0]['hypothesis'])
        self.assertFalse(d['runtime_bindings_verified'])
    def test_luajit_elf_dynamic_recorded(self):
        self.assertEqual(self.inspect(10,3)['main_luajit_elf_type'],'ET_DYN')
    def test_expected_counts_lock_fails_on_synthetic(self):
        af,sf,rs,baseline=fixture()
        with patch.object(c.scope,'analyze',return_value=baseline):
            with self.assertRaisesRegex(c.ProviderHold,'EXPECTED_R3877_18_2_BASELINE_DRIFT'):
                c.analyze(af,sf)
    def test_classification_totals_gate(self):
        with self.assertRaisesRegex(c.ProviderHold,'SCOPE_CLASSIFICATION_INCONSISTENT'):
            self.inspect(baseline_override={'classified_strong_import_count':3})
    def test_malformed_luajit_type_hold(self):
        with self.assertRaisesRegex(c.ProviderHold,'UNEXPECTED_LUAJIT_ELF_TYPE'):
            self.inspect(exe=0)
    def test_missing_versioned_export_reconciles_fail_closed(self):
        af,sf,rs,baseline=fixture()
        rs[b'librt']['exports'][0]['version']='GLIBC_2.17'
        with patch.object(c.scope,'analyze',return_value=baseline),\
             patch.object(c.parser,'parse',side_effect=lambda raw:rs[raw]),\
             patch.object(c.app,'inspect_elf',side_effect=lambda raw:rs[raw]):
            with self.assertRaisesRegex(c.ProviderHold,'UNCLASSIFIED_STATIC_MISS_'):
                c.analyze(af,sf,expected_counts=False)

class CliTests(unittest.TestCase):
    def call(self,args):
        buf=io.StringIO()
        with redirect_stdout(buf):rc=runner.main(args)
        return rc,json.loads(buf.getvalue())
    def test_preflight_does_not_invoke_ssh(self):
        with patch.object(sshdiag,'one_session_collect',side_effect=AssertionError('called')):
            rc,out=self.call([])
        self.assertEqual(rc,2)
        self.assertEqual(out['ssh_sessions_requested'],0)
        self.assertEqual(out['immutable_hold'],'NOT_BOOTABLE')
    def test_bad_ssh_target_rejected(self):
        with patch.object(sshdiag,'one_session_collect',side_effect=AssertionError('called')):
            rc,out=self.call(['--target','root@other','--authorize-live-readonly-ssh'])
        self.assertEqual(rc,2)
        self.assertEqual(out['hold_category'],'UNEXPECTED_SSH_TARGET')
    def test_bad_port_rejected(self):
        with patch.object(sshdiag,'one_session_collect',side_effect=AssertionError('called')):
            rc,out=self.call(['--target',runner.transport.EXPECTED_TARGET,'--port','0','--authorize-live-readonly-ssh'])
        self.assertEqual(rc,2)
        self.assertEqual(out['hold_category'],'SSH_PORT_INVALID')
    def test_ssh_probe_does_not_collect(self):
        with patch.object(sshdiag,'probe_ssh_only',return_value={'kernel_release':'3.0.35-lab126'}),\
             patch.object(sshdiag,'one_session_collect',side_effect=AssertionError('called')):
            rc,out=self.call(['--target',runner.transport.EXPECTED_TARGET,'--probe-ssh-only','--authorize-live-readonly-ssh'])
        self.assertEqual(rc,0)
        self.assertEqual(out['result'],'PASS_SSH_HANDSHAKE_ONLY')
        self.assertFalse(out['app_and_stock_binary_contents_transferred'])
    def test_success_mock_only_static(self):
        with patch.object(sshdiag,'one_session_collect',return_value=b'archive'),\
             patch.object(runner.transport,'parse_concatenated_archives',return_value=({},{})),\
             patch.object(runner.audit,'analyze',return_value={'type_mismatch_count':4,'runtime_bindings_verified':False,'immutable_hold':'NOT_BOOTABLE'}):
            rc,out=self.call(['--target',runner.transport.EXPECTED_TARGET,'--authorize-live-readonly-ssh'])
        self.assertEqual(rc,0)
        self.assertEqual(out['result'],'PASS_PROVIDER_TYPE_METADATA_ONLY')
        self.assertFalse(out['inventory']['runtime_bindings_verified'])
    def test_malformed_parser_hold(self):
        with patch.object(sshdiag,'one_session_collect',return_value=b'archive'),\
             patch.object(runner.transport,'parse_concatenated_archives',return_value=({},{})),\
             patch.object(runner.audit,'analyze',side_effect=c.ProviderHold('ELF_PARSE_FAILED')):
            rc,out=self.call(['--target',runner.transport.EXPECTED_TARGET,'--authorize-live-readonly-ssh'])
        self.assertEqual(rc,2)
        self.assertEqual(out['hold_category'],'ELF_PARSE_FAILED')
        self.assertEqual(out['immutable_hold'],'NOT_BOOTABLE')

if __name__=='__main__':unittest.main()
