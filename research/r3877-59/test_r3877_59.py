#!/usr/bin/env python3
"""Synthetic host-only R3877.59 tests. Never invokes Docker or Kindle."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import pw3_r3877_59_qemu_pthread_tls as m

class Tests(unittest.TestCase):
    def setUp(self):
        self.base=m.r49

    def fake_base(self):
        tr={'status':'TRACE_OBSERVED_UNCLASSIFIED_STREAM',
            'exit_code':0,'control_probe':'r59_probe_control','untraced_control_verified':True,
            'trace':{'syscall_record_count':31,'syscall_names':['clone','futex','getrandom','write','exit_group'],
                     'trace_unknown_record_count':0,'trace_enosys_record_count':0}}
        probe={'status':'PASS','exit_code':0,'expected_applet_output_matches':True}
        return {'result':'PASS_QEMU_SYSCALL_NAMES_AND_UNTRACED_APPLET_CONTROLS_ONLY',
                'original_image_unchanged':True,'all_created_containers_removed':True,
                'authorized_qemu_execution_performed':True,
                'independent_untraced_controls_verified':True,
                'busybox_sha256':self.base.BUSYBOX_SHA256,
                'qemu_binary_sha256':self.base.QEMU_SHA256,
                'runtime_probes':{'qemu_version':{'status':'PASS'},
                    'busybox_true_control':dict(probe),
                    'r59_probe_control':dict(probe),'r59_probe_trace':dict(tr)},
                'read_only_copy_probe':{'classification':'READONLY_ROOTFS_COPY_REJECTED'},
                'writable_fallback_used':True}

    def assertHold(self,report,needle):
        with self.assertRaises(m.Hold) as e:m.assess(report)
        self.assertIn(needle,str(e.exception))

    def test_01_pinned_binary(self):self.assertTrue(m.require_pinned())
    def test_02_baseline_script_hash(self):self.assertEqual(m.digest(m.r49.__file__),m.BASE_SHA256)
    def test_03_binary_hash(self):self.assertEqual(m.digest(m.PROBE),m.PROBE_SHA256)
    def test_04_legacy_qemu_image_pinned(self):self.assertTrue(m.r49.PARENT_ID.startswith('sha256:'))
    def test_05_immutable_hold(self):self.assertEqual(m.preflight()['immutable_hold'],'NOT_BOOTABLE')
    def test_06_no_docker_preflight(self):self.assertFalse(m.preflight()['docker_used'])
    def test_07_no_kindle_preflight(self):self.assertEqual(m.preflight()['kindle_ssh_sessions'],0)
    def test_08_no_arm_preflight(self):self.assertFalse(m.preflight()['arm_guest_execution_performed'])
    def test_09_no_vendor_kernel_claim(self):self.assertFalse(m.preflight()['vendor_kernel_syscall_dispatch_verified'])
    def test_10_no_getrandom_enosys_claim(self):self.assertFalse(m.preflight()['runtime_getrandom_enosys_fallback_verified'])
    def test_11_preflight_cli_zero_docker(self):
        with patch.object(m.r49,'docker',side_effect=AssertionError('No Docker')):
            with redirect_stdout(io.StringIO()):self.assertEqual(m.main([]),2)
    def test_12_writable_opt_in_alone_refuses(self):
        with patch.object(m,'execute',side_effect=AssertionError('Never execute')):
            buf=io.StringIO()
            with redirect_stdout(buf):self.assertEqual(m.main(['--allow-disposable-writable-layer']),2)
            self.assertEqual(json.loads(buf.getvalue())['hold_category'],'WRITABLE_OPT_IN_REQUIRES_QEMU_AUTHORIZATION')
    def test_13_true_exact(self):self.assertTrue(m.control_output_ok('busybox_true_control',0,''))
    def test_14_true_wrong(self):self.assertFalse(m.control_output_ok('busybox_true_control',0,'help'))
    def test_15_elf_probe_exact(self):self.assertTrue(m.control_output_ok('r59_probe_control',0,m.EXPECTED_OUTPUT))
    def test_16_elf_probe_rc_error(self):self.assertFalse(m.control_output_ok('r59_probe_control',1,m.EXPECTED_OUTPUT))
    def test_17_elf_probe_missing_tls(self):self.assertFalse(m.control_output_ok('r59_probe_control',0,m.EXPECTED_OUTPUT.replace('PTHREAD_TLS','PTHREAD_MISSING')))
    def test_18_elf_probe_extra_output(self):self.assertFalse(m.control_output_ok('r59_probe_control',0,m.EXPECTED_OUTPUT+'noise'))
    def test_19_extra_probe_in_guest_path(self):self.assertTrue(m.GUEST_PROBE.startswith('/usr/bin/'))
    def test_20_required_list(self):self.assertEqual({k for k,_ in m.PROBES},{'qemu_version','busybox_true_control','r59_probe_control','r59_probe_trace'})
    def test_21_no_unexpected_base(self):self.assertNotIn('-0',m.PROBES[2][1])
    def test_22_assess_positive(self):
        r=m.assess(self.fake_base());self.assertTrue(r['clone_syscall_observed_in_qemu_trace']);self.assertTrue(r['getrandom_syscall_observed_in_qemu_trace'])
    def test_23_assess_futex_optional(self):
        b=self.fake_base();b['runtime_probes']['r59_probe_trace']['trace']['syscall_names']=['clone','getrandom'];self.assertFalse(m.assess(b)['futex_syscall_observed_in_qemu_trace'])
    def test_24_bad_base_result(self):
        b=self.fake_base();b['result']='HOLD';self.assertHold(b,'R49_ISOLATED_QEMU_HOLD')
    def test_25_cleanup_required(self):
        b=self.fake_base();b['all_created_containers_removed']=False;self.assertHold(b,'R49_GUEST_CLEANUP')
    def test_26_parent_required(self):
        b=self.fake_base();b['original_image_unchanged']=False;self.assertHold(b,'R49_GUEST_CLEANUP')
    def test_27_execution_required(self):
        b=self.fake_base();b['authorized_qemu_execution_performed']=False;self.assertHold(b,'R49_QEMU_CONTROLS')
    def test_28_untraced_required(self):
        b=self.fake_base();b['independent_untraced_controls_verified']=False;self.assertHold(b,'R49_QEMU_CONTROLS')
    def test_29_busybox_pin_required(self):
        b=self.fake_base();b['busybox_sha256']='0'*64;self.assertHold(b,'R59_HELPER')
    def test_30_qemu_pin_required(self):
        b=self.fake_base();b['qemu_binary_sha256']='0'*64;self.assertHold(b,'R59_HELPER')
    def test_31_missing_probe(self):
        b=self.fake_base();del b['runtime_probes']['r59_probe_control'];self.assertHold(b,'R59_PROBE_SET')
    def test_32_control_failure(self):
        b=self.fake_base();b['runtime_probes']['r59_probe_control']['status']='HOLD';self.assertHold(b,'R59_UNTRACED')
    def test_33_trace_unverified(self):
        b=self.fake_base();b['runtime_probes']['r59_probe_trace']['untraced_control_verified']=False;self.assertHold(b,'R59_TRACE_CONTROL')
    def test_34_no_clone(self):
        b=self.fake_base();b['runtime_probes']['r59_probe_trace']['trace']['syscall_names']=['getrandom'];self.assertHold(b,'UNOBSERVED')
    def test_35_no_getrandom(self):
        b=self.fake_base();b['runtime_probes']['r59_probe_trace']['trace']['syscall_names']=['clone'];self.assertHold(b,'UNOBSERVED')
    def test_36_bad_trace_record(self):
        b=self.fake_base();b['runtime_probes']['r59_probe_trace']['trace']['syscall_record_count']=0;self.assertHold(b,'R59_TRACE_CONTROL')
    def test_37_trace_attribution_not_proved(self):self.assertFalse(m.assess(self.fake_base())['trace_stream_attribution_verified'])
    def test_38_readonly_copy_error_keeps_hold(self):
        b={'result':'HOLD','error_category':'READONLY_COPY_REJECTED_WRITABLE_FALLBACK_NOT_AUTHORIZED','all_created_containers_removed':True,'original_image_unchanged':True,'authorized_qemu_execution_performed':False}
        with patch.object(m.r49,'run',return_value=b):
            r=m.execute(False)
        self.assertEqual(r['result'],'HOLD')
        self.assertEqual(r['base_error_category'],b['error_category'])
    def test_39_pass_only_after_valid_parent(self):
        with patch.object(m.r49,'run',return_value=self.fake_base()):r=m.execute(True)
        self.assertEqual(r['result'],m.PASS)
        self.assertTrue(r['arm_pthread_and_isolated_tls_runtime_under_qemu_verified'])
        self.assertFalse(r['target_musl_linux_3_0_35_compatibility_verified'])
    def test_40_authorized_cli_pass(self):
        with patch.object(m,'execute',return_value={'result':m.PASS}) as run:
            with redirect_stdout(io.StringIO()):self.assertEqual(m.main(['--authorize-offline-qemu','--allow-disposable-writable-layer']),0)
            run.assert_called_once_with(True)
    def test_41_authorized_cli_hold(self):
        with patch.object(m,'execute',return_value={'result':'HOLD'}):
            with redirect_stdout(io.StringIO()):self.assertEqual(m.main(['--authorize-offline-qemu']),2)
    def test_42_diff_expected(self):
        cp=SimpleNamespace(stdout='A /usr/bin/qemu-arm-static\nA /usr/bin/pw3-r3877-59-armv7-probe\n')
        self.assertTrue(m.classify_guest_diff('a'*64,lambda x:cp)['allowed_changes_only'])
    def test_43_diff_unexpected_file(self):
        cp=SimpleNamespace(stdout='A /usr/bin/qemu-arm-static\nA /usr/bin/pw3-r3877-59-armv7-probe\nC /etc/passwd\n')
        with self.assertRaisesRegex(m.r49.Hold,'UNEXPECTED'):m.classify_guest_diff('a'*64,lambda x:cp)
    def test_44_diff_missing_probe(self):
        cp=SimpleNamespace(stdout='A /usr/bin/qemu-arm-static\n')
        with self.assertRaisesRegex(m.r49.Hold,'PROBE_INJECTION'):m.classify_guest_diff('a'*64,lambda x:cp)
    def test_45_diff_missing_qemu(self):
        cp=SimpleNamespace(stdout='A /usr/bin/pw3-r3877-59-armv7-probe\n')
        with self.assertRaisesRegex(m.r49.Hold,'QEMU_INJECTION'):m.classify_guest_diff('a'*64,lambda x:cp)
    def test_46_copy_failed_not_inject(self):
        calls=[]
        def fake(argv,**kw):calls.append(argv);return SimpleNamespace(returncode=1)
        m.copied_probe_on_success(['cp','/host/qemu','a'*64+':/usr/bin/qemu-arm-static'],fake,allow_nonzero=True)
        self.assertEqual(len(calls),1)
    def test_47_non_guest_copy_not_inject(self):
        calls=[]
        def fake(argv,**kw):calls.append(argv);return SimpleNamespace(returncode=0)
        m.copied_probe_on_success(['cp','-L','a'*64+':/usr/bin/qemu-arm','/host/qemu'],fake)
        self.assertEqual(len(calls),1)
    def test_48_symlink_binary_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td).resolve()/'probe.elf';p.symlink_to(m.PROBE)
            with patch.object(m,'PROBE',p):
                with self.assertRaisesRegex(m.Hold,'R59_ARMV7_PROBE_BINARY'):m.require_pinned()
    def test_49_changed_binary_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td).resolve()/'probe.elf';p.write_bytes(m.PROBE.read_bytes()+b'x')
            with patch.object(m,'PROBE',p):
                with self.assertRaisesRegex(m.Hold,'R59_ARMV7_PROBE_BINARY'):m.require_pinned()
    def test_50_probe_source_has_thread_tls(self):
        s=(Path(__file__).parent/'pw3_r3877_59_armv7_probe.c').read_text()
        for marker in ('__thread int tls_counter','pthread_create','pthread_join','getrandom','getentropy'):
            self.assertIn(marker,s)

if __name__=='__main__':unittest.main()
