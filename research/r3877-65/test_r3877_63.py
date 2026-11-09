"""R3877.63 bounded read-only recovery candidate content triage; Python 3.9+."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import pw3_r3877_63_recovery_candidate_headers as m


def zip_bytes(files):
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',compression=zipfile.ZIP_STORED) as z:
        for name,data in files.items():z.writestr(name,data)
    return mem.getvalue()

class R63OfflineTests(unittest.TestCase):
    def test_01_base_pinned(self):self.assertTrue(m.pins_ok())
    def test_02_default_no_content_or_scan(self):
        with patch.object(m,'inspect',side_effect=AssertionError('should not scan')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                rc=m.main([])
        self.assertEqual(rc,2)
        r=json.loads(output.getvalue())
        self.assertEqual(r['immutable_hold'],'NOT_BOOTABLE')
        self.assertFalse(r['physical_device_access_performed'])
    def test_03_root_without_optin_refuses_before_scan(self):
        with patch.object(m,'inspect',side_effect=AssertionError('unexpected review')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                rc=m.main(['--scan-root','/no/such/path'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(output.getvalue())['hold_category'],'READONLY_CONTENT_REVIEW_OPT_IN_REQUIRED')
    def test_04_zip_magic_and_structure(self):
        z=zip_bytes({'stock_rootfs.img':b'abc','docs/readme.txt':b'hi'})
        f=io.BytesIO(z)
        self.assertEqual(m.magic_format(f),'zip')
        d=m.zip_metadata(f,len(z))
        self.assertEqual(d['entry_count'],2)
        self.assertEqual(d['image_named_member_count'],1)
    def test_05_zip_traversal_is_reported_not_extracted(self):
        z=zip_bytes({'../rootfs.img':b'x','/absolute':b'y','C:/path/file':b'z'})
        d=m.zip_metadata(io.BytesIO(z),len(z))
        self.assertEqual(d['suspicious_path_member_count'],3)
    def test_06_zip_no_eocd(self):
        d=m.zip_metadata(io.BytesIO(b'PK\x03\x04not-really-zip'),17)
        self.assertEqual(d['status'],'INVALID_EOCD_OR_UNSUPPORTED_ZIP')
    def test_07_zip_entry_limit(self):
        z=zip_bytes({'file%04d.txt'%i:b'' for i in range(m.MAX_ZIP_ENTRIES+1)})
        self.assertEqual(m.zip_metadata(io.BytesIO(z),len(z))['status'],
                         'ZIP_CENTRAL_DIRECTORY_BOUNDS_OR_MULTIDISK_HOLD')
    def test_08_zip_unsafe_symlink_reports(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z:
            info=zipfile.ZipInfo('dir/link')
            info.create_system=3
            info.external_attr=(stat.S_IFLNK|0o777)<<16
            z.writestr(info,'../../outside')
        z=b.getvalue()
        self.assertEqual(m.zip_metadata(io.BytesIO(z),len(z))['symlink_member_count'],1)
    def test_09_gzip_opaque_never_unzipped(self):
        self.assertEqual(m.magic_format(io.BytesIO(b'\x1f\x8b'+b'0'*400)),'gzip_opaque')
    def test_10_7z_opaque(self):
        self.assertEqual(m.magic_format(io.BytesIO(b'7z\xbc\xaf\x27\x1c'+b'0'*400)),'7z_opaque')
    def test_11_archive_digest_stream_exact(self):
        x=b'abc'*100
        self.assertEqual(m.sha256_stream(io.BytesIO(x),len(x)),hashlib.sha256(x).hexdigest())
    def test_12_archive_digest_short_read_holds(self):
        with self.assertRaises(m.Hold):m.sha256_stream(io.BytesIO(b'abc'),100)
    def test_13_manifest_exact_basenames_only(self):
        digest='a'*64
        data=('{}  archive.zip\n{}  ../some/other.zip\n'.format(digest,digest)).encode()
        self.assertEqual(m.parse_manifest(io.BytesIO(data),len(data)),[(digest,'archive.zip')])
    def test_14_manifest_nonutf8_ignored(self):
        self.assertEqual(m.parse_manifest(io.BytesIO(b'\xff\xff'),2),[])
    def test_15_manifest_too_big_holds(self):
        with self.assertRaises(m.Hold):m.parse_manifest(io.BytesIO(b'xx'),m.MAX_MANIFEST_BYTES+1)
    def test_16_file_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);real=root/'data';real.write_bytes(b'abc')
            link=root/'kindle_backup.zip';link.symlink_to(real)
            with self.assertRaises(m.Hold):
                with m.opened_regular_file(link,link.lstat()):pass
    def test_17_inode_change_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'kindle_backup.zip';p.write_bytes(b'a');before=p.stat();p.write_bytes(b'zz')
            with self.assertRaises(m.Hold):
                with m.opened_regular_file(p,before):pass
    def test_18_reject_symlink_dir(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);target=root/'actual';target.mkdir()
            (target/'backup.zip').write_bytes(b'abc')
            (root/'link').symlink_to(target,target_is_directory=True)
            selected=m.choose(root,2,1000,100)
            self.assertEqual(len(selected),1)
    def test_19_candidate_triage_full(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            archive=root/'kindle_backup.zip'
            archive.write_bytes(zip_bytes({'stock_rootfs.img':b'test','README':b'file'}))
            checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
            (root/'SHA256SUMS_LOCAL.txt').write_text(checksum+'  kindle_backup.zip\n')
            (root/'rescue-notes.md').write_text('Kindle restoration plan: UART and checksum, not verified')
            (root/'pw3-r3877-62-research.zip').write_bytes(b'not relevant to recovery')
            result=m.inspect(root)
            self.assertEqual(result['archive_candidates_reviewed'],1)
            self.assertEqual(result['manifest_files_reviewed'],1)
            self.assertEqual(result['archive_candidates_with_matching_untrusted_sha256_manifest'],1)
            self.assertEqual(result['archive_candidates'][0]['candidate_id'],'A01')
            self.assertEqual(result['archive_candidates'][0]['structural_review']['image_named_member_count'],1)
            self.assertEqual(result['recovery_docs_plaintext_read'],1)
            self.assertIn('mentions_serial_uart',result['recovery_doc_keyword_mentions_by_document'])
            self.assertFalse(result['raw_archive_names_or_paths_published'])
            self.assertNotIn('kindle_backup.zip',json.dumps(result))
            self.assertNotIn(checksum,json.dumps(result))
            self.assertFalse(result['stock_image_authenticated'])
            self.assertFalse(result['restoration_verified'])
            self.assertTrue(result['scope']['bounded_scope_scan_complete'])
            self.assertEqual(result['scope']['candidate_counts_by_category']['research_named_archive_candidate_not_authenticated_backup'],1)
    def test_20_mismatched_manifest_no_claim(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'kindle_backup.zip').write_bytes(zip_bytes({'x':b'x'}))
            (root/'SHA256SUMS.txt').write_text('0'*64+'  kindle_backup.zip\n')
            r=m.inspect(root)
            self.assertEqual(r['archive_candidates_with_matching_untrusted_sha256_manifest'],0)
    def test_21_opaque_document_never_parsed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'recovery_guide.pdf').write_bytes(b'%PDF-xxxx')
            r=m.inspect(root)
            self.assertEqual(r['recovery_docs_opaque_or_binary'],1)
    def test_22_image_candidate_included(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'stock_mmcblk0p1.img').write_bytes(b'abcd')
            r=m.inspect(root)
            self.assertEqual(r['archive_candidates_reviewed'],1)
            self.assertEqual(r['archive_candidates'][0]['format_detected_from_bytes'],'unknown_or_raw')
    def test_23_max_aggregate_archive_cap(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'kindle_backup.zip'
            with p.open('wb') as f:f.truncate(m.MAX_ARCHIVE_BYTES+1)
            with self.assertRaises(m.Hold):m.inspect(d)
    def test_24_selected_root_link_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'real').mkdir();(p/'fake').symlink_to(p/'real',target_is_directory=True)
            with self.assertRaises(m.base.Hold):m.inspect(p/'fake')
    def test_25_expected_always_hold_with_review(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'kindle_backup.zip').write_bytes(zip_bytes({'a':b'b'}))
            with contextlib.redirect_stdout(io.StringIO()) as out:
                rc=m.main(['--scan-root',d,'--acknowledge-readonly-content-inspection'])
            j=json.loads(out.getvalue())
            self.assertEqual(rc,2)
            self.assertEqual(j['result'],'HOLD')
            self.assertTrue(j['review']['content_hashes_published'] is False)
            self.assertFalse(j['recovery_verified'])
            self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')
    def test_26_limit_malformed_or_missing(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc=m.main(['--scan-root','/missing/path','--acknowledge-readonly-content-inspection'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],
            'BOUNDED_CANDIDATE_CONTENT_REVIEW_REFUSED_OR_INCOMPLETE')
    def test_27_no_unsafe_features(self):
        s=Path(m.__file__).read_text()
        for needle in ['subprocess.', 'requests.', 'urllib.', 'paramiko', 'docker run', 'adb ',
                       'ssh ', 'extractall(', 'extract(', 'open(\'wb\')', '.write_bytes(', '.write_text(']:
            self.assertNotIn(needle,s)
    def test_28_file_limit_capped(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(260): (Path(d)/('SHA256SUMS_%d.txt'%i)).write_bytes(b'')
            with self.assertRaises(m.Hold):m.inspect(d)
    def test_29_no_content_without_optin(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'kindle_backup.zip').write_bytes(b'hello')
            with patch.object(m,'inspect',side_effect=AssertionError('Content accessed')):
                with contextlib.redirect_stdout(io.StringIO()) as out:
                    code=m.main(['--scan-root',d])
            self.assertEqual(code,2)
    def test_30_duplicate_basename_manifest_matches_only_one_digest(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);a=root/'a';b=root/'b';a.mkdir();b.mkdir()
            x=zip_bytes({'x':b'x'});y=zip_bytes({'x':b'y'})
            (a/'kindle_backup.zip').write_bytes(x)
            (b/'kindle_backup.zip').write_bytes(y)
            (root/'SHA256SUMS.txt').write_text(hashlib.sha256(x).hexdigest()+'  kindle_backup.zip\n')
            r=m.inspect(root)
            self.assertEqual(r['archive_candidates_reviewed'],2)
            self.assertEqual(r['archive_candidates_with_matching_untrusted_sha256_manifest'],1)
    def test_31_reject_parent_becomes_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);tar=root/'actual';tar.mkdir();file=tar/'kindle_backup.zip';file.write_bytes(b'x')
            proxy=root/'newdir';proxy.symlink_to(tar,target_is_directory=True)
            with self.assertRaises(m.Hold):
                with m.opened_regular_file(proxy/'kindle_backup.zip',file.stat()):pass

if __name__=='__main__':unittest.main()
