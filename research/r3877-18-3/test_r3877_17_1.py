import hashlib
import io
import json
import tarfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from subprocess import CompletedProcess
import pw3_r3877_17_2_single_ssh_audit as m

def archive(entries):
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:') as t:
        for name,val in entries:
            ti=tarfile.TarInfo(name)
            if isinstance(val,tuple):
                ti.type=tarfile.SYMTYPE;ti.linkname=val[1];t.addfile(ti)
            else:
                ti.size=len(val);t.addfile(ti,io.BytesIO(val))
    return buf.getvalue()

def fixture():
    # All these are synthetic data; parsing archive must not interpret them as real ELF.
    a=archive([('fbink',b'A'*60),('luajit',b'B'*60),('libs/a.so',b'C'*60),('libs/b.so',('link','a.so'))])
    b=archive([('lib/'+name,b'D'*64) for name in m.syslib.NAMES])
    return a+b

class Tests(unittest.TestCase):
    def test_preflight_never_ssh(self):
        out=io.StringIO()
        with patch.object(m,'one_session_collect',side_effect=AssertionError('ssh invoked')):
            with redirect_stdout(out): rc=m.main([])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'EXPLICIT_READONLY_SSH_AUTHORIZATION_REQUIRED')
    def test_reject_unknown_target_before_ssh(self):
        out=io.StringIO()
        with patch.object(m,'one_session_collect',side_effect=AssertionError('ssh invoked')):
            with redirect_stdout(out): rc=m.main(['--target','root@other','--authorize-live-readonly-ssh'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'UNEXPECTED_SSH_TARGET')
    def test_reject_bad_port_before_ssh(self):
        out=io.StringIO()
        with patch.object(m,'one_session_collect',side_effect=AssertionError('ssh invoked')):
            with redirect_stdout(out): rc=m.main(['--target',m.EXPECTED_TARGET,'-p','65536','--authorize-live-readonly-ssh'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'SSH_PORT_INVALID')
    def test_combined_two_tar_streams(self):
        a,b=m.parse_concatenated_archives(fixture())
        self.assertEqual(a['libs/b.so'],('symlink','a.so'))
        self.assertEqual(len(b),7)
    def test_reject_unexpected_member(self):
        a=archive([('fbink',b'A'*60),('luajit',b'B'*60),('documents/private.txt',b'X')])
        b=archive([('lib/'+n,b'D'*64) for n in m.syslib.NAMES])
        with self.assertRaisesRegex(m.Hold,'UNEXPECTED_ARCHIVE_PATH'):
            m.parse_concatenated_archives(a+b)
    def test_reject_absolute_symlink(self):
        a=archive([('fbink',b'A'*60),('luajit',b'B'*60),('libs/evil.so',('link','/etc/passwd'))])
        b=archive([('lib/'+n,b'D'*64) for n in m.syslib.NAMES])
        with self.assertRaisesRegex(m.Hold,'APP_SYMLINK_TARGET_UNSAFE'):
            m.parse_concatenated_archives(a+b)
    def test_reject_duplicate_system(self):
        a=archive([('fbink',b'A'*60),('luajit',b'B'*60)])
        b=archive([('lib/'+n,b'D'*64) for n in m.syslib.NAMES]+[('lib/libc.so.6',b'D'*64)])
        with self.assertRaisesRegex(m.Hold,'DUPLICATE_SYSTEM_ARCHIVE_MEMBER'):
            m.parse_concatenated_archives(a+b)
    def test_reject_missing_system(self):
        a=archive([('fbink',b'A'*60),('luajit',b'B'*60)])
        b=archive([('lib/'+n,b'D'*64) for n in m.syslib.NAMES[:-1]])
        with self.assertRaisesRegex(m.Hold,'SYSTEM_PROVIDER_SET_INCOMPLETE'):
            m.parse_concatenated_archives(a+b)
    def test_ssh_stderr_not_exposed(self):
        raw=b'Permission denied (publickey,password). /users/secrets/token PASSWORD_EXAMPLE'
        cp=CompletedProcess([],255,b'',raw)
        with patch.object(m.subprocess,'run',return_value=cp) as run:
            with self.assertRaises(m.Hold) as ctx:
                m.one_session_collect(m.EXPECTED_TARGET,2222)
        self.assertEqual(run.call_count,1)
        self.assertEqual(ctx.exception.evidence['ssh_error_class'],'SSH_AUTHENTICATION_FAILURE')
        self.assertNotIn('PASSWORD_EXAMPLE',repr(ctx.exception.evidence))
        self.assertEqual(ctx.exception.evidence['ssh_stderr_sha256'],hashlib.sha256(raw).hexdigest())
    def test_ssh_uses_single_session_fixed_target_and_readonly_shell(self):
        with patch.object(m.subprocess,'run',return_value=CompletedProcess([],0,fixture(),b'')) as run:
            m.one_session_collect(m.EXPECTED_TARGET,2222)
        self.assertEqual(run.call_count,1)
        args,kw=run.call_args
        self.assertIn('sh -s',args[0]);self.assertIn('2222',args[0])
        self.assertNotIn(b' rm ',kw['input']);self.assertEqual(kw['input'].count(b'tar -'),2)
        self.assertIn(b'tar -cf -',kw['input']);self.assertIn(b'tar -chf -',kw['input'])
    def test_ssh_fail_classes(self):
        self.assertEqual(m.classify_ssh_error(b'Connection refused',255),'SSH_CONNECTION_REFUSED')
        self.assertEqual(m.classify_ssh_error(b'Host key verification failed',255),'SSH_HOST_KEY_FAILURE')
        self.assertEqual(m.classify_ssh_error(b'unclassified message',255),'SSH_EXIT_255_UNCLASSIFIED')
    def test_main_success_metadata_only(self):
        out=io.StringIO()
        with patch.object(m,'one_session_collect',return_value=fixture()) as ssh,\
             patch.object(m.r17,'analyze',return_value={'version_requirements_statically_satisfied':True}),\
             redirect_stdout(out):
            rc=m.main(['--target',m.EXPECTED_TARGET,'--port','2222','--authorize-live-readonly-ssh'])
        o=json.loads(out.getvalue())
        self.assertEqual(rc,0);self.assertEqual(o['result'],'PASS_VERSION_NAMES_METADATA_ONLY')
        self.assertEqual(o['ssh_sessions_requested'],1)
        self.assertEqual(o['immutable_hold'],'NOT_BOOTABLE')
    def test_main_reject_missing_version(self):
        out=io.StringIO()
        with patch.object(m,'one_session_collect',return_value=fixture()),\
             patch.object(m.r17,'analyze',return_value={'version_requirements_statically_satisfied':False}),\
             redirect_stdout(out):
            rc=m.main(['--target',m.EXPECTED_TARGET,'--authorize-live-readonly-ssh'])
        o=json.loads(out.getvalue())
        self.assertEqual(rc,2)
        self.assertEqual(o['hold_category'],'MISSING_PROVIDER_OR_REQUIRED_SYMBOL_VERSION_NAME')
    def test_main_ssh_failure_has_classified_proof(self):
        out=io.StringIO()
        with patch.object(m,'one_session_collect',side_effect=m.Hold('SSH_COLLECTION_FAILED',ssh_exit_code=255,ssh_error_class='SSH_CONNECTION_CLOSED')), redirect_stdout(out):
            rc=m.main(['--target',m.EXPECTED_TARGET,'--authorize-live-readonly-ssh'])
        record=json.loads(out.getvalue())
        self.assertEqual(rc,2)
        self.assertEqual(record['hold_category'],'SSH_COLLECTION_FAILED')
        self.assertEqual(record['ssh_error_class'],'SSH_CONNECTION_CLOSED')
        self.assertEqual(record['immutable_hold'],'NOT_BOOTABLE')

if __name__=='__main__': unittest.main()
