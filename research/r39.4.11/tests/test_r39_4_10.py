"""R39.4.10: original PdfDocument constructor source-bound second sidecar read."""
import unittest,hashlib,sys,importlib.util,zipfile,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'r394'))
from review_r39410 import review,SECOND_CTX,SECOND_GATE,SECOND_LOAD,FIRST_CTX,TARGET,CLEAN
from review_r3945 import GATE as FIRST_GATE,LOADED as FIRST_LOAD
import test_r39_4_6 as base_test
spec=importlib.util.spec_from_file_location('check39410',ROOT/'r394/check_inputs.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
class PdfDocumentConstructorSidecar(unittest.TestCase):
    def fixture(self):
        state=base_test.StrictTwoCycle().fixture()
        state[2]['r39410_pdfdocument_constructor_phase_pinned']=True
        log=state[0]
        log=log.replace(FIRST_GATE,TARGET+'\n'+FIRST_CTX+'\n'+FIRST_GATE,1)
        log=log.replace('R39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED\n',
            'R39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED\n'+TARGET+'\n'+SECOND_CTX+'\n'+SECOND_GATE+'\n'+SECOND_LOAD+'\n',1)
        log=log.replace('R39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY',
                        CLEAN+'\nR39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY',1)
        state[0]=log
        return state
    def test_host_fixture_only_not_arm(self):
        o=review(*self.fixture())
        self.assertEqual(o['verdict'],'R39_4_10_PDFDOCUMENT_CONSTRUCTOR_REOPEN_ARM_PASS')
        self.assertFalse(o['device_access_authorized'])
        self.assertEqual(o['immutable_hold'],'NOT_BOOTABLE')
    def reject(self,change,reason):
        a=self.fixture();change(a)
        with self.assertRaisesRegex(ValueError,reason):review(*a)
    def test_wrong_source_pin(self):
        self.reject(lambda a:a[2].__setitem__('r39410_pdfdocument_constructor_phase_pinned',False),'source-pinned')
    def test_original_strict_fail(self):
        self.reject(lambda a:a[4].__setitem__('verdict','FAIL'),'strict PASS')
    def test_original_r25_fail(self):
        self.reject(lambda a:a[1].__setitem__('verdict','FAIL'),'R25 baseline')
    def test_missing_second_context(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace(SECOND_CTX+'\n','')),'source-bound')
    def test_unreleased_first_doc(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace('prior_document_released=true','prior_document_released=false')),'strict')
    def test_second_registry_not_empty(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace('registry_empty=true','registry_empty=false')),'strict')
    def test_fm_not_closed(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace('fm_closed=true','fm_closed=false')),'strict')
    def test_input_cycle_started_early(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace('input_cycle1=true','input_cycle1=false')),'strict')
    def test_missing_second_gate(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace(SECOND_GATE+'\n','')),'source-bound')
    def test_wrong_pdf_method(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace('convertKopt=true','convertKopt=false')),'strict')
    def test_wrong_pdf_constructor(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace('pdf_init=true','pdf_init=false')),'strict')
    def test_wrong_docsettings(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace('docsettings=true convertKopt','docsettings=false convertKopt')),'strict')
    def test_no_original_pcall(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace('c_pcall=true docsettings=true convertKopt','c_pcall=false docsettings=true convertKopt')),'strict')
    def test_not_plain_regular_file(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace('regular_file=true phase2=true','regular_file=false phase2=true')),'strict')
    def test_phase2_false(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace('phase2=true','phase2=false')),'strict')
    def test_missing_load(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace(SECOND_LOAD+'\n','')),'strict')
    def test_duplicate_context(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace(SECOND_CTX,SECOND_CTX+'\n'+SECOND_CTX,1)),'source-bound')
    def test_duplicate_gate(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace(SECOND_GATE,SECOND_GATE+'\n'+SECOND_GATE,1)),'source-bound')
    def test_third_sidecar_read(self):
        self.reject(lambda a:a.__setitem__(0,a[0]+'\n'+TARGET),'source-bound')
    def test_wrong_sidecar_file(self):
        self.reject(lambda a:a.__setitem__(0,a[0].replace(TARGET,TARGET.replace('exact_pdf_sidecar','other_temp_home'),1)),'exactly two original sidecar')
    def test_second_read_after_input(self):
        def f(a):
            chunk=TARGET+'\n'+SECOND_CTX+'\n'+SECOND_GATE+'\n'+SECOND_LOAD+'\n'
            a[0]=a[0].replace(chunk,'')
            marker='R39_1_GENUINE_READERUI_INPUT_INHIBIT_REQUESTED_SYNTHETIC_ONLY'
            ix=a[0].rfind(marker)
            a[0]=a[0][:ix+len(marker)]+ '\n'+chunk+a[0][ix+len(marker):]
        self.reject(f,'reordered')
    def test_second_read_before_schedule(self):
        def f(a):
            chunk=TARGET+'\n'+SECOND_CTX+'\n'+SECOND_GATE+'\n'+SECOND_LOAD+'\n'
            a[0]=a[0].replace(chunk,'').replace('R39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED',chunk+'R39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED',1)
        self.reject(f,'reordered')
    def test_denied_operation(self):
        self.reject(lambda a:a.__setitem__(0,a[0]+'\nR39_4_3_FIRST_DENIAL kind=DOFILE'),'denied|runtime error')
    def test_previous_predicted_registry_gate_forbidden(self):
        self.reject(lambda a:a.__setitem__(0,a[0]+'\nR39_4_9_REGISTRY_PROVIDER_SIDECAR_GATE bogus'),'obsolete')
    def test_source_guard_bound_exact_caller_not_general(self):
        s=(ROOT/'r394/loop_guard.lua').read_text()
        for marker in ('frame4.func==pdfdocument.convertKoptToReflowableFontSize','frame4.currentline==74',
            'frame5.func==pdfdocument.init','frame5.currentline==34',
            "pdfdocument%.lua$",'registry_empty and original_pdf_size and original_pdf_init',
            'r3945_sidecar_loads==1 and r394_input_lifecycles==1',
            'from_returned_filemanager or from_pdfdocument_second_open',
            "if path==r3945_sidecar then", "deny('DOFILE:'..tostring(path))",
            'r3945_sidecar_writes==2 and r3945_sidecar_loads==3'):
            self.assertIn(marker,s)
        self.assertNotIn('stats.denied=0',s)
    def test_guard_checker_hash_pinned(self):
        self.assertEqual(hashlib.sha256((ROOT/'r394/loop_guard.lua').read_bytes()).hexdigest(),check.R394_PINS['r394/loop_guard.lua'])
        self.assertIn(hashlib.sha256((ROOT/'r394/review_r39410.py').read_bytes()).hexdigest(),(ROOT/'r394/check_inputs.py').read_text())
        self.assertEqual(check.prior.STAGE_DOCUMENT_PINS['frontend/document/pdfdocument.lua'],
          '963cbae1a42e5cb163361e89585a47ca2994477cac5741da743d314fa2b5fe60')
    def test_original_reviewers_unchanged(self):
        expected={'review_r394.py':'b2d7a44f1acedeb6ec9899074e91bb0f4d3a4fed63b15d0816ff9d7b99d51e57',
                  'review_r3945.py':'8e28fb054aacc0ed4999deafd6b909ce5d88791a7e32451ea0e66c7d2cd322e0',
                  'review_r3946.py':'58587bd90bf6bd56c626d39fdc5690775ac5cf8bed9a152ba69de369822d74ef',
                  'review_r3949.py':'d65e469d3bcdb368bdde527f85be7760d553215efaaf1877c00aa718ab7d8cf0'}
        for n,d in expected.items():
            self.assertEqual(hashlib.sha256((ROOT/'r394'/n).read_bytes()).hexdigest(),d)
    def test_r3949_actual_arm_fail_not_pass(self):
        f=Path('/mnt/data/R39.4.9-ARM-EVIDENCE.zip')
        if not f.is_file():self.skipTest('actual guest evidence not present')
        with zipfile.ZipFile(f) as z:
            a=self.fixture()
            a[0]=z.read('R394-EMULATION.log').decode()
            a[1]=json.loads(z.read('R394-R25-BASELINE-CONTROL.json'))
            a[2]=json.loads(z.read('R394-SOURCE-PREFLIGHT.json'))
            a[4]=json.loads(z.read('R394-REVIEW.json'))
        self.assertEqual(a[4]['verdict'],'FAIL')
        with self.assertRaisesRegex(ValueError,'source-pinned'):
            review(*a)
if __name__=='__main__':unittest.main()
