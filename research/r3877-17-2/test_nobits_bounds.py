"""Offline regression fixture for SHT_NOBITS bounds rule (research-only)."""
import struct
import unittest

SHT_NOBITS = 8

def check_section_extent(elf_bytes, section_type, offset, size):
    """Mirrors the R3877.17.2 section extent gate, not full ELF parsing."""
    if section_type == SHT_NOBITS:
        return "NO_FILE_BYTES_REQUIRED"
    if offset > len(elf_bytes) or size > len(elf_bytes)-offset:
        raise ValueError("SECTION_DATA_OUT_OF_BOUNDS")
    return "IN_FILE"

class SectionExtentTests(unittest.TestCase):
    def test_large_bss_is_permitted(self):
        self.assertEqual(check_section_extent(b"x"*64, SHT_NOBITS, 64, 65536),
                         "NO_FILE_BYTES_REQUIRED")
    def test_nobits_conceptual_offset_beyond_eof(self):
        self.assertEqual(check_section_extent(b"x"*64, SHT_NOBITS, 300, 65536),
                         "NO_FILE_BYTES_REQUIRED")
    def test_file_backed_section_still_rejected(self):
        with self.assertRaisesRegex(ValueError, "SECTION_DATA_OUT_OF_BOUNDS"):
            check_section_extent(b"x"*64, 1, 64, 65536)
    def test_file_backed_offset_still_rejected(self):
        with self.assertRaisesRegex(ValueError, "SECTION_DATA_OUT_OF_BOUNDS"):
            check_section_extent(b"x"*64, 1, 300, 0)
    def test_valid_file_backed_is_accepted(self):
        self.assertEqual(check_section_extent(b"x"*64, 1, 12, 52), "IN_FILE")

if __name__ == "__main__":
    unittest.main()
