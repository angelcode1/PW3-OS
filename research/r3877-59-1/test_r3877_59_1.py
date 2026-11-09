#!/usr/bin/env python3
"""Host-only, synthetic diagnostic regression. No Docker daemon / QEMU / Kindle."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import pw3_r3877_59_1_failure_diagnostic as d

class Tests(unittest.TestCase):
    def probe(self,status='HOLD',rc=12):
        return dict(status=status,exit_code=rc,
                    output_sha256='a'*64,program_output_sha256='b'*64,
                    program_output_bytes=29,expected_applet_output_matches=False)
    def base(self,rc=12):
        return dict(result='HOLD',error_category='GUEST_PROBE_FAILED:r59_probe_control',
            all_created_containers_removed=True,original_image_unchanged=True,
            authorized_qemu_execution_performed=True,writable_fallback_used=True,
            read_only_copy_probe={'classification':'READONLY_ROOTFS_COPY_REJECTED'},
            runtime_probes={'qemu_version':self.probe('PASS',0),
             'busybox_true_control':self.probe('PASS',0),
             'r59_probe_control':self.probe('HOLD',rc)})
    def test_01_pinned_source_and_binary(self): self.assertIsNone(d.pin_check())
    def test_02_r59_source_hash(self):self.assertEqual(hashlib.sha256(Path(d.r59.__file__).read_bytes()).hexdigest(),d.R59_SCRIPT_SHA256)
    def test_03_pinned_elf_kept(self):self.assertTrue(d.r59.require_pinned())
    def test_04_immutable_hold(self):self.assertEqual(d.base_report()['immutable_hold'],'NOT_BOOTABLE')
    def test_05_no_docker_default(self):self.assertFalse(d.base_report()['docker_used'])
    def test_06_no_kindle(self):self.assertEqual(d.base_report()['kindle_ssh_sessions'],0)
    def test_07_no_firmware(self):self.assertFalse(d.base_report()['firmware_write_performed'])
    def test_08_r59_control_failure_marker(self):
        x={};self.assertFalse(d.classified_output('r59_probe_control',12,'R59_FAIL_PTHREAD_CREATE\n',d.r59.control_output_ok,x));self.assertEqual(x['control_output']['allowlisted_program_markers'],['R59_FAIL_PTHREAD_CREATE'])
    def test_09_other_output_redacted(self):
        out='R59_PASS_ARMV7_PTHREAD_TLS\nsecret-private-path\n'
        x={};d.classified_output('r59_probe_control',13,out,d.r59.control_output_ok,x)
        self.assertEqual(x['control_output']['unrecognized_line_count'],1)
        self.assertNotIn('secret-private-path',json.dumps(x))
    def test_10_exact_stdout_success(self):
        x={};self.assertTrue(d.classified_output('r59_probe_control',0,d.r59.EXPECTED_OUTPUT,d.r59.control_output_ok,x));self.assertTrue(x['control_output']['expected_exact_output_matched'])
    def test_11_unrecognized_lines_not_printed(self):
        x={};d.classified_output('r59_probe_control',127,'Error loading /secret/app\n',d.r59.control_output_ok,x);self.assertEqual(x['control_output']['unrecognized_line_count'],1);self.assertNotIn('/secret/app',json.dumps(x))
    def test_12_not_control_no_diagnostic(self):
        x={};d.classified_output('busybox_true_control',0,'',d.r59.control_output_ok,x);self.assertEqual(x,{})
    def test_13_no_unknown_marker(self):
        x={};d.classified_output('r59_probe_control',14,'FAKE_PASS\n',d.r59.control_output_ok,x);self.assertEqual(x['control_output']['allowlisted_program_markers'],[])
    def test_14_control_exit_code(self):
        x={};d.classified_output('r59_probe_control',139,'',d.r59.control_output_ok,x);self.assertEqual(x['control_output']['exit_code'],139)
    def test_15_base_r49_failure_visible(self):
        x=d.sanitized_r49_details(self.base());self.assertEqual(x['base_error_category'],'GUEST_PROBE_FAILED:r59_probe_control');self.assertEqual(x['baseline_probe_statuses']['r59_probe_control']['exit_code'],12)
    def test_16_base_no_secret_fields(self):
        raw=self.base();raw['runtime_probes']['r59_probe_control']['secret']='private';raw['something_else']='nope'
        text=json.dumps(d.sanitized_r49_details(raw));self.assertNotIn('private',text);self.assertNotIn('nope',text)
    def test_17_base_unknown_error_sanitized(self):
        raw=self.base();raw['error_category']='USER_PRIVATE_DATA';self.assertEqual(d.sanitized_r49_details(raw)['base_error_category'],'OTHER_HOLD')
    def test_18_base_wrong_type(self):
        with self.assertRaises(ValueError):d.sanitized_r49_details([])
    def test_19_base_missing_probes(self):
        raw=self.base();del raw['runtime_probes'];self.assertEqual(d.sanitized_r49_details(raw)['baseline_probe_statuses'],{})
    def test_20_base_invalid_exit_code(self):
        raw=self.base();raw['runtime_probes']['r59_probe_control']['exit_code']='no';self.assertIsNone(d.sanitized_r49_details(raw)['baseline_probe_statuses']['r59_probe_control']['exit_code'])
    def test_21_hash_format_rejected(self):
        raw=self.base();raw['runtime_probes']['r59_probe_control']['output_sha256']='garbage';self.assertNotIn('output_sha256',d.sanitized_r49_details(raw)['baseline_probe_statuses']['r59_probe_control'])
    def test_22_readonly_classification_limited(self):
        raw=self.base();raw['read_only_copy_probe']['classification']='PRIVATE_TEXT';self.assertEqual(d.sanitized_r49_details(raw)['read_only_copy_classification'],'UNKNOWN')
    def test_23_cli_no_opt_in(self):
        with patch.object(d.r59.r49,'docker',side_effect=AssertionError('NO Docker')):
            x=io.StringIO()
            with redirect_stdout(x):self.assertEqual(d.main([]),2)
            self.assertEqual(json.loads(x.getvalue())['result'],'HOLD')
    def test_24_cli_writable_only_no_execute(self):
        with patch.object(d,'execute',side_effect=AssertionError('must not invoke')):
            x=io.StringIO()
            with redirect_stdout(x):self.assertEqual(d.main(['--allow-disposable-writable-layer']),2)
            self.assertEqual(json.loads(x.getvalue())['hold_category'],'WRITABLE_OPT_IN_REQUIRES_QEMU_AUTHORIZATION')
    def test_25_cli_authorized(self):
        with patch.object(d,'execute',return_value={'result':'HOLD'}) as mocked:
            with redirect_stdout(io.StringIO()):self.assertEqual(d.main(['--authorize-offline-qemu','--allow-disposable-writable-layer']),2)
            mocked.assert_called_once_with(True)
    def test_26_hold_uses_real_r59_without_promoting(self):
        with patch.object(d.r59.r49,'run',return_value=self.base(12)):
            x=d.execute(True)
        self.assertEqual(x['result'],'HOLD');self.assertEqual(x['diagnostics']['baseline_probe_statuses']['r59_probe_control']['exit_code'],12)
        self.assertTrue(x['all_created_containers_removed']);self.assertTrue(x['original_image_unchanged'])
    def test_27_bad_r59_script_hash_blocks_any_invocation(self):
        with patch.object(d,'R59_SCRIPT_SHA256','0'*64):
            with patch.object(d.r59.r49,'docker',side_effect=AssertionError('never')):
                x=d.execute(True)
        self.assertEqual(x['result'],'HOLD');self.assertIn('PINNED_R59_SCRIPT_CHANGED',x['hold_category'])
    def test_28_no_end_to_end_pass_without_r59_pass(self):
        with patch.object(d.r59.r49,'run',return_value=self.base(0)):
            x=d.execute(True)
        self.assertNotEqual(x['result'],d.PASS)
    def test_29_probe_output_oversize(self):
        with self.assertRaisesRegex(ValueError,'OVERSIZE'):
            d.classified_output('r59_probe_control',1,'x'*1000001,d.r59.control_output_ok,{})
    def test_30_very_long_status_redacted(self):
        raw=self.base();raw['runtime_probes']['r59_probe_control']['status']='SECRET_PATH';s=d.sanitized_r49_details(raw);self.assertEqual(s['baseline_probe_statuses']['r59_probe_control']['status'],'UNKNOWN')
    def test_31_original_r59_pass_whitelist(self):
        self.assertEqual(d.PASS,'PASS_R59_PINNED_QEMU_PTHREAD_TLS_CONTROL_WITH_DIAGNOSTIC_ONLY')
    def test_32_trace_presence_false_no_fake(self):
        self.assertNotIn('r59_probe_trace',d.sanitized_r49_details(self.base())['baseline_probe_statuses'])

if __name__=='__main__':unittest.main()
