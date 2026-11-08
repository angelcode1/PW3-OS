#!/usr/bin/env python3
"""Offline only: no real SSH, Docker, or Kindle access."""
import contextlib
import hashlib
import io
import json
import subprocess
import unittest
from unittest.mock import patch
import pw3_r3877_51_kernel_metadata as m


def fixture(*, config_source='PROC_CONFIG_GZ', symbol_source='AVAILABLE', release='3.0.35-lab126', machine='armv7l', missing=()):
    out=['PW3_R51_BEGIN',f'RELEASE|{release}',f'MACHINE|{machine}',
         f'CONFIG_SOURCE|{config_source}']
    for key in m.CONFIG_KEYS:
        val='UNKNOWN' if config_source=='UNAVAILABLE' or key in missing else ('n' if key=='CONFIG_SECCOMP' else 'y')
        out.append(f'CFG|{key}|{val}')
    out.append(f'KALLSYMS_SOURCE|{symbol_source}')
    for name in m.SOURCE_ENTRY_SYMBOLS:
        val='UNKNOWN' if symbol_source=='UNAVAILABLE' else ('ABSENT' if name=='sys_newuname' else 'PRESENT')
        out.append(f'SYM|{name}|{val}')
    out.append('PW3_R51_END')
    return '\n'.join(out)+'\n'


