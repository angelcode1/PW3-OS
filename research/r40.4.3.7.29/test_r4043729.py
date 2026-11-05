"""Synthetic-only tests for read-only R3729 ELF dynamic metadata gate."""
import importlib.util
import io
from pathlib import Path
import struct
import tempfile
import unittest

P = Path(__file__).with_name('R4043729-INTERP-ELF-DYNAMIC-READONLY.py')
spec = importlib.util.spec_from_file_location('r3729', P)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
P26 = Path(__file__).with_name('R4043726-INTERP-GUEST-RESOLVE-READONLY.py')
P27 = Path(__file__).with_name('R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py')
P28 = Path(__file__).with_name('R4043728-INTERP-PATH-TOPOLOGY-READONLY.py')


def elf32(interp=None, *, dynamic=False, broken_dynamic=False, no_strtab=False):
    size = 512
    phnum = (3 if dynamic else (1 if interp is not None else 2))
    if interp is not None:
        phnum = 1
    out = bytearray(size)
    out[:7] = b'\x7fELF\x01\x01\x01'
    struct.pack_into('<HHI', out, 16, 3, 40, 1)
    struct.pack_into('<I', out, 28, 52)
    struct.pack_into('<I', out, 36, 0x05000200)
    struct.pack_into('<HHH', out, 40, 52, 32, phnum)
    def ph(i, typ, offset, vaddr, filesz, memsz):
        struct.pack_into('<IIIIIIII', out, 52+32*i,
                         typ, offset, vaddr, 0, filesz, memsz, 5, 0x1000 if offset == 0 else 1)
    if interp is not None:
        ph(0, 3, 256, 0, len(interp), len(interp))
        out[256:256+len(interp)] = interp
    else:
        ph(0, 1, 0, 0x10000, size, size)
        ph(1, 1, 0x100, 0x10100, 128, 128)
        if dynamic:
            ph(2, 2, 0x140, 0x10140, 40, 40)
            tags = [(1, 0)]
            if not no_strtab:
                tags.extend([(5, 0x10180), (10, 16)])
            if not broken_dynamic:
                tags.append((0, 0))
            else:
                while len(tags) < 5: tags.append((1, 1))
            for i, (tag, val) in enumerate(tags):
                struct.pack_into('<II', out, 0x140+i*8, tag, val)
            out[0x180:0x190] = b'libc.so.6\0' + b'\0'*6
    return bytes(out)


class TestR3729(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p26=m.load_pinned(P26)
        cls.p27=m.load_pinned(P27)
        cls.p28=m.load_pinned(P28)

    def test_bad_pin_refused(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/P26.name
            f.write_text('not the pinned source')
            with self.assertRaises(m.Hold) as ctx:
                m.load_pinned(f)
            self.assertEqual(ctx.exception.code, 'PARENT_HASH_MISMATCH')

    def test_symlink_pin_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/P26.name
            p.symlink_to(P26)
            with self.assertRaises(m.Hold):
                m.load_pinned(p)

    def test_arm_eabi5_soft(self):
        self.assertEqual(m.arm_flags(0x05000200,1,40),
                         {'arch':'ELF32_ARM','eabi':'EABI_VERSION_5','float_flags':'SOFT_FLOAT_FLAG'})

    def test_hard_and_conflict(self):
        self.assertEqual(m.arm_flags(0x05000400,1,40)['float_flags'],'HARD_FLOAT_FLAG')
        self.assertEqual(m.arm_flags(0x05000600,1,40)['float_flags'],'CONFLICTING_FLOAT_FLAGS_HOLD')

    def test_nonarm_flag_excluded(self):
        self.assertEqual(m.arm_flags(0x05000200, 2, 183)['arch'], 'NOT_ELF32_ARM')

    def test_dynamic_needed_and_strtab(self):
        r=m.read_segment_metadata(self.p26,io.BytesIO(elf32(dynamic=True)))
        self.assertEqual(r['pt_load_count'],2)
        self.assertEqual(r['pt_dynamic_count'],1)
        self.assertEqual(r['dt_needed_count'],1)
        self.assertTrue(r['dt_strtab_load_mapping_candidate'])
        self.assertEqual(r['dynamic_null_terminated'],True)

    def test_dynamic_missing_null_hold(self):
        with self.assertRaises(m.Hold) as ctx:
            m.read_segment_metadata(self.p26,io.BytesIO(elf32(dynamic=True,broken_dynamic=True)))
        self.assertEqual(ctx.exception.code,'DYNAMIC_NOT_TERMINATED_HOLD')

    def test_needed_without_strtab_hold(self):
        with self.assertRaises(m.Hold) as ctx:
            m.read_segment_metadata(self.p26,io.BytesIO(elf32(dynamic=True,no_strtab=True)))
        self.assertEqual(ctx.exception.code,'NEEDED_STRTAB_UNRESOLVED_HOLD')

    def test_no_dynamic_is_classified(self):
        r=m.read_segment_metadata(self.p26,io.BytesIO(elf32()))
        self.assertEqual(r['pt_dynamic_count'],0)
        self.assertIsNone(r['dynamic_null_terminated'])

    def test_no_elf_hold(self):
        with self.assertRaises(m.Hold):
            m.read_segment_metadata(self.p26,io.BytesIO(b'not an elf'))

    def test_synthetic_integrated_83_19_7_12(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'bin').mkdir()
            (root/'lib').mkdir()
            (root/'usr/lib').mkdir(parents=True)
            (root/'usr/lib/ld-gamma.so').write_bytes(elf32(dynamic=True))
            (root/'usr/lib/ld-delta.so').write_bytes(elf32(dynamic=False))
            for i in range(19):
                guest=b'/lib/ld-gamma.so\0' if i < 12 else b'/usr/lib/ld-delta.so\0'
                if 2 <= i < 12:
                    guest += b'\0\0'
                (root/'bin'/('src-%03d' % i)).write_bytes(elf32(interp=guest))
            for i in range(62):
                (root/'bin'/('other-%03d' % i)).write_bytes(elf32())
            for i in range(1363):
                (root/('ordinary-%04d' % i)).write_bytes(b'TEXT')
            for i in range(335):
                (root/('link-%04d' % i)).symlink_to('ordinary-%04d' % (i%1363))
            result=m.audit(root,self.p26,self.p27,self.p28)
            self.assertEqual(result['result'],'SINGLE_ALTERNATE_ELF_DYNAMIC_METADATA_CLASSIFIED_ONLY')
            self.assertEqual(result['alternative_metadata']['dt_needed_count'],1)
            self.assertEqual(result['alternative_metadata']['pt_load_count'],2)
            self.assertFalse(result['runtime_loader_resolved'])
            self.assertFalse(result['missing_guest_path_resolved'])
            self.assertNotIn('ld-gamma',str(result))
            self.assertNotIn('ld-delta',str(result))


if __name__=='__main__':
    unittest.main()
