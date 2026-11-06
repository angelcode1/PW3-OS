import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
PATH=HERE/'R4043762-PUBLIC-WARIO-KERNEL-REFERENCE-READONLY.py'
spec=importlib.util.spec_from_file_location('r3762',PATH)
r=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

CFG=("#\n# Automatically generated make config: don't edit\n"
     "# Linux/arm 3.0.35 Kernel Configuration\n"
     "CONFIG_AEABI=y\n# CONFIG_SECCOMP is not set\nCONFIG_OTHER_OPTION=\"x\"\n").encode()

class SourcePinTest(unittest.TestCase):
    def test_source_digest(self):
        import hashlib
        self.assertEqual(len(r.REFERENCE_BLOB_SHA1),40)
        self.assertEqual(len(r.REFERENCE_COMMIT),40)
        self.assertEqual(len(r.EXPECTED),sum(map(len,r.FEATURES.values())))
        self.assertEqual(set(r.EXPECTED),set(v for vals in r.FEATURES.values() for v in vals))
        self.assertEqual(r.REFERENCE_BLOB_SIZE,59582)
        self.assertEqual(r.REFERENCE_PATH,'arch/arm/configs/imx60_wario_defconfig')
    def test_git_blob_formula(self):
        import hashlib
        self.assertEqual(r.git_blob_id(b'hello\n'),hashlib.sha1(b'blob 6\x00hello\n').hexdigest())
    def test_rejects_modified_blob(self):
        with self.assertRaisesRegex(r.Hold,'PINNED_PUBLIC_REFERENCE_BLOB_MISMATCH_HOLD'):
            r.require_reference_blob(CFG)
    def test_pin_invariants(self):
        with mock.patch.object(r,'REFERENCE_BLOB_SIZE',len(CFG)),mock.patch.object(r,'REFERENCE_BLOB_SHA1',r.git_blob_id(CFG)):
            self.assertIsNone(r.require_reference_blob(CFG))
    def test_audit_data_synthetic_pinned(self):
        with mock.patch.object(r,'REFERENCE_BLOB_SIZE',len(CFG)),mock.patch.object(r,'REFERENCE_BLOB_SHA1',r.git_blob_id(CFG)),mock.patch.object(r,'EXPECTED',{'CONFIG_AEABI':'ENABLED','CONFIG_SECCOMP':'NOT_SET'}),mock.patch.object(r,'FEATURES',{'GROUP':('CONFIG_AEABI','CONFIG_SECCOMP')}):
            v=r.audit_bytes(CFG)
            self.assertEqual(v['result'],'PUBLIC_WARIO_KERNEL_CONFIG_REFERENCE_STATIC_ONLY')
            self.assertFalse(v['boot_authorized'])
            self.assertFalse(v['actual_pw3_running_kernel_config_verified'])
            self.assertEqual(v['immutable_hold'],'NOT_BOOTABLE')
    def test_wrong_feature_table_hold(self):
        with mock.patch.object(r,'REFERENCE_BLOB_SIZE',len(CFG)),mock.patch.object(r,'REFERENCE_BLOB_SHA1',r.git_blob_id(CFG)),mock.patch.object(r,'EXPECTED',{'CONFIG_AEABI':'NOT_SET'}),mock.patch.object(r,'FEATURES',{'GROUP':('CONFIG_AEABI',)}):
            with self.assertRaisesRegex(r.Hold,'REFERENCE_FEATURE_TABLE_DISAGREEMENT_HOLD'):
                r.audit_bytes(CFG)

class ParserTest(unittest.TestCase):
    def test_configuration(self):
        obj=r.parse_configuration(CFG)
        self.assertEqual(obj['CONFIG_AEABI'],'ENABLED')
        self.assertEqual(obj['CONFIG_SECCOMP'],'NOT_SET')
        self.assertEqual(obj['CONFIG_OTHER_OPTION'],'OTHER_VALUE')
        self.assertNotIn('CONFIG_MISSING',obj)
    def test_not_declared(self):
        a,drift=r.report_feature_groups({'CONFIG_AEABI':'ENABLED'})
        self.assertEqual(a['TLS_METADATA_FOLLOWUP']['CONFIG_TLS_REG_EMUL'],'NOT_DECLARED')
        self.assertGreater(drift,0)
    def test_duplicate_positive_option(self):
        with self.assertRaisesRegex(r.Hold,'REFERENCE_DUPLICATE_OPTION_HOLD'):
            r.parse_configuration(CFG+b'CONFIG_AEABI=y\n')
    def test_duplicate_unset_option(self):
        with self.assertRaisesRegex(r.Hold,'REFERENCE_DUPLICATE_OPTION_HOLD'):
            r.parse_configuration(CFG+b'# CONFIG_SECCOMP is not set\n')
    def test_conflicting_option(self):
        with self.assertRaisesRegex(r.Hold,'REFERENCE_DUPLICATE_OPTION_HOLD'):
            r.parse_configuration(CFG+b'CONFIG_SECCOMP=y\n')
    def test_rejects_empty_option(self):
        with self.assertRaisesRegex(r.Hold,'REFERENCE_INVALID_OPTION_HOLD'):
            r.parse_configuration(CFG+b'CONFIG_EXTRA=\n')
    def test_rejects_huge_option(self):
        with self.assertRaisesRegex(r.Hold,'REFERENCE_INVALID_OPTION_HOLD'):
            r.parse_configuration(CFG+(b'CONFIG_EXTRA='+b'X'*257+b'\n'))
    def test_module(self):
        self.assertEqual(r.parse_configuration(CFG+b'CONFIG_MOD=m\n')['CONFIG_MOD'],'MODULE')
    def test_n_literal(self):
        self.assertEqual(r.parse_configuration(CFG+b'CONFIG_N=n\n')['CONFIG_N'],'NOT_SET')
    def test_noncanonical_crlf(self):
        with self.assertRaisesRegex(r.Hold,'REFERENCE_NONCANONICAL_TEXT_HOLD'):
            r.parse_configuration(CFG.replace(b'\n',b'\r\n'))
    def test_embedded_nul(self):
        with self.assertRaisesRegex(r.Hold,'REFERENCE_NONCANONICAL_TEXT_HOLD'):
            r.parse_configuration(CFG+b'\x00')
    def test_invalid_utf8(self):
        with self.assertRaisesRegex(r.Hold,'REFERENCE_NOT_UTF8_HOLD'):
            r.parse_configuration(CFG+b'\xff')
    def test_missing_magic(self):
        with self.assertRaisesRegex(r.Hold,'REFERENCE_CONFIG_HEADER_HOLD'):
            r.parse_configuration(CFG[2:])
    def test_missing_version(self):
        with self.assertRaisesRegex(r.Hold,'REFERENCE_KERNEL_VERSION_HEADER_HOLD'):
            r.parse_configuration(CFG.replace(b'3.0.35',b'4.0.35'))
    def test_duplicate_after_comment(self):
        with self.assertRaisesRegex(r.Hold,'REFERENCE_DUPLICATE_OPTION_HOLD'):
            r.parse_configuration(CFG+b'CONFIG_AEABI=n\n')