class ParserTests(unittest.TestCase):
    def test_preflight_no_ssh(self):
        with patch.object(m,'collect',side_effect=AssertionError('SSH forbidden')):
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(m.main([]),2)
        d=json.loads(output.getvalue());self.assertEqual(d['result'],'HOLD')
        self.assertEqual(d['kindle_ssh_sessions'],0)
    def test_preflight_target_alone_does_not_connect(self):
        with patch.object(m,'collect',side_effect=AssertionError('SSH forbidden')):
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(m.main(['--target','root@192.168.1.5']),2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'SSH_AUTHORIZATION_REQUIRED')
    def test_valid_selected_evidence_pass(self):
        d=m.assess(fixture(),from_ssh=True)
        self.assertEqual(d['result'],'PASS_SELECTED_LIVE_KERNEL_CONFIG_AND_SYMBOL_NAMES_METADATA_ONLY')
        self.assertEqual(d['config_known_count'],len(m.CONFIG_KEYS))
        self.assertEqual(d['kallsyms_entry_present_count'],len(m.SOURCE_ENTRY_SYMBOLS)-1)
        self.assertTrue(d['physical_device_access_performed'])
        self.assertFalse(d['actual_vendor_syscall_dispatch_verified'])
        self.assertFalse(d['running_kernel_matches_public_source_verified'])
    def test_offline_receipt_no_device_access(self):
        d=m.assess(fixture(),from_ssh=False)
        self.assertEqual(d['kindle_ssh_sessions'],0)
        self.assertFalse(d['stock_userland_read_commands_requested'])
    def test_source_and_kernel_pins(self):
        self.assertEqual(m.EXPECTED_KERNEL,'3.0.35-lab126')
        self.assertEqual(m.SOURCE_HEADER_GIT_BLOB,'2c04ed5efeb50707ac3353958434d37691841839')
        self.assertEqual(m.SOURCE_CALLS_GIT_BLOB,'80f7896cc0164ad6f74469f1e777b90c1f306443')
        self.assertEqual(set(m.EXPECTED_NAME_TO_ENTRY.values()),set(m.SOURCE_ENTRY_SYMBOLS))
        self.assertEqual(len(m.EXPECTED_NAME_TO_ENTRY),14)
    def test_missing_symbol_not_proof_of_syscall_absence(self):
        d=m.assess(fixture())
        self.assertEqual(d['kallsyms_source_entry_name_status']['sys_newuname'],'ABSENT')
        self.assertTrue(d['missing_kallsyms_symbols_does_not_prove_missing_syscalls'])
        self.assertFalse(d['actual_vendor_syscall_dispatch_verified'])
    def test_all_symbol_names_unavailable_still_metadata_only(self):
        d=m.assess(fixture(symbol_source='UNAVAILABLE'))
        self.assertEqual(d['result'],'PASS_SELECTED_LIVE_KERNEL_CONFIG_AND_SYMBOL_NAMES_METADATA_ONLY')
        self.assertEqual(d['kallsyms_entry_unknown_count'],14)
        self.assertFalse(d['actual_vendor_syscall_dispatch_verified'])
    def test_kconfig_unavailable_holds(self):
        d=m.assess(fixture(config_source='UNAVAILABLE'))
        self.assertEqual(d['result'],'HOLD')
        self.assertEqual(d['hold_category'],'LIVE_KERNEL_CONFIG_UNAVAILABLE')
    def test_kernel_release_mismatch_holds(self):
        d=m.assess(fixture(release='4.19.0'))
        self.assertEqual(d['result'],'HOLD')
        self.assertEqual(d['hold_category'],'RUNNING_KERNEL_RELEASE_OR_ARCH_CHANGED')
    def test_machine_mismatch_holds(self):
        self.assertEqual(m.assess(fixture(machine='aarch64'))['result'],'HOLD')
    def test_no_raw_addresses_or_identity_fields(self):
        d=m.assess(fixture(),from_ssh=True)
        text=json.dumps(d)
        self.assertNotIn('192.168.',text)
        self.assertNotIn('0xdeadbeef',text)
        self.assertNotIn('root@',text)
        self.assertNotIn('hostname',text.lower())
    def test_parser_tolerates_unknown_config_values_only_as_unknown(self):
        d=m.assess(fixture(missing=('CONFIG_VFP',)))
        self.assertEqual(d['config_known_count'],len(m.CONFIG_KEYS)-1)
        self.assertEqual(d['kconfig_allowlist_status']['CONFIG_VFP'],'UNKNOWN')
    def test_error_extra_line_holds(self):
        with self.assertRaisesRegex(m.AuditHold,'UNEXPECTED_RECEIPT_LINE'):
            m.assess(fixture().replace('PW3_R51_END','SECRET|data\nPW3_R51_END'))
    def test_error_duplicate_scalar(self):
        with self.assertRaisesRegex(m.AuditHold,'DUPLICATE_SCALAR'):
            m.assess(fixture().replace('MACHINE|armv7l','MACHINE|armv7l\nMACHINE|armv7l'))
    def test_error_duplicate_config(self):
        with self.assertRaisesRegex(m.AuditHold,'CONFIG_VALUE_OR_DUPLICATE'):
            m.assess(fixture().replace('CFG|CONFIG_AEABI|y','CFG|CONFIG_AEABI|y\nCFG|CONFIG_AEABI|n'))
    def test_error_duplicate_symbol(self):
        with self.assertRaisesRegex(m.AuditHold,'SYMBOL_VALUE_OR_DUPLICATE'):
            m.assess(fixture().replace('SYM|sys_brk|PRESENT','SYM|sys_brk|PRESENT\nSYM|sys_brk|ABSENT'))
    def test_error_invalid_config_value(self):
        with self.assertRaisesRegex(m.AuditHold,'CONFIG_VALUE_OR_DUPLICATE'):
            m.assess(fixture().replace('CFG|CONFIG_AEABI|y','CFG|CONFIG_AEABI|sensitive_text'))
    def test_error_invalid_symbol_value(self):
        with self.assertRaisesRegex(m.AuditHold,'SYMBOL_VALUE_OR_DUPLICATE'):
            m.assess(fixture().replace('SYM|sys_brk|PRESENT','SYM|sys_brk|a1b2c3'))
    def test_error_unavailable_symbols_cannot_be_present(self):
        with self.assertRaisesRegex(m.AuditHold,'KALLSYMS_UNAVAILABLE_CONTRADICTS_VALUES'):
            m.assess(fixture().replace('KALLSYMS_SOURCE|AVAILABLE','KALLSYMS_SOURCE|UNAVAILABLE'))
    def test_error_unavailable_config_cannot_have_values(self):
        with self.assertRaisesRegex(m.AuditHold,'CONFIG_UNAVAILABLE_CONTRADICTS_VALUES'):
            m.assess(fixture().replace('CONFIG_SOURCE|PROC_CONFIG_GZ','CONFIG_SOURCE|UNAVAILABLE'))
    def test_error_bad_sentinels(self):
        with self.assertRaisesRegex(m.AuditHold,'RECEIPT_SENTINELS_INVALID'):
            m.assess(fixture().replace('PW3_R51_BEGIN','UNKNOWN_BEGIN'))
    def test_error_non_utf8_controls(self):
        with self.assertRaisesRegex(m.AuditHold,'INPUT_CONTROL_CHARACTER'):
            m.assess(fixture().replace('MACHINE|','MACHINE|\r'))
    def test_oversize_receipt(self):
        with self.assertRaisesRegex(m.AuditHold,'INPUT_SIZE_OR_TYPE_INVALID'):
            m.assess(fixture()+'x'*9000)
    def test_missing_key_fails_closed(self):
        with self.assertRaisesRegex(m.AuditHold,'REQUIRED_ALLOWLIST_ENTRIES_MISSING'):
            m.assess(fixture().replace('CFG|CONFIG_AEABI|y\n',''))


