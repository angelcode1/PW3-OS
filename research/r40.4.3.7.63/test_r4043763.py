"""Host-only tests use synthetic source archives. No network or device access."""
import bz2
from contextlib import contextmanager
import importlib.util
from io import BytesIO
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).with_name('R4043763-AMAZON-PW3-SOURCE-COMPARE-READONLY.py')
spec = importlib.util.spec_from_file_location('r3763', SCRIPT)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)
DATA = b'CONFIG_VFPv3=y\n'

def pack_tar(items, mode='w'):
    out = BytesIO()
    with tarfile.open(fileobj=out, mode=mode) as arc:
        for name, data, typ in items:
            info = tarfile.TarInfo(name)
            if typ == 'file':
                info.size = len(data)
                arc.addfile(info, BytesIO(data))
            else:
                info.type = tarfile.SYMTYPE
                info.linkname = '../outside'
                arc.addfile(info)
    return out.getvalue()

@contextmanager
def fixture(items):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / r.OFFICIAL_ARCHIVE_NAME
        path.write_bytes(pack_tar(items, 'w:gz'))
        yield path

class TestR3763(unittest.TestCase):
    def test_github_blob_formula(self):
        import hashlib
        self.assertEqual(r.git_blob(b'a'), hashlib.sha1(b'blob 1\x00a').hexdigest())

    def test_nested_archive_match(self):
        nested = pack_tar([('linux-3.0.35/arch/arm/configs/imx60_wario_defconfig', DATA, 'file')], 'w:bz2')
        with fixture([('gplresults/linux-3.0.35-lab126.tar.bz2', nested, 'file')]) as path:
            with mock.patch.object(r, 'PIN_BLOB', r.git_blob(DATA)), mock.patch.object(r, 'PIN_SIZE', len(DATA)):
                result = r.analyze(path)
            self.assertEqual(result['result'], 'AMAZON_LISTED_ARCHIVE_WARIO_BLOB_MATCH_STATIC_ONLY')
            self.assertEqual(result['candidate_configs_in_nested_archive'], 1)
            self.assertFalse(result['r13_image_provenance_authenticated'])
            self.assertEqual(result['immutable_hold'], 'NOT_BOOTABLE')

    def test_direct_archive_match(self):
        with fixture([('arch/arm/configs/imx60_wario_defconfig', DATA, 'file')]) as path:
            with mock.patch.object(r, 'PIN_BLOB', r.git_blob(DATA)), mock.patch.object(r, 'PIN_SIZE', len(DATA)):
                self.assertEqual(r.analyze(path)['candidate_configs_found'], 1)

    def test_mismatch_hold(self):
        with fixture([('arch/arm/configs/imx60_wario_defconfig', DATA, 'file')]) as path:
            with self.assertRaisesRegex(r.Hold, 'OFFICIAL_ARCHIVE_WARIO_CONFIG_BLOB_DIFFERS_HOLD'):
                r.analyze(path)

    def test_not_found_hold(self):
        with fixture([('README.txt', b'empty', 'file')]) as path:
            with self.assertRaisesRegex(r.Hold, 'OFFICIAL_ARCHIVE_WARIO_CONFIG_NOT_LOCATED_HOLD'):
                r.analyze(path)

    def test_symlink_archive_hold(self):
        with fixture([('README.txt', b'empty', 'file')]) as path:
            link = path.parent / 'link'
            link.symlink_to(path)
            with self.assertRaisesRegex(r.Hold, 'UNEXPECTED_AMAZON_SOURCE_FILENAME_HOLD'):
                r.analyze(link)

    def test_symlink_parent_hold(self):
        with fixture([('README.txt', b'empty', 'file')]) as path:
            alias = path.parent / 'alias'
            alias.symlink_to(path.parent, target_is_directory=True)
            with self.assertRaisesRegex(r.Hold, 'LOCAL_ARCHIVE_SYMLINK_HOLD'):
                r.analyze(alias / path.name)

    def test_nonregular_tar_member_not_extracted(self):
        with fixture([('arch/arm/configs/imx60_wario_defconfig', DATA, 'link')]) as path:
            with self.assertRaisesRegex(r.Hold, 'OFFICIAL_ARCHIVE_WARIO_CONFIG_NOT_LOCATED_HOLD'):
                r.analyze(path)

    def test_conflicting_config_duplicates_hold(self):
        nested = pack_tar([('linux/arch/arm/configs/imx60_wario_defconfig', b'x'*10, 'file')], 'w:bz2')
        with fixture([('arch/arm/configs/imx60_wario_defconfig', DATA, 'file'),('gplresults/linux-test.tar.bz2', nested, 'file')]) as path:
            with self.assertRaisesRegex(r.Hold, 'OFFICIAL_ARCHIVE_WARIO_CONFIG_AMBIGUOUS_HOLD'):
                r.analyze(path)

    def test_duplicate_identical_config_hold(self):
        with fixture([('arch/arm/configs/imx60_wario_defconfig', DATA, 'file'),
                      ('linux/arch/arm/configs/imx60_wario_defconfig', DATA, 'file')]) as path:
            with mock.patch.object(r, 'PIN_BLOB', r.git_blob(DATA)), mock.patch.object(r, 'PIN_SIZE', len(DATA)):
                with self.assertRaisesRegex(r.Hold, 'OFFICIAL_ARCHIVE_WARIO_CONFIG_AMBIGUOUS_HOLD'):
                    r.analyze(path)

    def test_direct_symlink_archive_hold(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'real.tar.gz'
            target.write_bytes(pack_tar([('README.txt', b'empty', 'file')], 'w:gz'))
            alias = Path(d) / r.OFFICIAL_ARCHIVE_NAME
            alias.symlink_to(target)
            with self.assertRaisesRegex(r.Hold, 'LOCAL_ARCHIVE_SYMLINK_HOLD'):
                r.analyze(alias)

    def test_disallowed_source_name_hold(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'unrelated.tar.gz'; p.write_bytes(b'junk')
            with self.assertRaisesRegex(r.Hold, 'UNEXPECTED_AMAZON_SOURCE_FILENAME_HOLD'):
                r.analyze(p)

    def test_corrupt_tar_hold(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / r.OFFICIAL_ARCHIVE_NAME; p.write_bytes(b'junk archive')
            with self.assertRaisesRegex(r.Hold, 'INVALID_ARCHIVE_HOLD'):
                r.analyze(p)

    def test_static_no_execution(self):
        text = SCRIPT.read_text()
        for term in ('subprocess', 'urllib', 'requests.', 'os.system', 'extractall(', 'exec('):
            self.assertNotIn(term, text)

if __name__ == '__main__':
    unittest.main()
