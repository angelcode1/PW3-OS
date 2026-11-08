#!/usr/bin/env python3
"""Synthetic R3877.58 host tests; never contact Docker/Kindle."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from unittest.mock import patch
import unittest
import pw3_r3877_58_qemu_applets as mod


def sample_report():
    p={}
    for name, argv in mod.PROBE_ARGS:
        if name=='qemu_version':
            p[name]={'status':'PASS','exit_code':0,'expected_applet_output_matches':True}
        elif name in mod.CONTROLS:
            p[name]={'status':'PASS','exit_code':0,'expected_applet_output_matches':True}
        else:
            p[name]={'status':'TRACE_OBSERVED_UNCLASSIFIED_STREAM','exit_code':0,
                'control_probe':mod.PAIRS[name],'untraced_control_verified':True,
                'trace_unclassified_lines_present':True,
                'trace':{'syscall_record_count':15,'syscall_names':['read','write'],
                         'trace_unknown_record_count':0,'trace_enosys_record_count':0}}
    return {'result':'PASS_QEMU_SYSCALL_NAMES_AND_UNTRACED_APPLET_CONTROLS_ONLY',
        'original_image_unchanged':True, 'all_created_containers_removed':True,
        'authorized_qemu_execution_performed':True,
        'independent_untraced_controls_verified':True,
        'busybox_sha256':mod.r49.BUSYBOX_SHA256,
        'qemu_binary_sha256':mod.r49.QEMU_SHA256,
        'runtime_probes':p,
        'trace_stream_unclassified_output_present':True,
        'writable_fallback_used':False,
        'read_only_copy_probe':{'classification':'READONLY_COPY_ACCEPTED','exit_code':0}}


class TestR58(unittest.TestCase):
    def test_01_no_docker_default(self):
        with patch.object(mod.r49, 'docker',side_effect=AssertionError('no docker')):
            with redirect_stdout(io.StringIO()) as capture:
                self.assertEqual(mod.main([]),2)
            report=json.loads(capture.getvalue()); self.assertFalse(report['docker_used'])
    def test_02_no_docker_writable_without_authorization(self):
        with patch.object(mod.r49,'docker',side_effect=AssertionError('no docker')):
            with redirect_stdout(io.StringIO()) as capture:
                self.assertEqual(mod.main(['--allow-disposable-writable-layer']),2)
            self.assertIn('OPT_IN',json.loads(capture.getvalue())['hold_category'])
    def test_03_immutable_hold(self):
        self.assertEqual(mod.preflight()['immutable_hold'],'NOT_BOOTABLE')
    def test_04_no_kindle_or_boot(self):
        r=mod.preflight()
        for k in ('physical_device_access_performed','firmware_write_performed','boot_performed',
                  'target_musl_linux_3_0_35_compatibility_verified','arm_thread_clone_runtime_verified'):
            self.assertFalse(r[k], k)
    def test_05_helper_sha_pin(self):
        self.assertTrue(mod.require_base())
    def test_06_helper_sha_change_hold(self):
        with patch.object(mod, 'BASE_SHA256','0'*64):
            with self.assertRaisesRegex(mod.Hold,'PINNED_R49_3_RUNNER_CHANGED'):mod.require_base()
    def test_07_qemu_version_good(self):
        self.assertTrue(mod.control_output_ok('qemu_version',0,'qemu-arm version 10.0.4 (test)\n'))
    def test_08_qemu_version_wrong(self):
        self.assertFalse(mod.control_output_ok('qemu_version',0,'qemu-arm version 9.2.0\n'))
    def test_09_busybox_true_good(self):
        self.assertTrue(mod.control_output_ok('busybox_true_control',0,''))
    def test_10_busybox_help_is_not_true(self):
        self.assertFalse(mod.control_output_ok('busybox_true_control',0,'BusyBox --help\n'))
    def test_11_ash_exact(self):
        self.assertTrue(mod.control_output_ok('ash_control',0,'PW3_R58_ASH_OK\n'))
    def test_12_ash_extra_output_reject(self):
        self.assertFalse(mod.control_output_ok('ash_control',0,'PW3_R58_ASH_OK\nWARN\n'))
    def test_13_ash_rc_reject(self):
        self.assertFalse(mod.control_output_ok('ash_control',1,'PW3_R58_ASH_OK\n'))
    def test_14_stat_positive(self):
        self.assertTrue(mod.control_output_ok('stat_control',0,'653202\n'))
    def test_15_stat_zero_reject(self):
        self.assertFalse(mod.control_output_ok('stat_control',0,'0\n'))
    def test_16_stat_injected_reject(self):
        self.assertFalse(mod.control_output_ok('stat_control',0,'653202\nextra\n'))
    def test_17_date_positive(self):
        self.assertTrue(mod.control_output_ok('date_control',0,'1794160000\n'))
    def test_18_date_out_of_range(self):
        self.assertFalse(mod.control_output_ok('date_control',0,'1234567890\n'))
    def test_19_date_nonsense(self):
        self.assertFalse(mod.control_output_ok('date_control',0,'2026-11-08\n'))
    def test_20_od_hex_bytes(self):
        self.assertTrue(mod.control_output_ok('urandom_control',0,' 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f\n'))
    def test_21_od_newline(self):
        self.assertTrue(mod.control_output_ok('urandom_control',0,' 00 01 02 03 04 05 06 07\n 08 09 0a 0b 0c 0d 0e 0f\n'))
    def test_22_od_short_reject(self):
        self.assertFalse(mod.control_output_ok('urandom_control',0,' 00 01 02 03\n'))
    def test_23_od_injected_reject(self):
        self.assertFalse(mod.control_output_ok('urandom_control',0,' 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f\nBAD'))
    def test_24_unknown_probe_reject(self):
        self.assertFalse(mod.control_output_ok('unknown',0,'good'))
    def test_25_good_base_summary(self):
        d=mod.assess_base(sample_report());self.assertEqual(len(d),4)
    def test_26_missing_probe_hold(self):
        r=sample_report();r['runtime_probes'].pop('urandom_trace')
        with self.assertRaisesRegex(mod.Hold,'INCOMPLETE'):mod.assess_base(r)
    def test_27_cleanup_hold(self):
        r=sample_report();r['all_created_containers_removed']=False
        with self.assertRaisesRegex(mod.Hold,'CLEANUP'):mod.assess_base(r)
    def test_28_wrong_image_hold(self):
        r=sample_report();r['original_image_unchanged']=False
        with self.assertRaisesRegex(mod.Hold,'CLEANUP'):mod.assess_base(r)
    def test_29_mismatch_busybox_hold(self):
        r=sample_report();r['busybox_sha256']='0'*64
        with self.assertRaisesRegex(mod.Hold,'PINS_MISMATCH'):mod.assess_base(r)
    def test_30_control_did_not_pass(self):
        r=sample_report();r['runtime_probes']['date_control']['status']='HOLD'
        with self.assertRaisesRegex(mod.Hold,'UNTRACED_CONTROL'):mod.assess_base(r)
    def test_31_trace_zero_hold(self):
        r=sample_report();r['runtime_probes']['date_trace']['trace']['syscall_record_count']=0
        with self.assertRaisesRegex(mod.Hold,'QEMU_TRACE'):mod.assess_base(r)
    def test_32_trace_wrong_pair_hold(self):
        r=sample_report();r['runtime_probes']['urandom_trace']['control_probe']='ash_control'
        with self.assertRaisesRegex(mod.Hold,'QEMU_TRACE'):mod.assess_base(r)
    def test_33_base_hold_must_not_promote(self):
        r=sample_report();r['result']='HOLD'
        with self.assertRaisesRegex(mod.Hold,'PINNED_R49_RUNTIME_HOLD'):mod.assess_base(r)
    def test_34_no_direct_thread_probe(self):
        self.assertNotIn('pthread',str(mod.PROBE_ARGS))
    def test_35_no_guest_shell_commands_write(self):
        for name,argv in mod.PROBE_ARGS:
            self.assertNotIn('-0',argv)
            self.assertNotIn('rm',argv)
            self.assertNotIn('mount',argv)
            self.assertNotIn('curl',argv)
    def test_36_authorized_synthetic_result(self):
        def fake(allow):
            self.assertFalse(allow)
            self.assertEqual(set(mod.r49.TRACE_PROBES),mod.TRACES)
            self.assertEqual(mod.r49.TRACE_TO_CONTROL,mod.PAIRS)
            self.assertTrue(mod.r49.probe_ok('ash_control',0,'PW3_R58_ASH_OK\n'))
            return sample_report()
        with patch.object(mod.r49,'run',side_effect=fake):
            r=mod.execute(False)
        self.assertEqual(r['result'],mod.PASS)
        self.assertTrue(r['all_created_containers_removed'])
        self.assertFalse(r['target_musl_linux_3_0_35_compatibility_verified'])
    def test_37_authorized_opt_in_flag(self):
        with patch.object(mod.r49,'run',return_value=sample_report()) as method:
            r=mod.execute(True)
        method.assert_called_once_with(True)
        self.assertTrue(r['disposable_writable_layer_additional_opt_in'])
    def test_38_patch_restoration(self):
        original=mod.r49.PROBES
        with patch.object(mod.r49,'run',return_value=sample_report()):mod.execute(False)
        self.assertIs(mod.r49.PROBES,original)
        self.assertIs(mod.r49.probe_ok,mod.ORIGINAL_PROBE_OK)
    def test_39_real_run_never_mocked(self):
        self.assertFalse(mod.preflight()['arm_guest_execution_performed'])
    def test_40_no_docker_on_hash_hold(self):
        with patch.object(mod,'BASE_SHA256','0'*64), patch.object(mod.r49,'docker',side_effect=AssertionError('no docker')):
            r=mod.execute(False)
        self.assertEqual(r['result'],'HOLD')
    def test_41_script_uses_only_existing_busybox(self):
        for name,argv in mod.PROBE_ARGS:
            if name!='qemu_version':self.assertIn('/bin/busybox',argv)
    def test_42_trace_suffix_requires_qemu_strace(self):
        for name,argv in mod.PROBE_ARGS:
            self.assertEqual(argv[0]=='-strace',name in mod.TRACES)

if __name__=='__main__':unittest.main()
