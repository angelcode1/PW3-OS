"""R39.4.11: third source-bound `ReaderUI:init` read, no host fixture is ARM proof."""
import unittest,hashlib,json,sys,zipfile,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'r394'))
from review_r39411 import review,THIRD_CTX,THIRD_GATE,THIRD_LOAD,SECOND_CTX,SECOND_GATE,SECOND_LOAD,TARGET,CLEAN
from review_r3945 import GATE as FIRST_GATE,LOADED as FIRST_LOAD
import test_r39_4_6 as oldfixture
spec=importlib.util.spec_from_file_location('check11',ROOT/'r394/check_inputs.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
class ThirdGenuineSidecarRead(unittest.TestCase):
    def fixture(self):
        a=oldfixture.StrictTwoCycle().fixture()
        a[2]['r39411_readerui_init_third_read_pinned']=True
        log=a[0]
        from review_r3948 import FIRST_CTX
        log=log.replace(FIRST_GATE,TARGET+'\n'+FIRST_CTX+'\n'+FIRST_GATE,1)
        log=log.replace('R39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED\n',
          'R39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED\n'+TARGET+'\n'+SECOND_CTX+'\n'+SECOND_GATE+'\n'+SECOND_LOAD+'\n',1)
        marker='R39_1_GENUINE_READERUI_INPUT_INHIBIT_REQUESTED_SYNTHETIC_ONLY'
        i=log.rfind(marker)
        assert i>=0
        i+=len(marker)
        log=log[:i]+'\n'+TARGET+'\n'+THIRD_CTX+'\n'+THIRD_GATE+'\n'+THIRD_LOAD+log[i:]
        log=log.replace('R39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY',
                        CLEAN+'\nR39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY',1)
        a[0]=log
        return a
    def test_fixture_only_host_pass(self):
        result=review(*self.fixture())
        self.assertEqual(result['verdict'],'R39_4_11_THREE_SOURCE_BOUND_READS_ARM_PASS')
        self.assertTrue(result['exact_generated_metadata_three_reads_and_two_write_opens_verified'])
        self.assertFalse(result['boot_authorized'])
    def reject(self,change,reason):
        a=self.fixture();change(a)
        with self.assertRaisesRegex(ValueError,reason):review(*a)
    def test_unpinned_source(self):self.reject(lambda a:a[2].__setitem__('r39411_readerui_init_third_read_pinned',False),'source-pinned')
    def test_original_strict_fails(self):self.reject(lambda a:a[4].__setitem__('verdict','FAIL'),'strict PASS')
    def test_independent_r25_fails(self):self.reject(lambda a:a[1].__setitem__('verdict','FAIL'),'R25 baseline')
    def test_no_third_context(self):self.reject(lambda a:a.__setitem__(0,a[0].replace(THIRD_CTX+'\n','')),'source-bound observations')
    def test_no_third_gate(self):self.reject(lambda a:a.__setitem__(0,a[0].replace(THIRD_GATE+'\n','')),'source-bound observations')
    def test_no_third_load(self):self.reject(lambda a:a.__setitem__(0,a[0].replace(THIRD_LOAD+'\n','')),'strict R39.4.11 marker')
    def test_third_context_false(self):self.reject(lambda a:a.__setitem__(0,a[0].replace('registered_second_document=true','registered_second_document=false')),'strict R39.4.11 marker')
    def test_third_wrong_caller(self):self.reject(lambda a:a.__setitem__(0,a[0].replace('readerui_init=true','readerui_init=false')),'strict R39.4.11 marker')
    def test_third_wrong_phase(self):self.reject(lambda a:a.__setitem__(0,a[0].replace('phase3=true','phase3=false')),'strict R39.4.11 marker')
    def test_third_not_regular(self):self.reject(lambda a:a.__setitem__(0,a[0].replace('regular_file=true phase3=true','regular_file=false phase3=true')),'strict R39.4.11 marker')
    def test_third_no_pcall(self):self.reject(lambda a:a.__setitem__(0,a[0].replace('c_pcall=true docsettings=true readerui_init','c_pcall=false docsettings=true readerui_init')),'strict R39.4.11 marker')
    def test_duplicate_third_marker(self):self.reject(lambda a:a.__setitem__(0,a[0].replace(THIRD_GATE,THIRD_GATE+'\n'+THIRD_GATE,1)),'source-bound observations')
    def test_duplicate_third_target(self):self.reject(lambda a:a.__setitem__(0,a[0]+'\n'+TARGET),'source-bound observations')
    def test_wrong_third_target(self):
        def f(a):
            index=a[0].rfind(TARGET)
            a[0]=a[0][:index]+TARGET.replace('exact_pdf_sidecar','other_temp_home')+a[0][index+len(TARGET):]
        self.reject(f,'exactly three original disposable')
    def test_missing_first_read(self):self.reject(lambda a:a.__setitem__(0,a[0].replace(FIRST_LOAD+'\n','')),'single fully verified sidecar load')
    def test_missing_pdfconstructor(self):self.reject(lambda a:a.__setitem__(0,a[0].replace(SECOND_LOAD+'\n','')),'strict R39.4.11 marker')
    def test_third_after_input_release(self):
        def f(a):
            chunk=TARGET+'\n'+THIRD_CTX+'\n'+THIRD_GATE+'\n'+THIRD_LOAD+'\n'
            a[0]=a[0].replace(chunk,'')
            marker='R39_1_GENUINE_READERUI_INPUT_RELEASE_REQUESTED_SYNTHETIC_ONLY'
            i=a[0].rfind(marker)+len(marker)
            a[0]=a[0][:i]+'\n'+chunk+a[0][i:]
        self.reject(f,'reordered')
    def test_third_before_input_inhibit(self):
        def f(a):
            chunk=TARGET+'\n'+THIRD_CTX+'\n'+THIRD_GATE+'\n'+THIRD_LOAD+'\n'
            a[0]=a[0].replace(chunk,'')
            marker='R39_1_GENUINE_READERUI_INPUT_INHIBIT_REQUESTED_SYNTHETIC_ONLY'
            i=a[0].rfind(marker)
            a[0]=a[0][:i]+chunk+a[0][i:]
        self.reject(f,'reordered')
    def test_denied_preserves_fail(self):self.reject(lambda a:a.__setitem__(0,a[0]+'\nR39_4_3_FIRST_DENIAL kind=DOFILE'),'denied|runtime')
    def test_original_strict_fails_if_final_close_missing(self):self.reject(lambda a:a.__setitem__(0,a[0].replace('R39_4_FINAL_CLOSE_SENT_TO_SECOND_FILEMANAGER','')),'missing/duplicate')
    def test_safety_bounds_in_guard(self):
        s=(ROOT/'r394/loop_guard.lua').read_text()
        for x in ('frame4.func==readerui.init','frame4.currentline==131','r3945_sidecar_loads==2 and r394_input_lifecycles==2',
                  'registered_second~=r394_first_doc','registered_second.is_open==true','registry:getReferenceCount(r39_pdf)==1',
                  'archived_first_engine_closed and original_readerui_init','from_real_readerui_init',
                  'from_returned_filemanager or from_pdfdocument_second_open or',
                  'r3945_sidecar_writes==2 and r3945_sidecar_loads==3',
                  "if path==r3945_sidecar then", "deny('DOFILE:'..tostring(path))"):
            self.assertIn(x,s)
        self.assertNotIn('stats.denied=0',s)
    def test_pins(self):
        self.assertEqual(hashlib.sha256((ROOT/'r394/loop_guard.lua').read_bytes()).hexdigest(),check.R394_PINS['r394/loop_guard.lua'])
        self.assertIn(hashlib.sha256((ROOT/'r394/review_r39411.py').read_bytes()).hexdigest(),(ROOT/'r394/check_inputs.py').read_text())
    def test_old_reviewers_untouched(self):
        hashes={'review_r394.py':'b2d7a44f1acedeb6ec9899074e91bb0f4d3a4fed63b15d0816ff9d7b99d51e57',
                'review_r3945.py':'8e28fb054aacc0ed4999deafd6b909ce5d88791a7e32451ea0e66c7d2cd322e0',
                'review_r3946.py':'58587bd90bf6bd56c626d39fdc5690775ac5cf8bed9a152ba69de369822d74ef',
                'review_r39410.py':'bb551fd506a0bee7f160d4fd72b62ffde04697a87409d046edcf191716d37fc6'}
        for name,d in hashes.items():self.assertEqual(hashlib.sha256((ROOT/'r394'/name).read_bytes()).hexdigest(),d)
    def test_actual_failed_r39410_not_upgraded(self):
        path=Path('/mnt/data/R39.4.10-ARM-EVIDENCE.zip')
        if not path.exists():self.skipTest('actual ARM archive not here')
        with zipfile.ZipFile(path) as z:
            a=self.fixture();a[0]=z.read('R394-EMULATION.log').decode();a[1]=json.loads(z.read('R394-R25-BASELINE-CONTROL.json'));a[2]=json.loads(z.read('R394-SOURCE-PREFLIGHT.json'));a[4]=json.loads(z.read('R394-REVIEW.json'))
        self.assertEqual(a[4]['verdict'],'FAIL')
        with self.assertRaisesRegex(ValueError,'source-pinned'):review(*a)
if __name__=='__main__':unittest.main()
