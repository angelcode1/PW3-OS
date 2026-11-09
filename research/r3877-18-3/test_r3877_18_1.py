"""Read-only SSH diagnostics, mocked; no target/device access."""
import io
import json
import hashlib
import unittest
from contextlib import redirect_stdout
from subprocess import CompletedProcess,TimeoutExpired
from unittest.mock import patch
import r3877_18_1_ssh_diagnostic as d
import pw3_r3877_18_1_relocation_candidates as r

TARGET=d.original.EXPECTED_TARGET
class Tests(unittest.TestCase):
    def test_preflight_never_ssh(self):
        buf=io.StringIO()
        with patch.object(d.subprocess,'run',side_effect=AssertionError('network touched')):
            with redirect_stdout(buf): rc=r.main([])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(buf.getvalue())['immutable_hold'],'NOT_BOOTABLE')
    def test_no_ssh_for_bad_target(self):
        with patch.object(d.subprocess,'run',side_effect=AssertionError('network touched')):
            with redirect_stdout(io.StringIO()): rc=r.main(['--target','root@not-the-pw3','--authorize-live-readonly-ssh','--probe-ssh-only'])
        self.assertEqual(rc,2)
    def test_no_ssh_for_invalid_timeout(self):
        out=io.StringIO()
        with patch.object(d.subprocess,'run',side_effect=AssertionError('network touched')):
            with redirect_stdout(out): rc=r.main(['--target',TARGET,'--authorize-live-readonly-ssh','--probe-ssh-only','--connect-timeout','90'])
        self.assertEqual(rc,2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'SSH_CONNECT_TIMEOUT_INVALID')
    def test_probe_success(self):
        cp=CompletedProcess([],0,b'R3877_18_1_SSH_READY\n3.0.35-lab126\narmv7l\n',b'')
        out=io.StringIO()
        with patch.object(d.subprocess,'run',return_value=cp) as run:
            with redirect_stdout(out): rc=r.main(['--target',TARGET,'--authorize-live-readonly-ssh','--probe-ssh-only'])
        data=json.loads(out.getvalue())
        self.assertEqual(rc,0)
        self.assertEqual(data['result'],'PASS_SSH_HANDSHAKE_ONLY')
        self.assertFalse(data['app_and_stock_binary_contents_transferred'])
        self.assertEqual(data['ssh_sessions_requested'],1)
        self.assertIn('uname -m',run.call_args.args[0][-1])
    def test_bad_probe_response_holds(self):
        cp=CompletedProcess([],0,b'R3877_18_1_SSH_READY\nother\narmv7l\n',b'')
        with patch.object(d.subprocess,'run',return_value=cp):
            with self.assertRaisesRegex(d.Hold,'SSH_PROBE_UNEXPECTED_TARGET_RESPONSE'):
                d.probe_ssh_only(TARGET,2222,20)
    def test_reset_reports_partial_stdout_length_but_not_contents(self):
        stderr=b'kex_exchange_identification: read: Connection reset by peer\n'
        secret=b'ELF PRIVATE STREAM'
        with patch.object(d.subprocess,'run',return_value=CompletedProcess([],255,secret,stderr)):
            with self.assertRaises(d.Hold) as ctx:
                d.one_session_collect(TARGET,2222,20)
        evidence=ctx.exception.evidence
        self.assertEqual(evidence['ssh_error_class'],'SSH_CONNECTION_RESET')
        self.assertEqual(evidence['ssh_partial_stdout_bytes'],len(secret))
        self.assertNotIn('ELF PRIVATE STREAM',repr(evidence))
        self.assertEqual(evidence['ssh_stderr_sha256'],hashlib.sha256(stderr).hexdigest())
    def test_timeout_class_reported(self):
        with patch.object(d.subprocess,'run',side_effect=TimeoutExpired(['ssh'],180)):
            with self.assertRaisesRegex(d.Hold,'SSH_COMMAND_TIMEOUT'):
                d.one_session_collect(TARGET,2222,20)
    def test_single_ssh_for_collection(self):
        with patch.object(d.subprocess,'run',return_value=CompletedProcess([],0,b'archive',b'')) as run:
            d.one_session_collect(TARGET,2222,20)
        self.assertEqual(run.call_count,1)
        self.assertIn('sh -s',run.call_args.args[0])
        self.assertEqual(run.call_args.kwargs['input'],d.original.TARGET_SCRIPT.encode('ascii'))
    def test_ssh_error_classified_no_stderr_content(self):
        bad=b'Permission denied password123'
        with patch.object(d.subprocess,'run',return_value=CompletedProcess([],255,b'',bad)):
            with self.assertRaises(d.Hold) as ctx:d.probe_ssh_only(TARGET,2222,20)
        self.assertEqual(ctx.exception.evidence['ssh_error_class'],'SSH_AUTHENTICATION_FAILURE')
        self.assertNotIn('password123',repr(ctx.exception.evidence))

if __name__=='__main__':unittest.main()
