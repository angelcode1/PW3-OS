"""R3877.18.2 offline tests: no SSH, no Kindle, no binary execution."""
import unittest,io,json
from contextlib import redirect_stdout
from unittest.mock import patch
import r3877_18_2_scope_classifier as c
import pw3_r3877_18_2_scope_diagnostic as r
import r3877_18_1_ssh_diagnostic as diag

def im(name='lua_pcall',version=None,provider=None,typ=2):
    return {'name':name,'version':version,'version_provider':provider,'typ':typ,'bind':1,'version_weak':False}
def ex(name='lua_pcall',version=None,typ=2,hidden=False):
    return {'name':name,'version':version,'typ':typ,'version_hidden':hidden,'bind':1}

class ScopeTests(unittest.TestCase):
    def check(self,imp,index=None,reach=None,providers=None):
        index=index if index is not None else {imp['name']:[('koreader/luajit',ex(imp['name']))]}
        reachable={'koreader/libs/mod.so':set(reach if reach is not None else ['koreader/libs/mod.so','system/lib/libc.so.6'])}
        return c.describe(imp,'koreader/libs/mod.so',index,reachable,providers or {})
    def test_luajit_as_main_executable_conditional_candidate(self):
        self.assertEqual(self.check(im())['reason'],'main_luajit_executable_export_candidate_outside_strict_scope')
    def test_uncollected_symbol(self):
        self.assertEqual(self.check(im('never_exported'),{})['reason'],'no_export_with_this_name_in_collected_elf_set')
    def test_other_dlopen_scope_candidate(self):
        self.assertEqual(self.check(im(),{'lua_pcall':[('koreader/libs/other.so',ex())]})['reason'],'export_candidate_outside_strict_dependency_scope')
    def test_wrong_version_in_named_provider(self):
        x=self.check(im('clock_gettime','GLIBC_2.4','librt.so.1'),{'clock_gettime':[('system/lib/librt.so.1',ex('clock_gettime','GLIBC_2.17'))]},providers={'librt.so.1':'system/lib/librt.so.1'})
        self.assertEqual(x['reason'],'named_provider_version_or_default_mismatch')
        self.assertEqual(x['named_provider_available_versions'],['GLIBC_2.17'])
    def test_named_provider_does_not_export_symbol(self):
        self.assertEqual(self.check(im('clock_gettime','GLIBC_2.4','librt.so.1'),{},providers={'librt.so.1':'system/lib/librt.so.1'})['reason'],'named_provider_has_no_matching_symbol')
    def test_provider_not_collected(self):
        self.assertEqual(self.check(im('clock_gettime','GLIBC_2.4','librt.so.1'),{})['reason'],'version_provider_name_uncollected')
    def test_named_provider_outside_reachable_scope(self):
        i=im('clock_gettime','GLIBC_2.4','librt.so.1')
        d=self.check(i,{'clock_gettime':[('system/lib/librt.so.1',ex('clock_gettime','GLIBC_2.4'))]},providers={'librt.so.1':'system/lib/librt.so.1'})
        self.assertEqual(d['reason'],'named_provider_outside_strict_dependency_scope')
    def test_type_mismatch(self):
        d=self.check(im('clock_gettime','GLIBC_2.4','librt.so.1'),{'clock_gettime':[('system/lib/librt.so.1',ex('clock_gettime','GLIBC_2.4',typ=1))]},providers={'librt.so.1':'system/lib/librt.so.1'})
        self.assertEqual(d['reason'],'named_provider_symbol_type_mismatch')
    def test_version_hidden_unversioned_import_does_not_match(self):
        self.assertFalse(c.compatible(ex('x','GLIBC_2.4',hidden=True),im('x')))
    def test_default_version_unversioned_import_can_match(self):
        self.assertTrue(c.compatible(ex('x','GLIBC_2.4',hidden=False),im('x')))
    def test_symbol_not_type_wildcard_if_both_specified(self):
        self.assertFalse(c.compatible(ex('x',typ=1),im('x',typ=2)))
    def test_not_type_wildcard(self):
        self.assertTrue(c.compatible(ex('x',typ=0),im('x',typ=2)))
    def test_preflight_no_ssh(self):
        s=io.StringIO()
        with patch.object(diag.subprocess,'run',side_effect=AssertionError('no SSH allowed')):
            with redirect_stdout(s):rc=r.main([])
        self.assertEqual(rc,2);d=json.loads(s.getvalue());self.assertEqual(d['immutable_hold'],'NOT_BOOTABLE');self.assertEqual(d['ssh_sessions_requested'],0)
    def test_bad_target_no_ssh(self):
        s=io.StringIO()
        with patch.object(diag.subprocess,'run',side_effect=AssertionError('no SSH allowed')):
            with redirect_stdout(s):rc=r.main(['--target','root@unknown','--authorize-live-readonly-ssh'])
        self.assertEqual(rc,2);self.assertEqual(json.loads(s.getvalue())['hold_category'],'UNEXPECTED_SSH_TARGET')
    def test_probe_only_does_not_collect_archive(self):
        s=io.StringIO()
        with patch.object(diag,'probe_ssh_only',return_value={'probe':'READONLY_UNAME_ONLY'}) as probe,patch.object(diag,'one_session_collect',side_effect=AssertionError('archive touched')):
            with redirect_stdout(s):rc=r.main(['--target',diag.original.EXPECTED_TARGET,'--probe-ssh-only','--authorize-live-readonly-ssh'])
        self.assertEqual(rc,0);self.assertFalse(json.loads(s.getvalue())['app_and_stock_binary_contents_transferred']);self.assertEqual(probe.call_count,1)

