"""R3877.65: synthetic PAX/GNU + bounded in-memory gzip and HOLD regressions."""
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

import pw3_r3877_65_extended_tar_triage as m


def maketar(name,body=b'contents',fmt=tarfile.PAX_FORMAT,link=False):
    f=io.BytesIO()
    with tarfile.open(fileobj=f,mode='w',format=fmt) as tar:
        info=tarfile.TarInfo(name)
        if link:
            info.type=tarfile.SYMTYPE;info.linkname='../outside';info.size=0
            tar.addfile(info)
        else:
            info.size=len(body);tar.addfile(info,io.BytesIO(body))
    return f.getvalue()


def rechecksum(block):
    block=bytearray(block)
    block[148:156]=b'        '
    block[148:156]=('%06o\0 ' % (sum(block[:148])+8*32+sum(block[156:]))).encode()
    return bytes(block)


class R65Tests(unittest.TestCase):
    def test_01_transitive_pins(self):self.assertTrue(m.pins_ok())
    def test_02_cli_no_scan_without_optin(self):
        with patch.object(m,'inspect',side_effect=AssertionError('MUST_NOT_SCAN')):
            with contextlib.redirect_stdout(io.StringIO()) as out:rc=m.main(['--scan-root','/tmp'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'EXPLICIT_BOUNDED_DECOMPRESSION_OPT_IN_REQUIRED')
    def test_03_default_no_scan(self):
        with patch.object(m,'inspect',side_effect=AssertionError('MUST_NOT_SCAN')):
            with contextlib.redirect_stdout(io.StringIO()) as out:rc=m.main([])
        j=json.loads(out.getvalue());self.assertEqual(rc,2)
        self.assertEqual(j['hold_category'],'EXPLICIT_SCAN_ROOT_REQUIRED')
        self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')
    def test_04_ustar_simple(self):
        b=maketar('rootfs.img',fmt=tarfile.USTAR_FORMAT)
        r=m.parse_tar(io.BytesIO(b),len(b))
        self.assertTrue(r['full_name_coverage_verified'])
        self.assertEqual(r['stock_image_named_member_count'],1)
        self.assertEqual(r['regular_member_count'],1)
        self.assertEqual(r['status'],'TAR_NAMES_RESOLVED_HEADERS_COMPLETE')
    def test_05_pax_long_path_effective_name(self):
        b=maketar(('a/'*70)+'rootfs.img')
        r=m.parse_tar(io.BytesIO(b),len(b))
        self.assertEqual(r['extension_header_counts'].get('pax_local'),1)
        self.assertTrue(r['full_name_coverage_verified'],r)
        self.assertEqual(r['stock_image_named_member_count'],1)
        self.assertEqual(r['regular_member_count'],1)
    def test_06_gnu_longname(self):
        b=maketar(('subdir/'*20)+'original_kernel.bin',fmt=tarfile.GNU_FORMAT)
        r=m.parse_tar(io.BytesIO(b),len(b))
        self.assertEqual(r['extension_header_counts'].get('gnu_longname'),1)
        self.assertTrue(r['full_name_coverage_verified'],r)
        self.assertEqual(r['stock_image_named_member_count'],1)
    def test_07_pax_name_does_not_leak(self):
        private='private-secret-identifier-987123'
        b=maketar((private+'/'*0+'/')*10+'rootfs.img')
        r=m.parse_tar(io.BytesIO(b),len(b))
        self.assertNotIn(private,json.dumps(r))
        self.assertNotIn('rootfs.img',json.dumps(r))
    def test_08_pax_links_count_unsafe_target(self):
        b=maketar('link',link=True)
        r=m.parse_tar(io.BytesIO(b),len(b))
        self.assertEqual(r['symlink_member_count'],1)
        self.assertEqual(r['suspicious_path_or_link_count'],1)
    def test_09_pax_record_valid(self):
        payload=b'16 path=foo.img\n'
        self.assertEqual(m.parse_pax(payload),{'path':'foo.img'})
    def test_10_pax_record_bad_length(self):
        self.assertIsNone(m.parse_pax(b'13 path=foo.img\n'))
    def test_11_pax_record_invalid_utf8(self):
        self.assertIsNone(m.parse_pax(b'13 path=\xff.img\n'))
    def test_12_pax_header_payload_too_large(self):
        name='a/'*100+'rootfs.img'
        b=maketar(name)
        with patch.object(m,'MAX_EXTENSION_BYTES_PER_HEADER',1):
            r=m.parse_tar(io.BytesIO(b),len(b))
        self.assertEqual(r['termination'],'EXTENSION_BYTE_BUDGET_EXCEEDED')
        self.assertFalse(r['full_name_coverage_verified'])
    def test_13_tar_corrupt_checksum(self):
        b=bytearray(maketar('test.img',fmt=tarfile.USTAR_FORMAT));b[0]=42
        r=m.parse_tar(io.BytesIO(b),len(b))
        self.assertEqual(r['termination'],'BAD_TAR_HEADER_CHECKSUM')
    def test_14_tar_stop_early_prefix(self):
        b=maketar('x',b'a'*2048,fmt=tarfile.USTAR_FORMAT)
        r=m.parse_tar(io.BytesIO(b[:1024]),1024,allow_prefix=True)
        self.assertEqual(r['termination'],'PREFIX_LIMIT_REACHED')
        self.assertFalse(r['full_name_coverage_verified'])
    def test_15_gzip_complete_tar(self):
        b=gzip.compress(maketar(('a/'*70)+'rootfs.img'))
        r=m.inspect_gzip(io.BytesIO(b),len(b))
        self.assertTrue(r['gzip_stream_end_observed'],r)
        self.assertTrue(r['gzip_full_stream_integrity_verified'],r)
        self.assertTrue(r['tar_full_coverage_verified'],r)
        self.assertEqual(r['tar_headers']['stock_image_named_member_count'],1)
        self.assertFalse(r['decompressed_content_saved'])
    def test_16_gzip_more_than_old_512k(self):
        f=io.BytesIO()
        with tarfile.open(fileobj=f,mode='w',format=tarfile.PAX_FORMAT) as t:
            x=tarfile.TarInfo('filler.dat');x.size=700_000;t.addfile(x,io.BytesIO(bytes(range(256))*2734 + b'Z'*96))
            x=tarfile.TarInfo('stock_rootfs.img');x.size=1;t.addfile(x,io.BytesIO(b'X'))
        raw=f.getvalue();b=gzip.compress(raw)
        r=m.inspect_gzip(io.BytesIO(b),len(b))
        self.assertEqual(r['tar_headers']['stock_image_named_member_count'],1)
        self.assertTrue(r['tar_full_coverage_verified'],r)
    def test_17_gzip_bomb_bound(self):
        b=gzip.compress(b'A'*(2*1024*1024))
        with patch.object(m,'MAX_GZIP_IN_MEMORY_BYTES',64*1024):
            r=m.inspect_gzip(io.BytesIO(b),len(b))
        self.assertLessEqual(r['decompressed_bytes_in_memory'],64*1024)
        self.assertFalse(r['gzip_full_stream_integrity_verified'])
    def test_18_gzip_truncated(self):
        b=gzip.compress(maketar('rootfs.img'))[:-8]
        r=m.inspect_gzip(io.BytesIO(b),len(b))
        self.assertFalse(r['gzip_full_stream_integrity_verified'])
        self.assertFalse(r['tar_full_coverage_verified'])
    def test_19_gzip_bad_crc(self):
        b=bytearray(gzip.compress(b'hello'*200));b[-5]^=42
        r=m.inspect_gzip(io.BytesIO(b),len(b))
        self.assertEqual(r['status'],'GZIP_INVALID_OR_CHECKSUM_ERROR')
    def test_20_gzip_trailing_bytes(self):
        b=gzip.compress(maketar('test.img'))+b'EXTRA'
        r=m.inspect_gzip(io.BytesIO(b),len(b))
        self.assertFalse(r['gzip_full_stream_integrity_verified'])
    def test_21_gzip_concatenated(self):
        b=gzip.compress(maketar('a.img'))+gzip.compress(b'unknown')
        r=m.inspect_gzip(io.BytesIO(b),len(b))
        self.assertFalse(r['gzip_full_stream_integrity_verified'])
    def test_22_invalid_gzip(self):
        b=b'\x1f\x8b'+b'junk'*200
        r=m.inspect_gzip(io.BytesIO(b),len(b))
        self.assertEqual(r['status'],'GZIP_INVALID_OR_CHECKSUM_ERROR')
    def test_23_full_synthetic_inspect(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/'kindle_backup_a.tar').write_bytes(maketar(('a/'*75)+'rootfs.img'))
            (root/'kindle_backup_b.tar.gz').write_bytes(gzip.compress(maketar('original_kernel.bin')))
            r=m.inspect(root)
            self.assertEqual(r['archive_count'],2)
            self.assertFalse(r['stock_recovery_authenticity_verified'])
            self.assertFalse(r['independent_restore_verified'])
            text=json.dumps(r)
            self.assertNotIn('kindle_backup_a',text)
            self.assertNotIn('rootfs.img',text)
    def test_24_cli_always_hold(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'kindle_backup_a.tar').write_bytes(maketar('rootfs.img'))
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc=m.main(['--scan-root',d,'--acknowledge-readonly-extended-metadata-and-bounded-gzip-decompression'])
            r=json.loads(out.getvalue())
            self.assertEqual(rc,2)
            self.assertEqual(r['result'],'HOLD')
            self.assertEqual(r['hold_category'],'STOCK_RECOVERY_AUTHENTICITY_AND_INDEPENDENT_RESTORE_UNVERIFIED')
            self.assertFalse(r['physical_device_access_performed'])
    def test_25_pins_reject_change(self):
        with patch.object(m,'PINNED_R64_SHA256','0'*64):
            with self.assertRaises(m.Hold):m.pins_ok()
    def test_26_no_network_or_device_or_disk_writer(self):
        s=Path(m.__file__).read_text()
        for needle in ['subprocess.','requests.','urllib.','paramiko','docker run','adb ','ssh ','os.system(','.extract(','.extractall(','.write_bytes(','.write_text(']:
            self.assertNotIn(needle,s)
    def test_27_scanner_symlink_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'actual';p.mkdir();(root/'other').symlink_to(p, target_is_directory=True)
            with self.assertRaises((m.Hold,m.prev.Hold,m.prev.prior.Hold,m.prev.prior.base.Hold)):
                m.inspect(root/'other')
    def test_28_report_has_no_hash_or_paths(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'kindle_backup.tar').write_bytes(maketar('private-stock-rootfs.img'))
            r=m.inspect(d)
            self.assertNotIn('private',json.dumps(r))
            self.assertNotIn('"path"',json.dumps(r))

if __name__=='__main__':unittest.main()
