"""R39.4.6 strict source and timeline regressions; no synthetic ARM PASS claims."""
import hashlib,sys,unittest,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'r394'))
from review_r3946 import review,FIRST,SECOND
import test_r39_4_5 as prior_mod
spec=importlib.util.spec_from_file_location('checker_r3946',ROOT/'r394/check_inputs.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
class StrictTwoCycle(unittest.TestCase):
    def fixture(self):
        x=prior_mod.Contract().fixture()
        x[2]['r3946_two_home_sidecar_write_pinned']=True
        x[0]=x[0].replace('R39_3_GENUINE_FILEMANAGER_RETURNED_AFTER_HOME',FIRST+'\nR39_3_GENUINE_FILEMANAGER_RETURNED_AFTER_HOME')
        x[0]=x[0].replace('R39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY',SECOND+'\nR39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY')
        return x
    def test_positive(self):
        x=review(*self.fixture())
        self.assertEqual(x['verdict'],'R39_4_6_TWO_CYCLE_SIDECAR_REOPEN_ARM_PASS')
        self.assertTrue(x['independent_strict_r394_and_r3945_reviewers_pass'])
        self.assertFalse(x['boot_authorized'])
    def must_fail(self,transform,pattern):
        x=self.fixture()
        transform(x)
        with self.assertRaisesRegex(ValueError,pattern):review(*x)
    def test_missing_first_write(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0].replace(FIRST+'\n','')),'missing/duplicate')
    def test_missing_second_write(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0].replace(SECOND+'\n','')),'missing/duplicate')
    def test_duplicate_first_write(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0].replace(FIRST,FIRST+'\n'+FIRST)),'missing/duplicate')
    def test_duplicate_second_write(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0].replace(SECOND,SECOND+'\n'+SECOND)),'missing/duplicate')
    def test_first_write_before_home(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0].replace(FIRST+'\n','').replace('R39_3_HOME_SENT_THROUGH_REAL_UIMANAGER_INPUT',FIRST+'\nR39_3_HOME_SENT_THROUGH_REAL_UIMANAGER_INPUT')),'out of order')
    def test_first_write_after_return(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0].replace(FIRST+'\n','').replace('R39_4_REOPEN_REQUESTED_FROM_RETURNED_FILEMANAGER',FIRST+'\nR39_4_REOPEN_REQUESTED_FROM_RETURNED_FILEMANAGER')),'out of order')
    def test_second_write_before_second_home(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0].replace(SECOND+'\n','').replace('R39_4_SECOND_HOME_SENT_THROUGH_REAL_UIMANAGER_INPUT',SECOND+'\nR39_4_SECOND_HOME_SENT_THROUGH_REAL_UIMANAGER_INPUT')),'out of order')
    def test_second_write_after_engine_close(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0].replace(SECOND+'\n','').replace('R39_4_FINAL_CLOSE_SENT_TO_SECOND_FILEMANAGER',SECOND+'\nR39_4_FINAL_CLOSE_SENT_TO_SECOND_FILEMANAGER')),'out of order')
    def test_failed_old_strict(self):
        self.must_fail(lambda x:x[4].__setitem__('verdict','FAIL'),'strict PASS')
    def test_unpinned(self):
        self.must_fail(lambda x:x[2].__setitem__('r3946_two_home_sidecar_write_pinned',False),'source pins')
    def test_sidecar_gate_not_verified(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0].replace('cycle2=true','cycle2=false')),'single fully verified')
    def test_sidecar_load_missing(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0].replace('R39_4_5_GENUINE_DOCSETTINGS_SIDECAR_LOADED_FROM_FIRST_CYCLE\n','')),'single fully verified')
    def test_denied_read(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0]+'R23_DENIED_DOFILE\n'),'denial|runtime error')
    def test_denied_write(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0]+'R23_DENIED_SIDECAR_WRITE_PROVENANCE\n'),'denial|runtime error')
    def test_extra_home(self):
        self.must_fail(lambda x:x.__setitem__(0,x[0]+'R39_4_SECOND_HOME_SENT_THROUGH_REAL_UIMANAGER_INPUT\n'),'duplicate')
    def test_source_guard_first_doc_archive(self):
        s=(ROOT/'r394/loop_guard.lua').read_text()
        self.assertIn('local function r394_first_pdf_released()',s)
        self.assertIn('r394_first_doc.is_open==false',s)
        self.assertIn("rawget(r394_first_doc,'_document')==nil",s)
        self.assertIn('r394_first_reader.document==nil',s)
        self.assertIn('r394_first_pdf_released()',s)
        self.assertIn('registry:getReferenceCount(r39_pdf)==nil',s)
        self.assertNotIn('r3945_sidecar_writes==1 and r3933_pdf_engine_released()',s)
    def test_narrow_writes(self):
        s=(ROOT/'r394/loop_guard.lua').read_text()
        for v in ("path==r3945_sidecar", "mode=='wb'", "caller.func==util.writeToFile", "caller.currentline==1147", 'r3945_sidecar_writes==0','r3945_sidecar_writes==1','r3945_sidecar_loads==1','r394_second_home_sent','r394_second_scroll_returned','r394_input_lifecycles==2',"deny('SIDECAR_WRITE_PROVENANCE')", 'stats.denied==0','r3945_sidecar_writes==2 and r3945_sidecar_loads==3'):
            self.assertIn(v,s)
        self.assertNotIn('stats.denied=0',s)
    def test_reader_is_only_one_source_identity(self):
        s=(ROOT/'r394/loop_guard.lua').read_text()
        for v in ('frame2.func==pcall','frame3.func==docsettings.open','frame3.currentline==276','lfs.symlinkattributes', 'r3945_sidecar_loads==0', 'stats.events==2', 'stats.filemanager==2', 'r394_cycle==2'):
            self.assertIn(v,s)
    def test_original_strict_hashes_preserved(self):
        self.assertEqual(hashlib.sha256((ROOT/'r394/review_r394.py').read_bytes()).hexdigest(),'b2d7a44f1acedeb6ec9899074e91bb0f4d3a4fed63b15d0816ff9d7b99d51e57')
        self.assertEqual(hashlib.sha256((ROOT/'r394/review_r3945.py').read_bytes()).hexdigest(),'8e28fb054aacc0ed4999deafd6b909ce5d88791a7e32451ea0e66c7d2cd322e0')
        for name,sha in checker.R394_PINS.items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),sha)
    def test_new_reviewer_hash_pinned(self):
        text=(ROOT/'r394/check_inputs.py').read_text()
        self.assertIn(hashlib.sha256((ROOT/'r394/review_r3946.py').read_bytes()).hexdigest(),text)
    def test_independent_r25_untouched(self):
        self.assertEqual(checker.prior.GUARD,'7f5881a9c79da22c626bd0451a580fd13eae8af96330de811a13042cd98ed2b8')
    def test_no_boot_ever(self):
        v=review(*self.fixture())
        for key in ('boot_authorized','device_access_authorized','firmware_write_authorized','hardware_write_authorized','file_removal_authorized'):
            self.assertFalse(v[key])
        self.assertEqual(v['immutable_hold'],'NOT_BOOTABLE')
if __name__=='__main__':unittest.main()
