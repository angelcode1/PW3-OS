"""R3745.2 synthetic-only regression tests: pin, original failure and corrected call chain."""
from collections import Counter
import hashlib
import importlib.util
from pathlib import Path
from unittest.mock import patch
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
NAME='R4043745-2-PINNED-PLT-CALLCHAIN-FIX-READONLY.py'
spec=importlib.util.spec_from_file_location('r3745_2_fixed_test',HERE/NAME)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
spec0=importlib.util.spec_from_file_location('r3745_original_test',HERE/m.ORIGINAL_R3745)
original=importlib.util.module_from_spec(spec0);spec0.loader.exec_module(original)

BASELINE={'result':'WEAK_RELOCATION_SLOT_STORAGE_STATIC_ONLY',
          'weak_reference_symbol_group_counts':{
              'LOCAL_ZERO_NAME_IN_SIX':9,'LOCAL_ZERO_NAME_NOT_IN_SIX':33,
              'UNVERSIONED_WEAK_NAME_NOT_IN_SIX':2},
          'weak_relocation_site_total':62,'requester_now_policy_objects':0,
          'requester_relocation_sites_reverified':3499}
GROUP_A='LOCAL_ZERO_NAME_IN_SIX'; GROUP_B='LOCAL_ZERO_NAME_NOT_IN_SIX'; GROUP_C='UNVERSIONED_WEAK_NAME_NOT_IN_SIX'

class Original43:
    def __init__(self, mark):self.mark=mark
    def load_pinned_parent(self, folder):
        self.mark.append('R3743_original.load_pinned_parent')
        return R42(self.mark)
class R43_1:
    def __init__(self,mark):self.mark=mark
    def load_original(self,folder):
        self.mark.append('R3743_1.load_original')
        return Original43(self.mark)
class R42:
    def __init__(self,mark):self.mark=mark
    def load_parent(self,folder):
        self.mark.append('R3742.load_parent');return R11(self.mark)
class R11:
    def __init__(self,mark):self.mark=mark
    def load_original(self,folder):
        self.mark.append('R3741_1.load_original');return R41(self.mark)
class R41:
    def __init__(self,mark):self.mark=mark
    def load_parent(self,folder):
        self.mark.append('R3741.load_parent');return object()
    def locate_sources_providers(self,root,folder,p40):
        self.mark.append('R3741.locate_sources_providers')
        return object(),[Path('src'+str(i)) for i in range(12)],[Path('prv'+str(i)) for i in range(6)]
    def parse_version_file(self,p26,p40,path):
        return {'mock_path':path.name,'symbols':[], 'versym':[], 'referenced_indices':set()}
class Parent44:
    def __init__(self):self.mark=[]
    def audit(self,root,folder,arg):return dict(BASELINE)
    def import_pinned(self,folder):
        self.mark.append('R3744.import_pinned');return R43_1(self.mark)


def fake_reader(p26,parent,path,target_groups):
    i=int(path.name[3:]); rows={}
    if i<9:rows[GROUP_A]=Counter({('WORD','ORIGINAL_WORD_IN_OWN_EXEC_PT_LOAD'):1,('LOW_BIT','LOW_BIT_CLEAR'):1})
    elif i in (9,10):
        n=3 if i==9 else 4
        rows[GROUP_B]=Counter({('WORD','ORIGINAL_WORD_OUTSIDE_OWN_PT_LOAD'):n,('LOW_BIT','LOW_BIT_SET'):n})
    elif i==11:rows[GROUP_C]=Counter({('WORD','ORIGINAL_WORD_IN_OWN_NONEXEC_PT_LOAD'):2,('LOW_BIT','LOW_BIT_CLEAR'):2})
    return rows,'DT_PLTGOT_ABSENT',sum(val for groups in rows.values() for (kind,_),val in groups.items() if kind=='WORD')

