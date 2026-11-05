"""Synthetic-only R4043734 tests, never execute ELF, touch hardware or write original stage."""
import importlib.util
import io
from pathlib import Path
import struct
import tempfile
import unittest

PATH = Path(__file__).with_name('R4043734-FUTURE-MAPPING-SIMULATION-READONLY.py')
SPEC = importlib.util.spec_from_file_location('r3734', PATH)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def elf32(interp=None):
    hdr = bytearray(52)
    hdr[0:7] = b'\x7fELF\x01\x01\x01'
    struct.pack_into('<HHI', hdr, 16, 3, 40, 1)
    struct.pack_into('<I', hdr, 28, 52 if interp else 0)
    struct.pack_into('<HHH', hdr, 40, 52, 32, 1 if interp else 0)
    if interp is None:
        return bytes(hdr)
    ph = bytearray(32)
    struct.pack_into('<I', ph, 0, 3)
    struct.pack_into('<I', ph, 4, 84)
    struct.pack_into('<I', ph, 16, len(interp))
    return bytes(hdr) + bytes(ph) + interp


class TestPureSimulation(unittest.TestCase):
    def test_reaches_candidate(self):
        data = m.simulation('/lib/ld-demo.so', '/var/lib/private/app/ld-demo.so')
        self.assertTrue(data['purely_lexical_simulation_reaches_candidate'])
        self.assertEqual(data['relative_target_parent_ascents'], 1)
        self.assertFalse(data['mapping_applied'])

    def test_no_path_in_output(self):
        self.assertNotIn('ld-demo.so', str(m.simulation('/lib/ld-demo.so', '/var/lib/private/app/ld-demo.so')))

    def test_same_path_rejected(self):
        with self.assertRaises(m.Hold):
            m.simulation('/lib/ld.so', '/lib/ld.so')

    def test_different_basename_rejected(self):
        with self.assertRaises(m.Hold):
            m.simulation('/lib/ld.so', '/usr/lib/different.so')

    def test_dotdot_rejected(self):
        with self.assertRaises(m.Hold):
            m.simulation('/lib/../ld.so', '/usr/lib/ld.so')

    def test_invalid_nul_rejected(self):
        with self.assertRaises(m.Hold):
            m.simulation('/lib/ld.so\0', '/usr/lib/ld.so')

    def test_relative_rejected(self):
        with self.assertRaises(m.Hold):
            m.simulation('lib/ld.so', '/usr/lib/ld.so')

    def test_missing_parent_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(m.Hold) as e:
                m.no_symlink_parent(Path(tmp), '/absent/name')
            self.assertEqual(e.exception.category, 'GUEST_PARENT_MISSING_HOLD')

    def test_symlinked_parent_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'original').mkdir()
            (root/'link').symlink_to('original')
            with self.assertRaises(m.Hold) as e:
                m.no_symlink_parent(root, '/link/name')
            self.assertEqual(e.exception.category, 'GUEST_PARENT_LINK_OR_NONDIR_HOLD')

    def test_existing_leaf_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'lib').mkdir()
            (root/'lib/ld.so').write_bytes(b'present')
            with self.assertRaises(m.Hold) as e:
                m.absent_leaf(root, '/lib/ld.so')
            self.assertEqual(e.exception.category, 'GUEST_LEAF_ALREADY_PRESENT_HOLD')

    def test_absent_leaf_accept(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'lib').mkdir()
            self.assertTrue(m.absent_leaf(root, '/lib/ld.so'))

    def test_parent_sha_pin_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/m.R33).write_text('tampered')
            with self.assertRaises(m.Hold):
                m.import_r33(Path(tmp))

    def test_zero_writes_in_contract(self):
        result = m.simulation('/lib/ld.so','/var/lib/private/app/ld.so')
        self.assertEqual(result['future_image_mapping_kind'], 'RELATIVE_SYMLINK_PROPOSAL_ONLY')
        self.assertFalse(result['mapping_runtime_validated'])

    def test_one_component_alias_relative(self):
        d = m.simulation('/lib/ld.so', '/usr/lib/ld.so')
        self.assertEqual(d['relative_target_parent_ascents'], 1)

    def test_nested_common_parent_relative(self):
        d = m.simulation('/usr/local/lib/ld.so','/usr/lib/ld.so')
        self.assertEqual(d['relative_target_parent_ascents'], 2)


class TestFullSyntheticStage(unittest.TestCase):
    def test_83_19_12_7_one_alternative(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp)
            (r/'bin').mkdir(); (r/'lib').mkdir()
            (r/'var/lib/private/app').mkdir(parents=True)
            (r/'var/lib/private/app/ld-demo.so').write_bytes(elf32())
            (r/'lib/ld-ok.so').write_bytes(elf32())
            for i in range(12):
                pad = b'\0\0' if i>=2 else b''
                (r/'bin'/('missing-%02d' % i)).write_bytes(elf32(b'/lib/ld-demo.so\0'+pad))
            for i in range(7):
                (r/'bin'/('present-%02d' % i)).write_bytes(elf32(b'/lib/ld-ok.so\0'))
            for i in range(62):
                (r/'bin'/('plain-%02d' % i)).write_bytes(elf32())
            # 83 total synthetic ELF files, 1363 ordinary files -> 1446 regular.
            for i in range(1363):
                (r/('data-%04d' % i)).write_bytes(b'x')
            for i in range(335):
                (r/('link-%03d' % i)).symlink_to('missing-target')
            p33=m.import_r33(PATH.parent)
            out=m.audit(r, PATH.parent, p33)
            self.assertEqual(out['result'],'FUTURE_IMAGE_GUEST_ALIAS_SIMULATION_ONLY')
            self.assertEqual(out['source_interpreter_references'],12)
            self.assertEqual(out['relative_target_parent_ascents'],1)
            self.assertEqual(out['stage_file_writes'],0)
            self.assertFalse(out['boot_authorized'])
            self.assertFalse(out['mapping_applied'])
            self.assertFalse(out['future_image_mapping_approved'])
            self.assertNotIn('ld-demo.so',str(out))


if __name__ == '__main__':
    unittest.main()
