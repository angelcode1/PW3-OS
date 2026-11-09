"""Host-only R3877.87 tests; never connect to Kindle or execute staged ARM."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

import pw3_r3877_87_widget_dispatch as r


class Tests(unittest.TestCase):
    def fixture(self):
        return {name: b'elf-fixture:'+name.encode() for name in ('luajit',)+r.r83.NAMES}, \
               {name: b'lua-fixture:'+name.encode() for name in r.MODULES}

    def test_01_r86_source_pinned(self):
        self.assertTrue(r.pinned_source_ok())

    def test_02_exact_three_modules(self):
        self.assertEqual(set(r.MODULES), {
            'ui/event.lua','ui/widget/eventlistener.lua','ui/widget/widget.lua'})
        self.assertEqual(sum(x[1] for x in r.MODULES.values()), 3973)

    def test_03_git_blob_digest(self):
        value=b'abc'
        self.assertEqual(r.git_blob_sha1(value), hashlib.sha1(b'blob 3\0abc').hexdigest())

    def test_04_module_reader_checks_stage_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            (base/'opt').symlink_to('/etc')
            with self.assertRaises(r.Refused):
                r.read_stage_module(base,'opt/foo.lua',100,'x'*40)

    def test_05_module_reader_rejects_wrong_size(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'opt/app';p.mkdir(parents=True)
            (p/'test.lua').write_bytes(b'abc'*30)
            with self.assertRaises(r.Refused):
                r.read_stage_module(Path(d),'opt/app/test.lua',91,'x'*40)

    def test_06_module_reader_rejects_wrong_digest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'opt/app';p.mkdir(parents=True)
            (p/'test.lua').write_bytes(b'abc'*30)
            with self.assertRaises(r.Refused):
                r.read_stage_module(Path(d),'opt/app/test.lua',90,'x'*40)

    def test_07_module_reader_exact_content(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'opt/app';p.mkdir(parents=True)
            content=b'abc'*30
            (p/'test.lua').write_bytes(content)
            self.assertEqual(r.read_stage_module(Path(d),'opt/app/test.lua',len(content),r.git_blob_sha1(content)),content)

    def test_08_tar_regular_files_and_dirs(self):
        a,b=self.fixture()
        tar=r.tar_bundle(a,b)
        with tarfile.open(fileobj=io.BytesIO(tar),mode='r:') as tf:
            members={x.name:x for x in tf.getmembers()}
            self.assertEqual(set(members), set(a)|set(b)|{'ui','ui/widget'})
            self.assertTrue(all(members[x].isfile() for x in set(a)|set(b)))
            self.assertTrue(all(members[x].isdir() for x in ('ui','ui/widget')))
            self.assertTrue(all(members[x].linkname=='' for x in members))

    def test_09_shell_preserves_loader_gate(self):
        a,b=self.fixture()
        s=r.remote_script(a,b)
        self.assertEqual(s.count('--inhibit-rpath'),2)
        self.assertIn('--list "$work/luajit"',s)
        self.assertIn('R3877_87_KOREADER_WIDGET_DISPATCH_OK',s)
        self.assertNotIn('R3877_83_GLIBC_LUAJIT_OK',s)
        self.assertIn('pw3-r3877-87-$$',s)
        self.assertEqual(s.count('check_one ui/'),3)

    def test_10_remote_posix_sh_syntax(self):
        a,b=self.fixture()
        subprocess.run(['sh','-n'],input=r.remote_script(a,b).encode(),check=True)

    def test_11_cleanup_includes_all_module_files_and_dirs(self):
        a,b=self.fixture();s=r.remote_script(a,b)
        self.assertIn('ui/event.lua ui/widget/eventlistener.lua ui/widget/widget.lua; do rm -f',s)
        self.assertIn('rmdir "$work/ui/widget"',s)
        self.assertIn('rmdir "$work/ui"',s)
        self.assertIn('cleanup || exit 54',s)
        self.assertNotIn('mount -',s)
        self.assertNotIn('chroot',s)

    def test_12_no_opt_in_never_ssh(self):
        with patch.object(r.r83,'validate_stage',side_effect=AssertionError('unexpected stage scan')):
            with contextlib.redirect_stdout(io.StringIO()) as text:
                code=r.main(['--stage','/nonexistent'])
        j=json.loads(text.getvalue())
        self.assertEqual(code,2)
        self.assertFalse(j['device_execution_attempted'])
        self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')

    def test_13_bad_target_no_stage_scan(self):
        with patch.object(r.r83,'validate_stage',side_effect=AssertionError('no scan')):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code=r.main(['--stage','/nonexistent','--review-only','--target','root@x;id'])
        self.assertEqual(code,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'TARGET_OR_PORT_INVALID')

    def test_14_review_only_host_pass_no_ssh(self):
        a,b=self.fixture()
        with patch.object(r.r83,'validate_stage',return_value=(a,{'objects':{'luajit':{'rpath_resolution_categories':['a','b']}}})), \
             patch.object(r,'load_modules',return_value=b), \
             patch.object(r,'remote_script',return_value='abc'):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code=r.main(['--stage','/fixture','--review-only'],runner=lambda *x,**k:(_ for _ in ()).throw(AssertionError('SSH forbidden')))
        j=json.loads(out.getvalue())
        self.assertEqual(code,2)
        self.assertTrue(j['offline_validation_passed'])
        self.assertEqual(j['host_bundle_bytes'],sum(map(len,a.values()))+sum(map(len,b.values())))
        self.assertFalse(j['kindle_access_performed'])
        self.assertFalse(j['synthetic_event_dispatch_verified'])

    def test_15_live_mock_pass_still_not_bootable(self):
        a,b=self.fixture()
        res=Mock(returncode=0,stdout=r.MARKER,stderr=b'')
        with patch.object(r.r83,'validate_stage',return_value=(a,{'objects':{'luajit':{'rpath_resolution_categories':['a','b']}}})), \
             patch.object(r,'load_modules',return_value=b), \
             patch.object(r,'remote_script',return_value='abc'):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code=r.main(['--stage','/fixture','--acknowledge-one-shot-kindle-widget-dispatch'],runner=lambda *args,**kw:res)
        j=json.loads(out.getvalue())
        self.assertEqual(code,0)
        self.assertTrue(j['synthetic_event_dispatch_verified'])
        self.assertTrue(j['genuine_widget_dependency_require_verified'])
        self.assertFalse(j['complete_koreader_runtime_verified'])
        self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')

    def test_16_ssh_failure_redacted(self):
        a,b=self.fixture()
        res=Mock(returncode=255,stdout=b'',stderr=b'Permission denied (publickey,password).')
        with patch.object(r.r83,'validate_stage',return_value=(a,{'objects':{'luajit':{'rpath_resolution_categories':['a']}}})), \
             patch.object(r,'load_modules',return_value=b), \
             patch.object(r,'remote_script',return_value='abc'):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code=r.main(['--stage','/fixture','--acknowledge-one-shot-kindle-widget-dispatch'],runner=lambda *args,**kw:res)
        j=json.loads(out.getvalue())
        self.assertEqual(code,2)
        self.assertEqual(j['ssh_failure_category'],'AUTHENTICATION')
        self.assertFalse(j['tmpfs_cleanup_reported_complete'])
        self.assertNotIn('password',out.getvalue().lower())

    def test_17_source_pin_failure_refuses(self):
        with patch.object(r.r83,'validate_stage',side_effect=r.r83.Hold('PIN_UNVERIFIED')):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                code=r.main(['--stage','/fixture','--review-only'])
        self.assertEqual(code,2)
        self.assertFalse(json.loads(out.getvalue())['offline_validation_passed'])

    def test_18_lua_code_has_no_device_import(self):
        self.assertIn('require("ui/widget/widget")',r.LUA_CODE)
        self.assertIn('require("ui/event")',r.LUA_CODE)
        self.assertIn('NoSuchHandler',r.LUA_CODE)
        self.assertNotIn('ui/uimanager',r.LUA_CODE)
        self.assertNotIn('device',r.LUA_CODE)
        self.assertNotIn('paintTo(',r.LUA_CODE)


if __name__=='__main__':unittest.main()
