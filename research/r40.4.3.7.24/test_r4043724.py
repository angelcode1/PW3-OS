"""Host-only synthetic tests for R4043724; no stage, QEMU or hardware."""
import importlib.util
import io
import struct
import unittest
from pathlib import Path

p = Path(__file__).with_name("R4043724-INTERP-PADDING-READONLY.py")
spec = importlib.util.spec_from_file_location("r3724", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def elf32(name, endian="<"):
    hdr = bytearray(52)
    hdr[:7] = b"\x7fELF" + bytes([1, 1 if endian == "<" else 2, 1])
    struct.pack_into(endian + "I", hdr, 28, 52)
    struct.pack_into(endian + "HHH", hdr, 40, 52, 32, 1)
    ph = bytearray(32)
    struct.pack_into(endian + "I", ph, 0, 3)
    struct.pack_into(endian + "I", ph, 4, 84)
    struct.pack_into(endian + "I", ph, 16, len(name))
    return bytes(hdr + ph + name)

class TestInterpreter(unittest.TestCase):
    def test_strict(self):
        self.assertEqual(m.classify_literal(b"/lib/ld.so\0"), "STRICT_LITERAL_PASS")
    def test_padding(self):
        self.assertEqual(m.classify_literal(b"/lib/ld.so\0\0\0"), "PADDING_ONLY_CANDIDATE")
    def test_embedded_nonzero(self):
        self.assertEqual(m.classify_literal(b"/lib/ld.so\0x\0"), "HOLD_EMBEDDED_NONZERO_AFTER_NUL")
    def test_not_absolute(self):
        self.assertEqual(m.classify_literal(b"ld.so\0"), "HOLD_NONABSOLUTE_OR_EMPTY")
    def test_missing_final_nul(self):
        self.assertEqual(m.classify_literal(b"/lib/ld.so"), "HOLD_MISSING_FINAL_NUL")
    def test_dotdot(self):
        self.assertEqual(m.classify_literal(b"/lib/../ld.so\0"), "HOLD_UNSAFE_COMPONENT")
    def test_double_slash(self):
        self.assertEqual(m.classify_literal(b"//lib/ld.so\0"), "HOLD_UNSAFE_COMPONENT")
    def test_ascii_only(self):
        self.assertEqual(m.classify_literal(b"/lib/\xff.so\0"), "HOLD_NONASCII_OR_CONTROL")
    def test_elf32(self):
        self.assertEqual(m.inspect_elf(io.BytesIO(elf32(b"/lib/ld.so\0\0"))), ["PADDING_ONLY_CANDIDATE"])
    def test_elf32_big_endian(self):
        self.assertEqual(m.inspect_elf(io.BytesIO(elf32(b"/ld.so\0", ">"))), ["STRICT_LITERAL_PASS"])
    def test_program_header_bounds(self):
        data = bytearray(elf32(b"/ld.so\0"))
        struct.pack_into("<I", data, 28, 99999)
        with self.assertRaises(m.Hold):
            m.inspect_elf(io.BytesIO(data))
    def test_non_elf(self):
        self.assertIsNone(m.inspect_elf(io.BytesIO(b"ordinary file")))

if __name__ == "__main__":
    unittest.main()
