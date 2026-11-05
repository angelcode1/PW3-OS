"""Host-only synthetic tests; no Kindle or private stage required."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

PATH = Path(__file__).with_name('R4043733-INTERP-LAYOUT-READONLY.py')
spec = importlib.util.spec_from_file_location('pw3_r3733_tests', PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class TestLayout(unittest.TestCase):
    def test_different_parent(self):
        d = m.classify_layout('/lib/loader.so', '/usr/lib/loader.so')
        self.assertEqual(d['missing_parent_vs_candidate_parent'], 'DIFFERENT_PARENT_DIRECTORY')
    def test_same_parent_rejected_identical(self):
        with self.assertRaises(m.Hold):
            m.classify_layout('/lib/loader.so', '/lib/loader.so')
    def test_default_no_private_strings(self):
        payload = json.dumps(m.classify_layout('/lib/loader.so', '/usr/lib/loader.so'))
        self.assertNotIn('loader.so', payload)
        self.assertNotIn('/usr/lib', payload)
    def test_explicit_local_paths(self):
        d = m.classify_layout('/lib/loader.so', '/usr/lib/loader.so', show_local_paths=True)
        self.assertEqual(d['missing_interpreter_guest_path'], '/lib/loader.so')
        self.assertEqual(d['alternative_candidate_guest_path'], '/usr/lib/loader.so')
    def test_basename_mismatch(self):
        with self.assertRaises(m.Hold) as e:
            m.classify_layout('/lib/loader.so', '/usr/lib/another.so')
        self.assertEqual(e.exception.code, 'BASENAME_DIFFERENT_HOLD')
    def test_dotdot_holds(self):
        with self.assertRaises(m.Hold):
            m.classify_layout('/lib/../loader.so', '/usr/lib/loader.so')
    def test_embedded_nul_holds(self):
        with self.assertRaises(m.Hold):
            m.classify_layout('/lib/loader.so\x00x', '/usr/lib/loader.so')
    def test_relative_holds(self):
        with self.assertRaises(m.Hold):
            m.classify_layout('lib/loader.so', '/usr/lib/loader.so')
    def test_relative_guest_path(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d)
            self.assertEqual(m.relative_guest_path(r, r/'usr/lib/loader.so'), '/usr/lib/loader.so')
    def test_outside_stage_holds(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.Hold):
                m.relative_guest_path(Path(d), Path('/tmp/elsewhere'))
    def test_malformed_parent_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(m.Hold) as e:
                m.import_parent(Path(d) / m.R3727, m.R3727)
            self.assertEqual(e.exception.code, 'PARENT_INVALID_HOLD')
    def test_wrong_source_pin_refused(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/m.R3726
            file.write_text('tampered')
            with self.assertRaises(m.Hold) as e:
                m.import_parent(file,m.R3726)
            self.assertEqual(e.exception.code,'PARENT_SHA_MISMATCH_HOLD')
    def test_alias_action_unauthorized(self):
        d = m.classify_layout('/lib/loader.so','/usr/lib/loader.so',show_local_paths=True)
        self.assertFalse(d['alias_creation_authorized'])
        self.assertTrue(d['requested_guest_path_still_absent'])
    def test_common_parent_prefix(self):
        d=m.classify_layout('/usr/lib/loader.so','/usr/local/lib/loader.so')
        self.assertEqual(d['common_parent_components'],1)
        self.assertEqual(d['missing_parent_component_count'],2)
        self.assertEqual(d['candidate_parent_component_count'],3)

if __name__ == '__main__':
    unittest.main()
