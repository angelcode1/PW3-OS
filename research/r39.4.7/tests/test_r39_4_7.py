"""R39.4.7: distinct FileManager and ReaderUI metadata read source contracts."""
import hashlib,sys,unittest,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'r394'))
from review_r3947 import review,FIRST_GATE,FIRST_LOAD,SECOND_GATE,SECOND_LOAD,TARGET,CLEAN
import test_r39_4_6 as previous
spec=importlib.util.spec_from_file_location('check_r3947',ROOT/'r394/check_inputs.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)

class TwoDistinctSidecarReadPhases(unittest.TestCase):
    def fixture(self):
        original=previous.StrictTwoCycle().fixture()
        log,base,pins,prior,strict=original
        pins['r3947_two_source_bound_sidecar_reads_pinned']=True
        log=log.replace(FIRST_GATE,TARGET+'\n'+FIRST_GATE)
        log=log.replace('R39_1_GENUINE_READERUI_INPUT_RELEASE_REQUESTED_SYNTHETIC_ONLY\nR39_4_SECOND_GENUINE_PDF_SCROLL_DRAW_RETURNED',
                        TARGET+'\n'+SECOND_GATE+'\n'+SECOND_LOAD+'\nR39_1_GENUINE_READERUI_INPUT_RELEASE_REQUESTED_SYNTHETIC_ONLY\nR39_4_SECOND_GENUINE_PDF_SCROLL_DRAW_RETURNED')
        log=log.replace('R39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY',CLEAN+'\nR39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY')
        return [log,base,pins,prior,strict]

    def test_strict_positive_on_synthetic_fixture_only(self):
        result=review(*self.fixture())
        self.assertEqual(result['verdict'],'R39_4_7_TWO_SOURCE_BOUND_READS_ARM_PASS')
        self.assertFalse(result['boot_authorized'])
        self.assertTrue(result['final_genuine_filemanager_close_verified'])

    def fails(self,transform,reason):
        state=self.fixture();transform(state)
        with self.assertRaisesRegex(ValueError,reason): review(*state)

    def test_no_new_pin(self):
        self.fails(lambda x:x[2].__setitem__('r3947_two_source_bound_sidecar_reads_pinned',False),'source hashes')

    def test_failed_original_strict_review(self):
        self.fails(lambda x:x[4].__setitem__('verdict','FAIL'),'strict PASS')

    def test_failed_baseline(self):
        self.fails(lambda x:x[1].__setitem__('verdict','FAIL'),'baseline')

    def test_single_read_rejected(self):
        self.fails(lambda x:x.__setitem__(0,x[0].replace(SECOND_GATE+'\n'+SECOND_LOAD+'\n','')),'second read gate')

    def test_second_gate_wrong_callsite(self):
        self.fails(lambda x:x.__setitem__(0,x[0].replace('readerui_init=true','readerui_init=false')),'strict R39.4.7 marker')

    def test_second_gate_bad_phase(self):
        self.fails(lambda x:x.__setitem__(0,x[0].replace('phase2=true','phase2=false')),'strict R39.4.7 marker')

    def test_second_gate_c_pcall_unverified(self):
        self.fails(lambda x:x.__setitem__(0,x[0].replace(SECOND_GATE,SECOND_GATE.replace('c_pcall=true','c_pcall=false'))),'strict R39.4.7 marker')

    def test_second_load_not_completed(self):
        self.fails(lambda x:x.__setitem__(0,x[0].replace(SECOND_LOAD+'\n','')),'missing/duplicate')

    def test_duplicate_second_read(self):
        self.fails(lambda x:x.__setitem__(0,x[0].replace(SECOND_GATE,SECOND_GATE+'\n'+SECOND_GATE)),'second read gate')

    def test_wrong_target(self):
        self.fails(lambda x:x.__setitem__(0,x[0].replace(TARGET,TARGET.replace('exact_pdf_sidecar','other_temp_home'),1)),'two exact')

    def test_third_read_attempt(self):
        self.fails(lambda x:x.__setitem__(0,x[0]+'\n'+TARGET),'two exact')

    def test_missing_source_target(self):
        self.fails(lambda x:x.__setitem__(0,x[0].replace(TARGET+'\n','',1)),'two exact')

    def test_early_readerui_sidecar(self):
        def change(x):
            x[0]=x[0].replace(TARGET+'\n'+SECOND_GATE+'\n'+SECOND_LOAD+'\n','')
            x[0]=x[0].replace('R39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED',TARGET+'\n'+SECOND_GATE+'\n'+SECOND_LOAD+'\nR39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED')
        self.fails(change,'reordered')

    def test_late_sidecar_after_render(self):
        def change(x):
            x[0]=x[0].replace(TARGET+'\n'+SECOND_GATE+'\n'+SECOND_LOAD+'\n','')
            x[0]=x[0].replace('R39_4_DISTINCT_READERUI_AND_PDF_DOCUMENT_REOPENED',TARGET+'\n'+SECOND_GATE+'\n'+SECOND_LOAD+'\nR39_4_DISTINCT_READERUI_AND_PDF_DOCUMENT_REOPENED')
        self.fails(change,'reordered')

    def test_second_fm_not_active(self):
        self.fails(lambda x:x.__setitem__(0,x[0].replace('denied_zero=true','denied_zero=false')),'missing/duplicate')

    def test_denied_operation_blocked(self):
        self.fails(lambda x:x.__setitem__(0,x[0]+'R23_DENIED_DOFILE\n'),'denial|runtime error')

    def test_source_no_general_lua_whitelist(self):
        source=(ROOT/'r394/loop_guard.lua').read_text()
        for anchor in ("path==r3945_sidecar", "frame2.func==pcall", "frame3.func==docsettings.open",
                       "frame3.currentline==276", "frame4.func==readerui.init", "frame4.currentline==131",
                       "readerui%.lua", "r3945_sidecar_loads==0", "r3945_sidecar_loads==1",
                       "r3945_sidecar_loads==2", "r394_input_lifecycles==2",
                       "r39_input_inhibit==1", "r39_input_until==0", "real_fm.instance==nil",
                       "r394_first_doc.is_open==false", "r394_first_reader.document==nil",
                       "r394_second_home_sent", "deny('DOFILE:'..tostring(path))",
                       'r3945_sidecar_writes==2 and r3945_sidecar_loads==2'):
            self.assertIn(anchor,source)
        self.assertNotIn('stats.denied=0',source)
        self.assertIn("if path==r3945_sidecar then",source)
        self.assertNotIn('return native_dofile(path) -- any',source)

    def test_pinned_source_and_unchanged_original_reviewers(self):
        self.assertEqual(hashlib.sha256((ROOT/'r394/loop_guard.lua').read_bytes()).hexdigest(),
                         check.R394_PINS['r394/loop_guard.lua'])
        old={'review_r394.py':'b2d7a44f1acedeb6ec9899074e91bb0f4d3a4fed63b15d0816ff9d7b99d51e57',
             'review_r3945.py':'8e28fb054aacc0ed4999deafd6b909ce5d88791a7e32451ea0e66c7d2cd322e0',
             'review_r3946.py':'58587bd90bf6bd56c626d39fdc5690775ac5cf8bed9a152ba69de369822d74ef'}
        for name,digest in old.items():
            self.assertEqual(hashlib.sha256((ROOT/'r394'/name).read_bytes()).hexdigest(),digest)
        self.assertIn(hashlib.sha256((ROOT/'r394/review_r3947.py').read_bytes()).hexdigest(),
                      (ROOT/'r394/check_inputs.py').read_text())

    def test_original_r25_baseline_guard_untouched(self):
        self.assertEqual(check.prior.GUARD,'7f5881a9c79da22c626bd0451a580fd13eae8af96330de811a13042cd98ed2b8')

if __name__=='__main__':unittest.main()
