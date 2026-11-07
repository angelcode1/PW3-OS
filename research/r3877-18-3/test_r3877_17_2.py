"""R3877.17.2 regressions: valid .bss/SHT_NOBITS must not be file-backed.
All fixtures are synthetic. No SSH, Docker or Kindle execution.
"""
import io
import json
import struct
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import r3877_17_version_parser as parser
import pw3_r3877_17_2_single_ssh_audit as runner
from test_r3877_17 import fixture
from test_r3877_17_1 import fixture as archive_fixture


def with_section(*, kind, offset, size, before=False):
    raw=bytearray(fixture('need'))
    # Four headers: SHT_NULL, .dynstr, .gnu.version_r, new section.
    struct.pack_into('<H',raw,48,4)  # e_shnum
    struct.pack_into('<IIIIIIIIII',raw,256+3*40,
                     0,kind,0,0,offset,size,0,0,1,0)
    if before:
        # Reorder auxiliary SHT_NOBITS in front of version section, then
        # make the GNU version requirement link to the same .dynstr.
        a=bytes(raw[256+2*40:256+3*40]); b=bytes(raw[256+3*40:256+4*40]);
        raw[256+2*40:256+3*40]=b
        raw[256+3*40:256+4*40]=a
    return bytes(raw)

class Tests(unittest.TestCase):
    def test_nobits_oversized_memory_section_not_file_bytes(self):
        x=parser.parse_version_sections(with_section(kind=parser.SHT_NOBITS,offset=512,size=0x1000000))
        self.assertEqual(x['needs'],{'libc.so.6':[('GLIBC_2.13',False)]})
        self.assertEqual(x['nobits_section_count'],1)
        self.assertEqual(x['nobits_non_file_extent_count'],1)

    def test_nobits_conceptual_offset_beyond_eof(self):
        x=parser.parse_version_sections(with_section(kind=parser.SHT_NOBITS,offset=0x200000,size=0x1000000))
        self.assertEqual(x['sections_seen']['verneed'],1)
        self.assertEqual(x['nobits_non_file_extent_count'],1)

    def test_nobits_before_version_section(self):
        x=parser.parse_version_sections(with_section(kind=parser.SHT_NOBITS,offset=0x200000,size=0x1000000,before=True))
        self.assertEqual(x['needs'],{'libc.so.6':[('GLIBC_2.13',False)]})

    def test_valid_file_backed_section_still_parses(self):
        x=parser.parse_version_sections(with_section(kind=1,offset=460,size=48))
        self.assertEqual(x['sections_seen']['verneed'],1)
        self.assertEqual(x['nobits_section_count'],0)

    def test_file_backed_section_beyond_eof_rejected(self):
        with self.assertRaisesRegex(parser.VersionHold,'SECTION_DATA_OUT_OF_BOUNDS'):
            parser.parse_version_sections(with_section(kind=1,offset=512,size=0x1000000))

    def test_file_backed_offset_beyond_eof_rejected(self):
        with self.assertRaisesRegex(parser.VersionHold,'SECTION_DATA_OUT_OF_BOUNDS'):
            parser.parse_version_sections(with_section(kind=1,offset=0x200000,size=0))

    def test_version_section_truncated_still_rejected(self):
        b=bytearray(fixture('need'))
        struct.pack_into('<I',b,256+80+20,0x1000000)
        with self.assertRaisesRegex(parser.VersionHold,'SECTION_DATA_OUT_OF_BOUNDS'):
            parser.parse_version_sections(bytes(b))

    def test_nobits_cannot_be_version_string_table(self):
        b=bytearray(fixture('need'))
        struct.pack_into('<I',b,256+40+4,parser.SHT_NOBITS)
        with self.assertRaisesRegex(parser.VersionHold,'VERSION_STRING_TABLE_INVALID'):
            parser.parse_version_sections(bytes(b))

    def test_unmodified_version_definition_still_parses(self):
        self.assertEqual(parser.parse_version_sections(fixture('def'))['defines'],['GLIBC_2.13'])

    def test_preflight_still_holds_without_authorization(self):
        output=io.StringIO()
        with patch.object(runner,'one_session_collect',side_effect=AssertionError('SSH must not run')):
            with redirect_stdout(output): rc=runner.main([])
        self.assertEqual(rc,2)
        rec=json.loads(output.getvalue())
        self.assertEqual(rec['milestone'],'R3877.17.2')
        self.assertEqual(rec['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(rec['app_and_stock_binary_contents_transferred'])

    def test_runner_still_uses_only_one_ssh_and_sets_new_milestone(self):
        output=io.StringIO()
        with patch.object(runner,'one_session_collect',return_value=archive_fixture()) as ssh, \
             patch.object(runner.r17,'analyze',return_value={'version_requirements_statically_satisfied':True}), \
             redirect_stdout(output):
            rc=runner.main(['--target',runner.EXPECTED_TARGET,'--port','2222','--authorize-live-readonly-ssh'])
        self.assertEqual(rc,0)
        self.assertEqual(ssh.call_count,1)
        rec=json.loads(output.getvalue())
        self.assertEqual(rec['milestone'],'R3877.17.2')
        self.assertEqual(rec['result'],'PASS_VERSION_NAMES_METADATA_ONLY')
        self.assertEqual(rec['immutable_hold'],'NOT_BOOTABLE')

if __name__=='__main__': unittest.main()
