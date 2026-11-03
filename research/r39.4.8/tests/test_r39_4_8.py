"""R39.4.8 returned FM stays active while provider metadata is read."""
import hashlib,importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'r394'))
from review_r3948 import review,FIRST_CTX,SECOND_CTX
import test_r39_4_7 as parent
s=importlib.util.spec_from_file_location('check_r3948',ROOT/'r394/check_inputs.py')
check=importlib.util.module_from_spec(s);s.loader.exec_module(check)
class PhaseSpecificSidecar(unittest.TestCase):
    def fixture(self):
        state=parent.TwoDistinctSidecarReadPhases().fixture()
        state[2]['r3948_phase_specific_filemanager_pinned']=True
        state[0]=state[0].replace('R39_4_5_SIDECAR_GATE ',FIRST_CTX+'\nR39_4_5_SIDECAR_GATE ',1)
        state[0]=state[0].replace('R39_4_7_READERUI_SIDECAR_GATE ',SECOND_CTX+'\nR39_4_7_READERUI_SIDECAR_GATE ',1)
        return state
    def rejected(self,change,reason):
        data=self.fixture();change(data)
        with self.assertRaisesRegex(ValueError,reason):review(*data)
    def test_host_fixture_only_pass(self):
        out=review(*self.fixture())
        self.assertEqual(out['verdict'],'R39_4_8_FILEMANAGER_PHASE_BOUND_SIDECAR_ARM_PASS')
        self.assertFalse(out['boot_authorized'])
    def test_missing_new_source_pin(self):
        self.rejected(lambda a:a[2].__setitem__('r3948_phase_specific_filemanager_pinned',False),'source-pinned')
    def test_missing_first_context(self):
        self.rejected(lambda a:a.__setitem__(0,a[0].replace(FIRST_CTX+'\n','')),'state marker')
    def test_missing_second_context(self):
        self.rejected(lambda a:a.__setitem__(0,a[0].replace(SECOND_CTX+'\n','')),'state marker')
    def test_inactive_first_fm(self):
        self.rejected(lambda a:a.__setitem__(0,a[0].replace(FIRST_CTX,FIRST_CTX.replace('active=true','active=false'))),'marker')
    def test_not_present_first_fm(self):
        self.rejected(lambda a:a.__setitem__(0,a[0].replace(FIRST_CTX,FIRST_CTX.replace('present=true','present=false'))),'marker')
    def test_old_first_document_still_open(self):
        self.rejected(lambda a:a.__setitem__(0,a[0].replace(FIRST_CTX,FIRST_CTX.replace('first_document_released=true','first_document_released=false'))),'marker')
    def test_second_fm_not_closed(self):
        self.rejected(lambda a:a.__setitem__(0,a[0].replace(SECOND_CTX,SECOND_CTX.replace('fm_closed=true','fm_closed=false'))),'marker')
    def test_second_input_bad(self):
        self.rejected(lambda a:a.__setitem__(0,a[0].replace(SECOND_CTX,SECOND_CTX.replace('input_cycle2=true','input_cycle2=false'))),'marker')
    def test_duplicate_context(self):
        self.rejected(lambda a:a.__setitem__(0,a[0].replace(FIRST_CTX,FIRST_CTX+'\n'+FIRST_CTX,1)),'duplicate')
    def test_reordered_context(self):
        def change(a):
            a[0]=a[0].replace(SECOND_CTX+'\n','')
            a[0]=a[0].replace('R39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED',SECOND_CTX+'\nR39_4_GENUINE_FILEMANAGER_REOPEN_SCHEDULED')
        self.rejected(change,'reordered')
    def test_original_strict_failure_remains_failure(self):
        self.rejected(lambda a:a[4].__setitem__('verdict','FAIL'),'strict PASS')
    def test_any_denial_remains_failure(self):
        self.rejected(lambda a:a.__setitem__(0,a[0]+'R23_DENIED_DOFILE\n'),'denial|runtime error')
    def test_source_is_closed_phase_specific(self):
        source=(ROOT/'r394/loop_guard.lua').read_text()
        a=source.index('local returned_fm=real_fm and real_fm.instance')
        b=source.index('if r3945_sidecar_loads==0 then',a)
        phase=source[a:b]
        self.assertIn('returned_fm_active and r394_first_pdf_released()',phase)
        self.assertIn('real_fm.instance==nil and',phase)
        self.assertIn('fm_top.widget==returned_fm',phase)
        self.assertIn("returned_fm.file_chooser.path==home..'/library'",phase)
        self.assertIn('r3945_sidecar_loads==0',phase)
        self.assertIn('r3945_sidecar_loads==1',phase)
        self.assertNotIn('not r394_first_pdf_released()',phase)
        self.assertIn("deny('DOFILE:'..tostring(path))",source)
        self.assertNotIn('stats.denied=0',source)
    def test_new_source_hashes(self):
        self.assertEqual(hashlib.sha256((ROOT/'r394/loop_guard.lua').read_bytes()).hexdigest(),check.R394_PINS['r394/loop_guard.lua'])
        self.assertIn(hashlib.sha256((ROOT/'r394/review_r3948.py').read_bytes()).hexdigest(),(ROOT/'r394/check_inputs.py').read_text())
    def test_old_reviewers_unchanged(self):
        for name,digest in {'review_r394.py':'b2d7a44f1acedeb6ec9899074e91bb0f4d3a4fed63b15d0816ff9d7b99d51e57',
                            'review_r3945.py':'8e28fb054aacc0ed4999deafd6b909ce5d88791a7e32451ea0e66c7d2cd322e0',
                            'review_r3946.py':'58587bd90bf6bd56c626d39fdc5690775ac5cf8bed9a152ba69de369822d74ef',
                            'review_r3947.py':'07e116b0c26f84bb3ef218b9dd80b09bfede3cfe1e0a3018fbaecb47e4f09e73'}.items():
            self.assertEqual(hashlib.sha256((ROOT/'r394'/name).read_bytes()).hexdigest(),digest)
if __name__=='__main__':unittest.main()
