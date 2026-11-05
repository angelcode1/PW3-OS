"""R4043730 host-only synthetic tests. Never execute ELF or access PW3."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

HERE = Path(__file__).parent
M = HERE / 'R4043730-INTERP-ABI-SONAME-READONLY.py'
spec = importlib.util.spec_from_file_location('r3730', M)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
P = HERE / 'R4043729-INTERP-ELF-DYNAMIC-READONLY.py'


def elf32(interp=None, *, soname='ld-gamma.so', flags=0x05000200, dynamic=True, bad_strtab=False, executable_stack=False):
    size = 512
    out = bytearray(size)
    out[:7] = b'\x7fELF\x01\x01\x01'
    struct.pack_into('<HHI', out, 16, 3, 40, 1)
    struct.pack_into('<I', out, 24, 0x10100)
    struct.pack_into('<I', out, 28, 52)
    struct.pack_into('<I', out, 36, flags)
    phnum = 1 if interp is not None else 4 if dynamic else 2
    struct.pack_into('<HHH', out, 40, 52, 32, phnum)
    def ph(i, typ, off, vaddr, filesz, memsz, pflags=5):
        struct.pack_into('<IIIIIIII', out, 52+32*i, typ, off, vaddr, 0, filesz, memsz, pflags, 0x1000)
    if interp is not None:
        ph(0, 3, 256, 0, len(interp), len(interp))
        out[256:256+len(interp)] = interp
    else:
        ph(0, 1, 0, 0x10000, 512, 512, 5)
        ph(1, 1, 0x100, 0x10100, 256, 256, 6)
        if dynamic:
            ph(2, 2, 0x140, 0x10140, 40, 40, 4)
            ph(3, 0x6474e551, 0, 0, 0, 0, 7 if executable_stack else 6)
            name = b'\0' + soname.encode() + b'\0'
            if len(name) > 32:
                raise ValueError('synthetic name too long')
            out[0x180:0x180+len(name)] = name
            tags = [(5, 0x10180 if not bad_strtab else 0xdeadbeef), (10, 32), (14, 1), (0, 0)]
            for i, (tag, val) in enumerate(tags):
                struct.pack_into('<II', out, 0x140+8*i, tag, val)
    return bytes(out)


class TestR3730(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p29 = m.load_r29(P)
        cls.p26 = cls.p29.load_pinned(HERE / 'R4043726-INTERP-GUEST-RESOLVE-READONLY.py')
        cls.p27 = cls.p29.load_pinned(HERE / 'R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py')
        cls.p28 = cls.p29.load_pinned(HERE / 'R4043728-INTERP-PATH-TOPOLOGY-READONLY.py')

    def test_reject_tampered_parent(self):
        with tempfile.TemporaryDirectory() as d:
            name = Path(d) / m.R29_NAME
            name.write_bytes(b'tampered')
            with self.assertRaises(m.Hold) as exc:
                m.load_r29(name)
            self.assertEqual(exc.exception.code, 'R3729_SHA_MISMATCH')

    def test_reject_parent_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            link = Path(d) / m.R29_NAME
            link.symlink_to(P)
            with self.assertRaises(m.Hold):
                m.load_r29(link)

    def test_source_abi_match(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'src'
            path.write_bytes(elf32(interp=b'/lib/ld-gamma.so\0'))
            self.assertEqual(m.arm_abi_flags(self.p29,self.p26,path),('EABI_VERSION_5','SOFT_FLOAT_FLAG',3))

    def test_source_float_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'src'
            path.write_bytes(elf32(interp=b'/lib/ld-gamma.so\0',flags=0x05000400))
            self.assertEqual(m.arm_abi_flags(self.p29,self.p26,path)[1],'HARD_FLOAT_FLAG')

    def test_soname_match(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'candidate'
            path.write_bytes(elf32())
            result=m.inspect_soname(self.p26,path,'ld-gamma.so')
            self.assertEqual(result['soname_basename_match'],'MATCH')
            self.assertTrue(result['elf_entrypoint_nonzero'])
            self.assertEqual(result['load_segments_executable_count'],1)
            self.assertEqual(result['load_segments_writable_count'],1)
            self.assertEqual(result['gnu_stack_exec'],'NONEXECUTABLE')

    def test_soname_different(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'candidate'
            path.write_bytes(elf32(soname='libc.so.6'))
            self.assertEqual(m.inspect_soname(self.p26,path,'ld-gamma.so')['soname_basename_match'],'DIFFERENT')

    def test_bad_strtab_hold(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'candidate'
            path.write_bytes(elf32(bad_strtab=True))
            with self.assertRaises(m.Hold) as exc:
                m.inspect_soname(self.p26,path,'ld-gamma.so')
            self.assertEqual(exc.exception.code,'DT_STRTAB_MAPPING_HOLD')

    def test_stack_exec_classification(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'candidate'
            path.write_bytes(elf32(executable_stack=True))
            self.assertEqual(m.inspect_soname(self.p26,path,'ld-gamma.so')['gnu_stack_exec'],'EXECUTABLE')

    def test_reject_unterminated_soname(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'candidate'
            payload=bytearray(elf32())
            payload[0x180:0x1a0]=b'X'*32
            path.write_bytes(payload)
            with self.assertRaises(m.Hold) as exc:
                m.inspect_soname(self.p26,path,'ld-gamma.so')
            self.assertEqual(exc.exception.code,'DT_SONAME_TERMINATOR_HOLD')

    def test_synthetic_full_stage_replay(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'bin').mkdir(); (root/'lib').mkdir(); (root/'usr/lib').mkdir(parents=True)
            (root/'usr/lib/ld-gamma.so').write_bytes(elf32())
            (root/'usr/lib/ld-delta.so').write_bytes(elf32(dynamic=False))
            for i in range(19):
                guest=b'/lib/ld-gamma.so\0' if i<12 else b'/usr/lib/ld-delta.so\0'
                if 2<=i<12: guest+=b'\0\0'
                (root/'bin'/('src-%03d'%i)).write_bytes(elf32(interp=guest))
            for i in range(62):
                (root/'bin'/('other-%03d'%i)).write_bytes(elf32(dynamic=False))
            for i in range(1363):
                (root/('ordinary-%04d'%i)).write_bytes(b'TEXT')
            for i in range(335):
                (root/('link-%04d'%i)).symlink_to('ordinary-%04d'%(i%1363))
            result=m.audit(root,self.p26,self.p27,self.p28,self.p29)
            self.assertEqual(result['result'],'INTERP_ABI_AND_SONAME_STATIC_CLASSIFICATION_ONLY')
            self.assertEqual(result['requesting_elf_count'],12)
            self.assertEqual(result['source_arm_eabi_float_flag_categories']['EABI_MATCH'],12)
            self.assertEqual(result['source_arm_eabi_float_flag_categories']['FLOAT_FLAGS_MATCH'],12)
            self.assertEqual(result['candidate_soname_and_flags']['soname_basename_match'],'MATCH')
            self.assertFalse(result['missing_guest_path_resolved'])
            self.assertFalse(result['boot_authorized'])
            self.assertNotIn('ld-gamma',str(result))

if __name__=='__main__':
    unittest.main()
