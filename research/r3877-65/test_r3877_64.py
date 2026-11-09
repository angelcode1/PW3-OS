"""R3877.64 offline regressions: readonly TAR headers and bounded gzip prefix."""
import contextlib
import gzip
import io
import json
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch

import pw3_r3877_64_tar_gzip_structure as m


def tar_bytes(files):
    b=io.BytesIO()
    with tarfile.open(fileobj=b,mode='w',format=tarfile.USTAR_FORMAT) as t:
        for n,content in files.items():
            item=tarfile.TarInfo(n);item.size=len(content)
            t.addfile(item,io.BytesIO(content))
    return b.getvalue()


class R64Tests(unittest.TestCase):
    def test_01_chain_pinned(self): self.assertTrue(m.pins_ok())
    def test_02_preflight_does_not_scan(self):
        with patch.object(m,'inspect',side_effect=AssertionError('scan called')):
            with contextlib.redirect_stdout(io.StringIO()) as out: code=m.main([])
        self.assertEqual(code,2)
        j=json.loads(out.getvalue());self.assertEqual(j['result'],'HOLD')
        self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(j['physical_device_access_performed'])
    def test_03_missing_optin(self):
        with patch.object(m,'inspect',side_effect=AssertionError('scan called')):
            with contextlib.redirect_stdout(io.StringIO()) as out:code=m.main(['--scan-root','/unknown'])
        self.assertEqual(code,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'GZIP_DECOMPRESSION_OPT_IN_REQUIRED')
    def test_04_number_octal(self):
        self.assertEqual(m._number(b'00000000777\0'),511)
        self.assertIsNone(m._number(b'\x80'+b'\0'*11))
        self.assertIsNone(m._number(b'99\0'))
    def test_05_tar_members_and_end(self):
        b=tar_bytes({'stock_rootfs.img':b'X'*4096,'docs/notes.txt':b'hi'})
        r=m.tar_headers(io.BytesIO(b),len(b))
        self.assertEqual(r['status'],'TAR_HEADERS_COMPLETE_NO_MEMBER_CONTENT_READ')
        self.assertEqual(r['termination'],'TWO_ZERO_END_BLOCKS')
        self.assertEqual(r['regular_member_count'],2)
        self.assertEqual(r['stock_image_named_member_count'],1)
        self.assertEqual(r['sum_declared_member_bytes'],4098)
        self.assertFalse(r['member_contents_read'])
    def test_06_tar_name_not_leaked(self):
        name='highly-private-kindle-stuff-rootfs.img'
        b=tar_bytes({name:b'secret'})
        r=m.tar_headers(io.BytesIO(b),len(b))
        self.assertNotIn(name,json.dumps(r))
        self.assertNotIn('secret',json.dumps(r))
    def test_07_tar_suspicious_path_count(self):
        b=tar_bytes({'../bad/rootfs.img':b'a','/absolute/path':b'x'})
        r=m.tar_headers(io.BytesIO(b),len(b))
        self.assertEqual(r['suspicious_path_member_count'],2)
    def test_08_tar_symlink_count(self):
        f=io.BytesIO()
        with tarfile.open(fileobj=f,mode='w',format=tarfile.USTAR_FORMAT) as t:
            entry=tarfile.TarInfo('link');entry.type=tarfile.SYMTYPE;entry.linkname='../../outside'
            t.addfile(entry)
        r=m.tar_headers(io.BytesIO(f.getvalue()),len(f.getvalue()))
        self.assertEqual(r['symlink_member_count'],1)
    def test_09_tar_bad_checksum(self):
        b=bytearray(tar_bytes({'file.txt':b'a'}));b[0]=ord('Z')
        r=m.tar_headers(io.BytesIO(b),len(b))
        self.assertEqual(r['termination'],'INVALID_TAR_HEADER_CHECKSUM')
    def test_10_tar_member_outside(self):
        b=tar_bytes({'file.txt':b'a'*2048})
        r=m.tar_headers(io.BytesIO(b[:1024]),1024,allow_prefix=True)
        self.assertEqual(r['termination'],'PREFIX_LIMIT_REACHED')
    def test_11_tar_short(self):
        self.assertEqual(m.tar_headers(io.BytesIO(b'a'*512),512)['status'],'TAR_TOO_SMALL_FOR_HEADER_REVIEW')
    def test_12_tar_unsupported_x_header(self):
        b=bytearray(tar_bytes({'file.txt':b'a'}));b[156]=ord('x');b[148:156]=b'        '
        chk=sum(b[:148])+8*32+sum(b[156:512]);b[148:156]=('%06o\0 '%chk).encode()
        r=m.tar_headers(io.BytesIO(b),len(b))
        self.assertEqual(r['extended_or_sparse_header_count'],1)
        self.assertFalse(r['full_name_coverage_verified'])
    def test_13_gzip_plain_unknown(self):
        b=gzip.compress(b'ABCDEF'*20)
        r=m.gzip_bounded_prefix(io.BytesIO(b),len(b))
        self.assertEqual(r['signature'],'unrecognized_prefix')
        self.assertTrue(r['gzip_stream_end_observed'])
        self.assertFalse(r['decompressed_content_saved'])
    def test_14_gzip_tar_signature(self):
        b=gzip.compress(tar_bytes({'stock_rootfs.img':b'x'*512}))
        r=m.gzip_bounded_prefix(io.BytesIO(b),len(b))
        self.assertEqual(r['signature'],'ustar_header_candidate')
        self.assertEqual(r['tar_prefix_headers']['stock_image_named_member_count'],1)
    def test_15_gzip_uimage_marker(self):
        b=gzip.compress(b'\x27\x05\x19\x56'+b'A'*140)
        self.assertEqual(m.gzip_bounded_prefix(io.BytesIO(b),len(b))['signature'],
                         'u_boot_uimage_header_candidate')
    def test_16_gzip_invalid(self):
        b=b'\x1f\x8b'+b'garbage'*50
        self.assertEqual(m.gzip_bounded_prefix(io.BytesIO(b),len(b))['status'],'INVALID_GZIP_PREFIX')
    def test_17_gzip_bomb_cap(self):
        b=gzip.compress(b'0'*(m.MAX_GZIP_UNCOMPRESSED_PREFIX_BYTES*5))
        r=m.gzip_bounded_prefix(io.BytesIO(b),len(b))
        self.assertLessEqual(r['decompressed_prefix_bytes'],m.MAX_GZIP_UNCOMPRESSED_PREFIX_BYTES)
        self.assertFalse(r['decompressed_content_saved'])
    def test_18_gzip_signature_elf(self):
        self.assertEqual(m._signature(b'\x7fELF' + b'x'*2000),'elf_prefix')
    def test_19_gzip_signature_ext(self):
        b=bytearray(1100);b[1080:1082]=b'\x53\xef'
        self.assertEqual(m._signature(b),'ext_family_superblock_magic_candidate')
    def test_20_gzip_signature_cpio(self):
        self.assertEqual(m._signature(b'070701'+b'A'*20),'cpio_newc_header_candidate')
    def test_21_gzip_signature_squashfs(self):
        self.assertEqual(m._signature(b'hsqs'+b'X'*100),'squashfs_header_candidate')
    def test_22_gzip_signature_ubi(self):
        self.assertEqual(m._signature(b'UBI#'+b'X'*100),'ubi_header_candidate')
    def test_23_inspect_synthetic_tar_and_gzip(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'kindle_backup_A.tar').write_bytes(tar_bytes({'stock_rootfs.img':b'abc'}))
            (root/'kindle_backup_B.tar.gz').write_bytes(gzip.compress(b'\x7fELF'+b'a'*10))
            (root/'SHA256SUMS_LOCAL.txt').write_text('')
            r=m.inspect(root)
            self.assertEqual(r['archive_count'],2)
            byfmt={x['format_detected_from_bytes']:x for x in r['archive_candidates']}
            self.assertEqual(byfmt['tar_opaque']['structural_review']['stock_image_named_member_count'],1)
            self.assertEqual(byfmt['gzip_opaque']['structural_review']['signature'],'elf_prefix')
            self.assertFalse(r['stock_recovery_authenticity_verified'])
            self.assertFalse(r['independent_restore_verified'])
            self.assertFalse(r['filenames_or_paths_published'])
            self.assertNotIn('kindle_backup_A',json.dumps(r))
    def test_24_mac_optin_always_hold(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'kindle_backup.tar').write_bytes(tar_bytes({'x':b'a'}))
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc=m.main(['--scan-root',d,'--acknowledge-readonly-prefix-inspection'])
            j=json.loads(out.getvalue())
            self.assertEqual(rc,2)
            self.assertEqual(j['result'],'HOLD')
            self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')
            self.assertFalse(j['recovery_verified'])
            self.assertEqual(j['review']['archive_count'],1)
    def test_25_missing_path_fail_closed(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc=m.main(['--scan-root','/missing/dir','--acknowledge-readonly-prefix-inspection'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],
            'BOUNDED_TAR_GZIP_STRUCTURAL_REVIEW_REFUSED_OR_INCOMPLETE')
    def test_26_pin_change_refused(self):
        with patch.object(m,'PINNED_R63_SHA256','0'*64):
            with self.assertRaises(m.Hold):m.pins_ok()
    def test_27_no_commands_network_or_writes(self):
        s=Path(m.__file__).read_text()
        for needle in ['subprocess.', 'requests.', 'urllib.', 'paramiko', 'docker run',
            'adb ', 'ssh ', '.extract(', '.extractall(', 'open(\'wb\')', '.write_bytes(','.write_text(']:
            self.assertNotIn(needle,s)
    def test_28_tar_header_limit(self):
        b=tar_bytes({'a':b'hi'})
        with patch.object(m,'MAX_TAR_HEADER_RECORDS',1):
            r=m.tar_headers(io.BytesIO(b),len(b))
        self.assertEqual(r['termination'],'TAR_HEADER_RECORD_BUDGET_EXHAUSTED')
    def test_29_no_raw_digest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'kindle_backup.tar';p.write_bytes(tar_bytes({'stock_rootfs.img':b'x'}))
            r=m.inspect(d)
            import re
            self.assertIsNone(re.search(r'\b[0-9a-f]{64}\b',json.dumps(r).lower()))
    def test_30_research_zip_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'pw3-r3877-63-research.zip').write_bytes(b'xxx')
            r=m.inspect(d)
            self.assertEqual(r['archive_count'],0)
    def test_31_no_gzip_unrestricted_stream(self):
        b=gzip.compress(b'x'*700000)
        r=m.gzip_bounded_prefix(io.BytesIO(b),len(b))
        self.assertLessEqual(r['compressed_bytes_consumed'],m.MAX_GZIP_COMPRESSED_PREFIX_BYTES)
        self.assertLessEqual(r['decompressed_prefix_bytes'],m.MAX_GZIP_UNCOMPRESSED_PREFIX_BYTES)

if __name__=='__main__':unittest.main()