# Additional whole-analyzer fixtures, exercising the baseline reconciliation gate.
class WholeAnalyzerTests(unittest.TestCase):
    def fixture(self, count=1):
        # The ELF contents are intentionally synthetic; the parsers are patched.
        af={'libs/mod.so':('file',b'module'),'luajit':('file',b'executable')}
        sf={'libc.so.6':b'system'}
        mod={'exports':[],'relocated_imports':[dict(im(),symidx=1)],
             'needed':['libc.so.6'],'soname':['mod.so']}
        exe={'exports':[ex()],'relocated_imports':[], 'needed':['libc.so.6'],'soname':[]}
        libc={'exports':[],'relocated_imports':[],'needed':[],'soname':['libc.so.6']}
        ps={b'module':mod,b'executable':exe,b'system':libc}
        def appinfo(raw):return {'needed':ps[raw]['needed'],'soname':ps[raw]['soname']}
        baseline={'files_parsed':3,'strong_relocated_imports':1,'weak_relocated_imports':0,
                  'strong_imports_without_export_candidates':count,'strong_imports_with_export_candidates':0,
                  'weak_imports_without_export_candidates':0}
        return af,sf,ps,appinfo,baseline
    def test_full_analyzer_luajit_candidate_is_only_conditional(self):
        af,sf,ps,appinfo,baseline=self.fixture()
        with patch.object(c.prior,'analyze',return_value=baseline),patch.object(c.parser,'parse',side_effect=lambda raw:ps[raw]),patch.object(c.app,'inspect_elf',side_effect=appinfo):
            result=c.analyze(af,sf)
        self.assertTrue(result['same_scope_baseline_reconciled'])
        self.assertEqual(result['classified_strong_import_count'],1)
        self.assertEqual(result['missing_strong_reason_counts'],{'main_luajit_executable_export_candidate_outside_strict_scope':1})
        self.assertFalse(result['runtime_bindings_verified'])
        self.assertFalse(result['koreader_dependency_closure_verified'])
        self.assertEqual(result['immutable_hold'],'NOT_BOOTABLE')
    def test_baseline_missing_count_mismatch_fails_closed(self):
        af,sf,ps,appinfo,baseline=self.fixture(count=0)
        with patch.object(c.prior,'analyze',return_value=baseline),patch.object(c.parser,'parse',side_effect=lambda raw:ps[raw]),patch.object(c.app,'inspect_elf',side_effect=appinfo):
            with self.assertRaisesRegex(c.ScopeHold,'BASELINE_STRONG_IMPORT_COUNTS_DO_NOT_RECONCILE'):
                c.analyze(af,sf)

if __name__=='__main__':unittest.main()