class IOTEST(unittest.TestCase):
    def test_nofollow_regular(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config'; p.write_bytes(CFG)
            self.assertEqual(r.read_nofollow(p),CFG)
    def test_missing_hold(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(r.Hold,'REFERENCE_INPUT_MISSING_HOLD'):
                r.read_nofollow(Path(d)/'notfound')
    def test_symlink_input_hold(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data';p.write_bytes(CFG)
            link=Path(d)/'link';link.symlink_to(p)
            with self.assertRaisesRegex(r.Hold,'REFERENCE_PATH_SYMLINK_HOLD'):
                r.read_nofollow(link)
    def test_symlink_parent_hold(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data';p.mkdir();(p/'config').write_bytes(CFG)
            link=Path(d)/'link';link.symlink_to(p, target_is_directory=True)
            with self.assertRaisesRegex(r.Hold,'REFERENCE_PATH_SYMLINK_HOLD'):
                r.read_nofollow(link/'config')
    def test_directory_hold(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(r.Hold,'REFERENCE_NONREGULAR_OR_SIZE_HOLD'):
                r.read_nofollow(Path(d))
    def test_empty_hold(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'empty';p.write_bytes(b'')
            with self.assertRaisesRegex(r.Hold,'REFERENCE_NONREGULAR_OR_SIZE_HOLD'):
                r.read_nofollow(p)
    def test_too_large_hold(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'large';p.write_bytes(b'A'*(r.MAX_SIZE+1))
            with self.assertRaisesRegex(r.Hold,'REFERENCE_NONREGULAR_OR_SIZE_HOLD'):
                r.read_nofollow(p)
    def test_mtime_changed_hold(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config';p.write_bytes(CFG)
            org=os.fstat
            index=[0]
            def mutate(fd):
                st=org(fd)
                index[0]+=1
                if index[0]==2:
                    class Changed:
                        st_dev=st.st_dev;st_ino=st.st_ino;st_size=st.st_size;st_mtime_ns=st.st_mtime_ns+1
                    return Changed()
                return st
            with mock.patch.object(r.os,'fstat',side_effect=mutate):
                with self.assertRaisesRegex(r.Hold,'REFERENCE_CHANGED_DURING_READ_HOLD'):
                    r.read_nofollow(p)
    def test_stdout_does_not_export_local_path(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config';p.write_bytes(CFG)
            from io import StringIO
            with mock.patch.object(r,'REFERENCE_BLOB_SIZE',len(CFG)),mock.patch.object(r,'REFERENCE_BLOB_SHA1',r.git_blob_id(CFG)),mock.patch.object(r,'EXPECTED',{'CONFIG_AEABI':'ENABLED'}),mock.patch.object(r,'FEATURES',{'GROUP':('CONFIG_AEABI',)}):
                with mock.patch('sys.stdout',new_callable=StringIO) as out:
                    code=r.main(['--reference-defconfig',str(p)])
                self.assertEqual(code,0)
                self.assertNotIn(str(p),out.getvalue())
                self.assertIn('NOT_BOOTABLE',out.getvalue())
    def test_mismatch_hold_stdout(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config';p.write_bytes(CFG)
            from io import StringIO
            with mock.patch('sys.stdout',new_callable=StringIO) as out:
                code=r.main(['--reference-defconfig',str(p)])
            self.assertEqual(code,2)
            self.assertIn('PINNED_PUBLIC_REFERENCE_BLOB_MISMATCH_HOLD',out.getvalue())
            self.assertNotIn(str(p),out.getvalue())
    def test_no_network_or_execution(self):
        import inspect
        source=inspect.getsource(r)
        for forbidden in ['urllib', 'requests.', 'subprocess.', 'os.system', 'shutil.copy', 'open_url']:
            self.assertNotIn(forbidden,source)

if __name__ == '__main__':
    unittest.main()
