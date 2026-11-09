"""Host-only synthetic tests. No network, Kindle access or guest execution."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
import pw3_r3877_85_luajit_ffi as m


def synthetic():
    return ({'luajit':b'elf',**{n:b'elf' for n in m.r83.NAMES}},
            {'objects':{'luajit':{'rpath_resolution_categories':['x','y']}}})


class Tests(unittest.TestCase):
    def test_01_r83_source_pin(self):
        self.assertTrue(m.validate_original_source())
    def test_02_exact_source_marker_replaced(self):
        s=m.remote_shell(synthetic()[0]);self.assertEqual(s.count(m.NEW),1)
        self.assertNotIn('R3877_83_GLIBC_LUAJIT_OK',s)
    def test_03_ffi_targets_explicit_libm(self):
        s=m.remote_shell(synthetic()[0]);self.assertIn('ffi.load(assert(os.getenv("HOME")).."/libm.so.6")',s)
        self.assertIn('ffi.C.getpid()',s)
        self.assertIn('lm.cos(0.0)',s)
    def test_04_loader_mappings_still_required(self):
        s=m.remote_shell(synthetic()[0]);self.assertIn('--list "$work/luajit"',s)
        self.assertIn('--inhibit-rpath "luajit:$work/luajit"',s)
        self.assertIn('--library-path "$work"',s)
        self.assertIn('exit 51',s)
    def test_05_tmpfs_cleanup_preserved(self):
        s=m.remote_shell(synthetic()[0]);self.assertIn('cleanup || exit 54',s)
        self.assertIn('trap',s)
        self.assertIn('case "$mp:$kind" in /tmp:tmpfs',s)
    def test_06_remote_shell_syntax(self):
        s=m.remote_shell(synthetic()[0])
        r=subprocess.run(['sh','-n'],input=s,text=True,capture_output=True)
        self.assertEqual(r.returncode,0,r.stderr)
    def test_07_no_mounts_or_gui(self):
        s=m.remote_shell(synthetic()[0])
        for term in ('mount -','chroot','initctl','/dev/fb','epdc','mmcblk','/mnt/us'):
            self.assertNotIn(term,s)
    def test_08_default_no_stage_scan(self):
        with patch.object(m.r83,'validate_stage',side_effect=AssertionError('must not scan')):
            with contextlib.redirect_stdout(io.StringIO()) as o:
                rc=m.main(['--stage','/nonexistent'],runner=lambda *_a,**_k:1)
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(o.getvalue())['hold_category'],'EXPLICIT_OPT_IN_REQUIRED')
    def test_09_mutually_exclusive(self):
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc=m.main(['--stage','/nonexistent','--review-only','--acknowledge-one-shot-kindle-ffi-test'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(o.getvalue())['hold_category'],'MUTUALLY_EXCLUSIVE_MODES')
    def test_10_host_only_no_ssh(self):
        with patch.object(m.r83,'validate_stage',return_value=synthetic()):
            with contextlib.redirect_stdout(io.StringIO()) as o:
                rc=m.main(['--stage','/nonexistent','--review-only'],
                          runner=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('ssh forbidden')))
        j=json.loads(o.getvalue());self.assertEqual(rc,2)
        self.assertTrue(j['offline_validation_passed'])
        self.assertFalse(j['kindle_access_performed'])
        self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')
    def test_11_success_remains_not_bootable(self):
        with patch.object(m.r83,'validate_stage',return_value=synthetic()):
            with contextlib.redirect_stdout(io.StringIO()) as o:
                rc=m.main(['--stage','/none','--acknowledge-one-shot-kindle-ffi-test'],
                           runner=lambda *a,**kw: Mock(returncode=0,stdout=m.MARKER,stderr=b''))
        j=json.loads(o.getvalue());self.assertEqual(rc,0)
        self.assertTrue(j['ffi_libc_libm_calls_verified'])
        self.assertEqual(j['result'],'PASS_GLIBC_LUAJIT_FFI_LIBC_LIBM_SINGLE_PROCESS')
        self.assertFalse(j['koreader_gui_started']);self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')
    def test_12_wrong_output_hold(self):
        with patch.object(m.r83,'validate_stage',return_value=synthetic()):
            with contextlib.redirect_stdout(io.StringIO()) as o:
                rc=m.main(['--stage','/none','--acknowledge-one-shot-kindle-ffi-test'],
                          runner=lambda *a,**kw: Mock(returncode=0,stdout=b'wrong',stderr=b''))
        self.assertEqual(rc,2)
        self.assertFalse(json.loads(o.getvalue())['ffi_libc_libm_calls_verified'])
    def test_13_ssh_failure_classifies_no_raw_log(self):
        with patch.object(m.r83,'validate_stage',return_value=synthetic()):
            with contextlib.redirect_stdout(io.StringIO()) as o:
                rc=m.main(['--stage','/none','--acknowledge-one-shot-kindle-ffi-test'],
                          runner=lambda *a,**kw: Mock(returncode=255,stdout=b'',stderr=b'Permission denied for SECRET user'))
        j=json.loads(o.getvalue());self.assertEqual(rc,2)
        self.assertEqual(j['ssh_failure_category'],'AUTHENTICATION')
        self.assertNotIn('SECRET',o.getvalue())
    def test_14_no_injection_target(self):
        with contextlib.redirect_stdout(io.StringIO()) as o:
            rc=m.main(['--stage','/none','--acknowledge-one-shot-kindle-ffi-test','--target','root@bad;touch x'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(o.getvalue())['hold_category'],'TARGET_OR_PORT_INVALID')
    def test_15_timeout_hold_no_cleanup_claim(self):
        with patch.object(m.r83,'validate_stage',return_value=synthetic()):
            def timeout(*a,**kw):raise subprocess.TimeoutExpired('ssh',75)
            with contextlib.redirect_stdout(io.StringIO()) as o:
                rc=m.main(['--stage','/none','--acknowledge-one-shot-kindle-ffi-test'],runner=timeout)
        self.assertEqual(rc,2)
        j=json.loads(o.getvalue());self.assertEqual(j['hold_category'],'SSH_OR_TIMEOUT_CLEANUP_UNVERIFIED')
        self.assertFalse(j.get('tmpfs_cleanup_reported_complete',False))
    def test_16_changed_r83_refused(self):
        with patch.object(m,'validate_original_source',return_value=False):
            with contextlib.redirect_stdout(io.StringIO()) as o:
                rc=m.main(['--stage','/none','--review-only'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(o.getvalue())['hold_category'],'HOST_ELF_OR_PINNED_SOURCE_REVIEW_REFUSED')

if __name__=='__main__':unittest.main()
