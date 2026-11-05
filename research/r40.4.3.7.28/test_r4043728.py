"""Read-only synthetic-only tests; no physical device or real staged files."""
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest

FOLDER = Path(__file__).parent
SCRIPT = FOLDER / 'R4043728-INTERP-PATH-TOPOLOGY-READONLY.py'
spec = importlib.util.spec_from_file_location('pw3r3728', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def elf32(interp=None, padded=False, load=False, machine=40):
    interp = interp.encode('ascii') + b'\0' + (b'\0\0' if padded else b'') if interp else b''
    hdr = bytearray(52)
    hdr[:7] = b'\x7fELF\x01\x01\x01'
    struct.pack_into('<HH', hdr, 16, 3, machine)
    struct.pack_into('<I', hdr, 28, 52 if (interp or load) else 0)
    struct.pack_into('<HHH', hdr, 40, 52, 32, int(bool(interp or load)))
    if interp:
        ph = bytearray(32)
        struct.pack_into('<I', ph, 0, 3)
        struct.pack_into('<I', ph, 4, 84)
        struct.pack_into('<I', ph, 16, len(interp))
        return bytes(hdr + ph + interp)
    if load:
        ph = bytearray(32)
        struct.pack_into('<I', ph, 0, 1)
        struct.pack_into('<I', ph, 4, 0)
        struct.pack_into('<I', ph, 16, 84)
        struct.pack_into('<I', ph, 20, 84)
        return bytes(hdr + ph)
    return bytes(hdr)


class TestParents(unittest.TestCase):
    def test_pin_matches_real_R3727_source(self):
        mod = m.load_pinned_r3727(FOLDER / m.PARENT27_NAME)
        self.assertEqual(mod.PARENT_SHA256, '7068af571b0c57677793eb5722938b3a4f14abfd5ce33c6b4e4ce41040e117b3')

    def test_parent26_checksum_chain(self):
        mod = m.load_pinned_r3727(FOLDER / m.PARENT27_NAME)
        second = mod.verify_parent(FOLDER / mod.PARENT_BASENAME)
        self.assertTrue(hasattr(second, 'resolve_guest'))

    def test_tamper_hold(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / m.PARENT27_NAME
            p.write_bytes(b'fake')
            with self.assertRaises(m.Hold) as err:
                m.load_pinned_r3727(p)
            self.assertEqual(err.exception.category, 'R3727_SHA_MISMATCH')

    def test_symlinked_source_hold(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'source').write_bytes(b'fake')
            (root / m.PARENT27_NAME).symlink_to('source')
            with self.assertRaises(m.Hold):
                m.load_pinned_r3727(root / m.PARENT27_NAME)


class TestParentTopo(unittest.TestCase):
    def test_parent_directory_present(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'lib').mkdir()
            self.assertEqual(m.guest_parent_status(root,'/lib/missing.so'), ('PARENT_DIRECTORY_PRESENT',0))

    def test_parent_absent(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(m.guest_parent_status(Path(d),'/lib/missing.so')[0], 'PARENT_DIRECTORY_COMPONENT_ABSENT')

    def test_parent_empty_root(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(m.guest_parent_status(Path(d),'/loader.so'), ('PARENT_DIRECTORY_PRESENT',0))

    def test_symlink_directory_no_host_escape(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'usr/lib').mkdir(parents=True)
            (root/'lib').symlink_to('/usr/lib')
            self.assertEqual(m.guest_parent_status(root,'/lib/missing.so'), ('PARENT_DIRECTORY_PRESENT',1))

    def test_parent_symlink_cycle(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'a').symlink_to('b')
            (root/'b').symlink_to('a')
            self.assertEqual(m.guest_parent_status(root,'/a/missing.so',3)[0], 'PARENT_SYMLINK_LIMIT_HOLD')

    def test_parent_symlink_dangling(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'a').symlink_to('not-found')
            self.assertEqual(m.guest_parent_status(root,'/a/missing.so')[0], 'PARENT_DIRECTORY_COMPONENT_ABSENT')

    def test_non_dir_parent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'dir').write_text('not directory')
            self.assertEqual(m.guest_parent_status(root,'/dir/loader.so')[0], 'PARENT_NON_DIRECTORY_COMPONENT_HOLD')

    def test_escape(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'dir').symlink_to('../../private')
            self.assertEqual(m.guest_parent_status(root,'/dir/loader.so')[0], 'PARENT_GUEST_ESCAPE_HOLD')

    def test_invalid_guest_path(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(m.guest_parent_status(Path(d),'relative/file')[0],'PARENT_INVALID_PATH_HOLD')
            self.assertEqual(m.guest_parent_status(Path(d),'/../file')[0],'PARENT_INVALID_PATH_HOLD')


class TestCandidate(unittest.TestCase):
    def test_structural_pt_load(self):
        with tempfile.TemporaryDirectory() as d:
            r = Path(d)
            loader = r/'candidate'
            loader.write_bytes(elf32(load=True))
            r27=m.load_pinned_r3727(FOLDER / m.PARENT27_NAME)
            r26=r27.verify_parent(FOLDER / r27.PARENT_BASENAME)
            s=m.candidate_elf_structure(r26,loader)
            self.assertEqual(s,{'elf_type':'ET_DYN','pt_load_segments':1,'pt_interp_segments':0,'has_loadable_segment':True})

    def test_bad_pt_load_bounds(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            bad=bytearray(elf32(load=True))
            struct.pack_into('<I', bad, 52+16, 2000)
            p=root/'bad'
            p.write_bytes(bad)
            r27=m.load_pinned_r3727(FOLDER / m.PARENT27_NAME)
            r26=r27.verify_parent(FOLDER / r27.PARENT_BASENAME)
            with self.assertRaises(m.Hold) as err:
                m.candidate_elf_structure(r26,p)
            self.assertEqual(err.exception.category,'CANDIDATE_PT_LOAD_BOUNDS_HOLD')

    def test_nonelf_candidate(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=root/'foo'
            p.write_bytes(b'plaintext')
            r27=m.load_pinned_r3727(FOLDER / m.PARENT27_NAME)
            r26=r27.verify_parent(FOLDER / r27.PARENT_BASENAME)
            with self.assertRaises(m.Hold):
                m.candidate_elf_structure(r26,p)

    def test_full_synthetic_replay(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'bin').mkdir()
            (root/'lib').mkdir()
            (root/'usr/lib').mkdir(parents=True)
            (root/'lib/ld-working.so').write_bytes(elf32(load=True))
            (root/'usr/lib/ld-missing.so').write_bytes(elf32(load=True))
            for i in range(19):
                missing=i>=7
                path='/lib/ld-missing.so' if missing else '/lib/ld-working.so'
                (root/'bin'/('app-%03d'%i)).write_bytes(elf32(interp=path,padded=i>=9))
            for i in range(62):
                (root/'bin'/('node-%03d'%i)).write_bytes(elf32())
            # Two loaders + 19 interpreter-bearing ELFs + 62 non-interpreter ELFs = 83.
            for i in range(1446-83):
                (root/('doc-%04d'%i)).write_bytes(b'file')
            for i in range(335):
                (root/('link-%03d'%i)).symlink_to('bin/app-000')
            r27=m.load_pinned_r3727(FOLDER / m.PARENT27_NAME)
            r26=r27.verify_parent(FOLDER / r27.PARENT_BASENAME)
            summary=m.audit(root,r27,r26)
            self.assertEqual(summary['result'],'INTERP_SINGLE_PATH_TOPOLOGY_CLASSIFIED_ONLY')
            self.assertEqual(summary['missing_parent_directory_categories'],{'PARENT_DIRECTORY_PRESENT':1})
            self.assertEqual(summary['candidate_elf_structure']['pt_load_segments'],1)
            self.assertEqual(summary['unique_compatible_alternative_regular_files'],1)
            self.assertFalse(summary['interpreter_guest_path_resolved'])
            self.assertFalse(summary['runtime_loader_resolved'])
            self.assertEqual(summary['absent_interp_segments'],12)
            self.assertNotIn('ld-missing.so',json.dumps(summary))


if __name__=='__main__':
    unittest.main()
