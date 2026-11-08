#!/usr/bin/env python3
"""Host-only tests for R3877.51.1; no SSH, Docker, or Kindle access."""
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import pw3_r3877_51_1_live_symbol_historical_config as m

ROOT=Path(__file__).parent
LIVE=(ROOT/'R3877_51_LIVE_SANITIZED_RECEIPT.txt').read_bytes()
PRIOR=(ROOT/'R3877_21_PRIOR_USER_REPORTED_INPUT.json').read_bytes()


class TestAudit(unittest.TestCase):
    def test_pins(self):
        self.assertEqual(hashlib.sha256(LIVE).hexdigest(),m.LIVE_SHA256)
        self.assertEqual(m.git_blob(PRIOR),m.PRIOR_BLOB_SHA1)
    def test_real_attached_receipt(self):
        r=m.assess(LIVE,PRIOR)
        self.assertTrue(r['result'].startswith('PASS_'))
        self.assertEqual(r['selected_live_kernel_symbols_present'],14)
        self.assertEqual(r['historical_reported_config_known_count'],14)
        self.assertEqual(r['live_config_known_count'],0)
        self.assertFalse(r['live_kernel_config_verified'])
        self.assertFalse(r['actual_vendor_syscall_dispatch_verified'])
        self.assertEqual(r['immutable_hold'],'NOT_BOOTABLE')
    def test_preflight_zero_external_calls(self):
        with patch.object(subprocess,'run',side_effect=AssertionError('no subprocess allowed')):
            stream=io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(m.main([]),2)
            r=json.loads(stream.getvalue())
            self.assertEqual(r['result'],'HOLD')
            self.assertFalse(r['physical_device_access_performed'])
    def test_only_one_arg_is_hold(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(m.main(['--live-receipt','sample']),2)
    def test_input_paths_pass(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(m.main(['--live-receipt',str(ROOT/'R3877_51_LIVE_SANITIZED_RECEIPT.txt'),
                                     '--historical-r21-json',str(ROOT/'R3877_21_PRIOR_USER_REPORTED_INPUT.json')]),0)
    def test_live_sha_tamper_rejected(self):
        with self.assertRaisesRegex(m.EvidenceHold,'LIVE_RECEIPT_SHA256_MISMATCH'):
            m.assess(LIVE+b' ',PRIOR)
    def test_prior_git_blob_tamper_rejected(self):
        with self.assertRaisesRegex(m.EvidenceHold,'PRIOR_GIT_BLOB_SHA1_MISMATCH'):
            m.assess(LIVE,PRIOR+b' ')
    def test_src_has_no_ssh_network_docker(self):
        src=Path(m.__file__).read_text()
        for banned in ('import subprocess','import socket','import requests','import urllib','os.system(', 'subprocess.run(', 'SSH_PASSWORD', 'root@'):
            self.assertNotIn(banned,src)
        self.assertNotIn('0x',json.dumps(m.preflight()))
    def test_raw_live_parser(self):
        x,c,s=m.read_receipt(LIVE)
        self.assertEqual((x['RELEASE'],x['MACHINE']),('3.0.35-lab126','armv7l'))
        self.assertEqual(len(c),18)
        self.assertEqual(len(s),14)
    def test_prior_parser(self):
        p=m.read_prior(PRIOR)
        self.assertEqual(p['kconfig_status'],'AVAILABLE')
        self.assertEqual(len(p['kconfig']),14)
        self.assertEqual(p['kconfig']['CONFIG_SECCOMP'],'DISABLED')


class TestMalformed(unittest.TestCase):
    def bad(self,receipt,cat):
        with self.assertRaisesRegex(m.EvidenceHold,cat):
            m.read_receipt(receipt if isinstance(receipt,bytes) else receipt.encode())
    def test_empty(self): self.bad(b'','RECEIPT_BYTES_INVALID')
    def test_trailing_space(self): self.bad(LIVE+b'x','RECEIPT_CONTROL_OR_NEWLINE_INVALID')
    def test_bad_utf8(self): self.bad(LIVE[:-1]+b'\xff\n','RECEIPT_ENCODING_INVALID')
    def test_crlf(self): self.bad(LIVE.replace(b'\n',b'\r\n'),'RECEIPT_CONTROL_OR_NEWLINE_INVALID')
    def test_nul(self): self.bad(LIVE.replace(b'armv7l',b'arm\x00v7l'),'RECEIPT_CONTROL_OR_NEWLINE_INVALID')
    def test_invalid_begin(self): self.bad(LIVE.replace(b'PW3_R51_BEGIN',b'PW3_R51_OTHER'),'RECEIPT_SENTINEL_INVALID')
    def test_invalid_end(self): self.bad(LIVE.replace(b'PW3_R51_END',b'PW3_R51_OTHER'),'RECEIPT_SENTINEL_INVALID')
    def test_unknown_line(self): self.bad(LIVE.replace(b'CONFIG_SOURCE|UNAVAILABLE',b'CONFIG_SOURCE|UNAVAILABLE\nUNKNOWN|999'), 'RECEIPT_LINE_NOT_ALLOWLISTED')
    def test_double_scalar(self): self.bad(LIVE.replace(b'RELEASE|3.0.35-lab126',b'RELEASE|3.0.35-lab126\nRELEASE|3.0.35-lab126'), 'DUPLICATE_SCALAR')
    def test_double_cfg(self): self.bad(LIVE.replace(b'CFG|CONFIG_FUTEX|UNKNOWN',b'CFG|CONFIG_FUTEX|UNKNOWN\nCFG|CONFIG_FUTEX|UNKNOWN'), 'DUPLICATE_CONFIG')
    def test_double_sym(self): self.bad(LIVE.replace(b'SYM|sys_brk|PRESENT',b'SYM|sys_brk|PRESENT\nSYM|sys_brk|PRESENT'), 'DUPLICATE_SYMBOL')
    def test_missing_cfg(self): self.bad(LIVE.replace(b'CFG|CONFIG_FUTEX|UNKNOWN\n',b''),'RECEIPT_FIELDS_INCOMPLETE')
    def test_missing_sym(self): self.bad(LIVE.replace(b'SYM|sys_brk|PRESENT\n',b''),'RECEIPT_FIELDS_INCOMPLETE')
    def test_mismatch_release(self): self.bad(LIVE.replace(b'3.0.35-lab126',b'6.7.0-lab126'),'RUNNING_KERNEL_BASELINE_CHANGED')
    def test_mismatch_arch(self): self.bad(LIVE.replace(b'armv7l',b'arm64'),'RUNNING_KERNEL_BASELINE_CHANGED')
    def test_config_unexpected(self): self.bad(LIVE.replace(b'CONFIG_SOURCE|UNAVAILABLE',b'CONFIG_SOURCE|PROC_CONFIG_GZ'),'RECEIPT_CONFIG_EXPECTATION_MISMATCH')
    def test_config_known_unexpected(self): self.bad(LIVE.replace(b'CFG|CONFIG_FUTEX|UNKNOWN',b'CFG|CONFIG_FUTEX|y'),'RECEIPT_CONFIG_EXPECTATION_MISMATCH')
    def test_symbol_missing(self): self.bad(LIVE.replace(b'SYM|sys_brk|PRESENT',b'SYM|sys_brk|ABSENT'),'RECEIPT_SYMBOLS_NOT_ALL_PRESENT')
    def test_symbol_source_missing(self): self.bad(LIVE.replace(b'KALLSYMS_SOURCE|AVAILABLE',b'KALLSYMS_SOURCE|UNAVAILABLE'),'RECEIPT_SYMBOLS_NOT_ALL_PRESENT')
    def test_prior_bad_kernel(self):
        p=json.loads(PRIOR);p['kernel_release']='1.0'
        with self.assertRaisesRegex(m.EvidenceHold,'PRIOR_BASELINE_INCONSISTENT'):
            m.read_prior(json.dumps(p).encode())
    def test_prior_bad_source(self):
        p=json.loads(PRIOR);p['source']='Invented'
        with self.assertRaisesRegex(m.EvidenceHold,'PRIOR_ORIGIN_INVALID'):
            m.read_prior(json.dumps(p).encode())
    def test_prior_bad_config(self):
        p=json.loads(PRIOR);p['kconfig']['CONFIG_AEABI']='UNSUPPORTED'
        with self.assertRaisesRegex(m.EvidenceHold,'PRIOR_CONFIG_INVALID'):
            m.read_prior(json.dumps(p).encode())
    def test_prior_bad_scope(self):
        p=json.loads(PRIOR);p['recovery_verified']=True
        with self.assertRaisesRegex(m.EvidenceHold,'PRIOR_SCOPE_INCONSISTENT'):
            m.read_prior(json.dumps(p).encode())
    def test_symlink_path_denied(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'alias';p.symlink_to(ROOT/'R3877_51_LIVE_SANITIZED_RECEIPT.txt')
            with self.assertRaisesRegex(m.EvidenceHold,'INPUT_MISSING_SYMLINK_OR_SIZE'):
                m.safe_bytes(p,8192)
    def test_absent_path_denied(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(m.EvidenceHold,'INPUT_MISSING_SYMLINK_OR_SIZE'):
                m.safe_bytes(Path(d)/'missing',8192)

if __name__=='__main__': unittest.main()