class PinIntegrity(unittest.TestCase):
    def test_historical_script_sha(self):
        self.assertEqual(hashlib.sha256((HERE/m.ORIGINAL_R3745).read_bytes()).hexdigest(),m.ORIGINAL_R3745_SHA256)
    def test_original_verifier_passes(self):self.assertTrue(m.verify_original_r3745(HERE))
    def test_original_symlink_refused(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/m.ORIGINAL_R3745).symlink_to(HERE/m.ORIGINAL_R3745)
            with self.assertRaises(m.Hold):m.verify_original_r3745(Path(t))
    def test_modified_original_refused(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t)/m.ORIGINAL_R3745).write_bytes(b'tampered')
            with self.assertRaises(m.Hold):m.verify_original_r3745(Path(t))
    def test_original_missing_refused(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(m.Hold):m.verify_original_r3745(Path(t))
    def test_pinned_r3744_parent_integrity(self):
        self.assertEqual(hashlib.sha256((HERE/m.PARENT).read_bytes()).hexdigest(),m.PARENT_SHA256)
    def test_r3744_import(self):self.assertTrue(callable(m.load_parent(HERE).audit))
    def test_only_corrected_call_site(self):
        original_source=(HERE/m.ORIGINAL_R3745).read_text()
        fixed=(HERE/NAME).read_text()
        self.assertIn('p42=p43.load_pinned_parent(folder)',original_source)
        self.assertNotIn('p42=p43.load_pinned_parent(folder)',fixed)
        self.assertIn('original43=p43.load_original(folder)',fixed)
        self.assertIn('p42=original43.load_pinned_parent(folder)',fixed)

class CorrectedChain(unittest.TestCase):
    def run_new(self):
        with tempfile.TemporaryDirectory() as t:
            p=Parent44()
            with patch.object(m,'read_weak_plt_words',side_effect=fake_reader):
                out=m.audit(Path(t),Path(t),p)
            return out,p.mark
    def test_original_error_reproduced(self):
        with tempfile.TemporaryDirectory() as t:
            p=Parent44()
            with self.assertRaises(AttributeError) as cm:
                original.audit(Path(t),Path(t),p)
            self.assertIn('load_pinned_parent',str(cm.exception))
    def test_corrected_audit_success(self):
        out,_=self.run_new()
        self.assertEqual(out['result'],'WEAK_PLT_INITIAL_WORD_GEOMETRY_PINNED_PARENT_CHAIN_CORRECTED_STATIC_ONLY')
    def test_corrected_parent_uses_original_3743(self):
        _,mark=self.run_new()
        self.assertEqual(mark[:4],['R3744.import_pinned','R3744.import_pinned','R3743_1.load_original','R3743_original.load_pinned_parent'])
    def test_corrected_parent_descends_other_pins(self):
        _,mark=self.run_new()
        self.assertEqual(mark[4:],['R3742.load_parent','R3741_1.load_original','R3741.load_parent','R3741.locate_sources_providers'])
    def test_plt_site_count(self):self.assertEqual(self.run_new()[0]['targeted_weak_plt_sites'],18)
    def test_original_evidence_hold_preserved(self):self.assertTrue(self.run_new()[0]['original_r3745_sha_pinned_and_original_hold_preserved'])
    def test_unchanged_pinned_stage_gate(self):
        with tempfile.TemporaryDirectory() as t:
            p=Parent44()
            p.audit=lambda *x:{'result':'HOLD'}
            with self.assertRaises(m.Hold) as exc:m.audit(Path(t),Path(t),p)
            self.assertEqual(exc.exception.category,'R3744_BASELINE_HOLD')
    def test_no_boot(self):
        result,_=self.run_new()
        self.assertFalse(result['boot_authorized'])
        self.assertEqual(result['immutable_hold'],'NOT_BOOTABLE')
    def test_no_prune(self):self.assertFalse(self.run_new()[0]['prune_authorized'])
    def test_no_firmware_write(self):self.assertFalse(self.run_new()[0]['firmware_write_authorized'])
    def test_no_stage_modified(self):self.assertFalse(self.run_new()[0]['original_stage_modified'])
    def test_no_mapping(self):self.assertFalse(self.run_new()[0]['mapping_applied'])
    def test_no_loader_verified(self):self.assertFalse(self.run_new()[0]['weak_symbol_runtime_semantics_verified'])
    def test_no_private_names_in_output(self):
        result,_=self.run_new();self.assertNotIn('src0',str(result));self.assertNotIn('prv0',str(result))

if __name__=='__main__':unittest.main()