class CollectionSafetyTests(unittest.TestCase):
    def test_collect_target_validation(self):
        for t in ('-oProxyCommand=evil','root@host;rm','root@host name','root@',''): 
            with self.subTest(t=t):
                with self.assertRaisesRegex(m.AuditHold,'SSH_TARGET_FORMAT_INVALID'):
                    m.collect(t)
    def test_collect_uses_strict_ssh_and_stdin_no_shell(self):
        call=[]
        def fake(argv, **kw):
            call.append((argv,kw))
            return subprocess.CompletedProcess(argv,0,fixture(),'')
        with patch.object(m.subprocess,'run',side_effect=fake):
            self.assertEqual(m.collect('root@192.168.8.100'),fixture())
        argv,kw=call[0]
        self.assertEqual(argv[0],'ssh')
        self.assertIn('StrictHostKeyChecking=yes',argv)
        self.assertIn('BatchMode=yes',argv)
        self.assertEqual(argv[-3:],['root@192.168.8.100','sh','-s'])
        self.assertIn('PW3_R51_BEGIN',kw['input'])
        self.assertTrue(kw['capture_output'])
        self.assertFalse(kw['check'])
    def test_ssh_failure_fails_closed_without_disclosure(self):
        with patch.object(m.subprocess,'run',return_value=subprocess.CompletedProcess([],255,'','root@SECRET host unavailable')):
            with self.assertRaisesRegex(m.AuditHold,'SSH_NONZERO_EXIT'):
                m.collect('root@192.168.8.100')
    def test_remote_script_only_selected_commands(self):
        s=m.REMOTE_SCRIPT
        for forbidden in ('/dev/mmcblk','/dev/mtd','mount ','insmod','modprobe ','reboot','flash_erase','nandwrite','dd if=','sudo ','su -c','fw_setenv','chroot','touch ','chmod ','chown ','/etc/shadow'):
            self.assertNotIn(forbidden,s)
        self.assertIn('uname -r',s)
        self.assertIn('/proc/config.gz',s)
        self.assertIn('/proc/kallsyms',s)
        self.assertNotIn('$1',s)
        self.assertIn('$3 in wanted',s)
    def test_default_options_refuse_target_without_explicit_authorization(self):
        out=io.StringIO()
        with patch.object(m.subprocess,'run',side_effect=AssertionError('no SSH')):
            with contextlib.redirect_stdout(out):
                self.assertEqual(m.main(['--target','root@192.168.1.2']),2)
    def test_both_modes_are_mutually_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                m.main(['--authorize-readonly-kindle-ssh','--input-receipt','a'])
    def test_offline_mode_rejects_target(self):
        out=io.StringIO()
        with patch.object(m,'read_input',side_effect=AssertionError('not expected')):
            with contextlib.redirect_stdout(out):
                self.assertEqual(m.main(['--input-receipt','a','--target','root@192.168.0.2']),2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],'TARGET_WITH_OFFLINE_RECEIPT_INVALID')
    def test_ssh_authorised_success_classified(self):
        with patch.object(m,'collect',return_value=fixture()):
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(m.main(['--authorize-readonly-kindle-ssh','--target','root@192.168.8.100']),0)
        x=json.loads(out.getvalue())
        self.assertTrue(x['physical_device_access_performed'])
        self.assertFalse(x['actual_vendor_syscall_dispatch_verified'])
    def test_ssh_failure_reports_unknown_access(self):
        with patch.object(m,'collect',side_effect=m.AuditHold('SSH_NONZERO_EXIT')):
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(m.main(['--authorize-readonly-kindle-ssh','--target','root@192.168.1.4']),2)
        x=json.loads(out.getvalue())
        self.assertEqual(x['kindle_ssh_sessions'],'UNKNOWN_ON_FAILURE')
        self.assertEqual(x['hold_category'],'SSH_NONZERO_EXIT')
    def test_script_has_no_ssh_in_normal_preflight(self):
        with patch.object(m.subprocess,'run',side_effect=AssertionError('no child process')):
            out=io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(m.main([]),2)

if __name__=='__main__':
    unittest.main()
