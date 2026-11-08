"""Strict offline synthetic tests: no GitHub, Docker, SSH or Kindle."""
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pw3_r3877_52_musl_arm_tls_fallback_audit as mod

TOKENS = {
 'musl/src/thread/arm/__set_thread_area.c': '__syscall(0xf0005, p)\nHWCAP_TLS\n',
 'musl/src/thread/arm/clone.s': 'mov r7,#120\nsvc 0\n',
 'musl/src/thread/pthread_create.c': 'CLONE_SETTLS\n__clone((\nif (!libc.can_do_threads) return ENOSYS\nCLONE_THREAD\n',
 'musl/arch/arm/pthread_arch.h': 'mrc p15,0,%0,c13,c0,3\nTLS_ABOVE_TP\n',
 'musl/src/time/clock_gettime.c': 'SYS_clock_gettime64\nr!=-ENOSYS\n__syscall(SYS_clock_gettime, clk, ts32)\n',
 'musl/src/time/clock_nanosleep.c': 'SYS_clock_nanosleep_time64\nr!=-ENOSYS\nSYS_clock_nanosleep\nSYS_nanosleep\n',
 'musl/src/thread/__timedwait.c': 'SYS_futex_time64\nr!=-ENOSYS\n__syscall_cp(SYS_futex\nCLAMP(s)\n',
 'musl/src/stat/fstatat.c': 'SYS_statx\nret!=-ENOSYS\nfstatat_kstat\n#ifdef SYS_fstatat\n',
 'musl/src/linux/getrandom.c': 'syscall_cp(SYS_getrandom, buf, buflen, flags)\n',
 'musl/src/misc/getentropy.c': 'ret = getrandom(pos, len, 0)\nif (errno == EINTR) continue;\nelse break;\n',
 'lab126/arch/arm/include/asm/unistd.h': '#define __ARM_NR_set_tls (__ARM_NR_BASE+5)\n',
 'lab126/arch/arm/kernel/traps.c': 'case NR(set_tls):\nthread->tp_value[0] = regs->ARM_r0;\nif (has_tls_reg)\n',
 'lab126/arch/arm/kernel/entry-common.S': '__ARM_NR_BASE\narm_syscall\n',
}

def evidence():
    return {
        'milestone': 'R3877.51.3',
        'result': 'PASS_LOCAL_DECODED_KERNEL_CONFIG_AND_PRIOR_LIVE_SYMBOL_NAMES_ONLY',
        'immutable_hold': 'NOT_BOOTABLE',
        'kernel_release': '3.0.35-lab126', 'architecture': 'armv7l',
        'compressed_sha256': mod.EXPECTED_COMPRESSED_SHA256,
        'decoded_sha256': mod.EXPECTED_DECODED_SHA256,
        'config_decoder': 'MAC_PYTHON_ZLIB_GZIP',
        'config_known_count': 18, 'config_unknown_count': 0,
        'previous_live_kallsyms_symbol_names_present': 14,
        'previous_live_kallsyms_symbol_names_checked': 14,
        'core_abi_config_flags_enabled': True,
        'target_musl_linux_3_0_35_compatibility_verified': False,
        'exact_source_to_kernel_binary_attestation_verified': False,
        'recovery_verified': False,
        'kconfig_allowlist_status': dict(mod.EXPECTED_CONFIG),
    }

class R52Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root/'sources'
        self.pins = {}
        for p, content in TOKENS.items():
            target = self.src/p
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(content)
            self.pins[p] = mod.git_blob_sha1(content.encode())
        self.report = self.root/'selected.json'
        self.report.write_text(json.dumps(evidence()))

    def audit(self):
        return mod.run(self.src,self.report,pins=self.pins)

    def test_01_positive_fixture_only(self):
        r=self.audit()
        self.assertTrue(r['result'].startswith('PASS_'))
        self.assertEqual(r['source_audit']['verified_public_git_blob_count'],13)

    def test_02_hold_is_immutable(self):
        self.assertEqual(self.audit()['immutable_hold'],'NOT_BOOTABLE')

    def test_03_actual_dispatch_not_claimed(self):
        self.assertFalse(self.audit()['actual_vendor_syscall_dispatch_verified'])

    def test_04_patched_source_not_proved(self):
        self.assertFalse(self.audit()['original_patched_musl_binary_reproducibility_verified'])

    def test_05_runtime_not_proved(self):
        self.assertFalse(self.audit()['target_musl_linux_3_0_35_compatibility_verified'])

    def test_06_no_on_device_actions(self):
        r=self.audit()
        self.assertEqual(r['kindle_ssh_sessions'],0)
        self.assertFalse(r['boot_performed'])
        self.assertFalse(r['firmware_write_performed'])

    def test_07_source_pin_count(self):
        self.assertEqual(len(mod.PINS),13)
        self.assertEqual(set(mod.PINS),set(TOKENS))

    def test_08_missing_source_hold(self):
        (self.src/'musl/src/linux/getrandom.c').unlink()
        with self.assertRaises(mod.AuditHold):self.audit()

    def test_09_changed_source_hash_hold(self):
        with (self.src/'musl/src/linux/getrandom.c').open('a') as f:f.write('changed\n')
        with self.assertRaisesRegex(mod.AuditHold,'GIT_BLOB_MISMATCH'):self.audit()

    def test_10_source_symlink_rejected(self):
        p=self.src/'musl/src/linux/getrandom.c'
        p.unlink()
        p.symlink_to(self.report)
        with self.assertRaises(mod.AuditHold):self.audit()

    def test_11_parent_symlink_rejected(self):
        p=self.src/'musl/src/linux/getrandom.c';p.unlink()
        directory=self.src/'musl/src/linux';directory.rmdir()
        target=self.root/'elsewhere';target.mkdir()
        directory.symlink_to(target,target_is_directory=True)
        with self.assertRaises(mod.AuditHold):self.audit()

    def test_12_empty_source_hold(self):
        p=self.src/'musl/src/linux/getrandom.c';p.write_bytes(b'')
        self.pins['musl/src/linux/getrandom.c']=mod.git_blob_sha1(b'')
        with self.assertRaises(mod.AuditHold):self.audit()

    def test_13_oversized_source_hold(self):
        p=self.src/'musl/src/linux/getrandom.c';p.write_bytes(b'x'*131073)
        with self.assertRaises(mod.AuditHold):self.audit()

    def test_14_invalid_utf8_hold(self):
        p=self.src/'musl/src/linux/getrandom.c';p.write_bytes(b'\xff')
        self.pins['musl/src/linux/getrandom.c']=mod.git_blob_sha1(b'\xff')
        with self.assertRaises(mod.AuditHold):self.audit()

    def test_15_missing_source_dir_hold(self):
        with self.assertRaises(mod.AuditHold):mod.load_sources(self.root/'missing',self.pins)

    def test_16_uses_fixed_tls_number(self):
        self.assertEqual(self.audit()['source_audit']['arm_private_set_tls_number'],'0x0f0005')

    def test_17_time64_fallbacks_source_only(self):
        d=self.audit()['source_audit']
        for x in ['clock_gettime_time64_to_legacy_fallback_source_present',
                  'clock_nanosleep_time64_to_legacy_fallback_source_present',
                  'futex_time64_to_legacy_fallback_source_present']:
            self.assertTrue(d[x])

    def test_18_entropy_fallback_not_proved(self):
        d=self.audit()
        self.assertFalse(d['entropy_application_fallback_verified'])
        self.assertTrue(d['source_audit']['getrandom_and_getentropy_no_internal_device_fallback_source'])

    def test_19_private_tls_pattern_removed_hold(self):
        p='musl/src/thread/arm/__set_thread_area.c'
        self._change_pin(p,TOKENS[p].replace('0xf0005','0xf0006'))
        with self.assertRaisesRegex(mod.AuditHold,'ARM_PRIVATE_TLS_CALL'):self.audit()

    def test_20_kernel_private_syscall_number_changed_hold(self):
        p='lab126/arch/arm/include/asm/unistd.h'
        self._change_pin(p,TOKENS[p].replace('+5','+6'))
        with self.assertRaisesRegex(mod.AuditHold,'LAB126_PRIVATE_TLS_NUMBER_MISMATCH'):self.audit()

    def test_21_kernel_handler_absent_hold(self):
        p='lab126/arch/arm/kernel/traps.c'
        self._change_pin(p,TOKENS[p].replace('NR(set_tls)','NR(set_fake)'))
        with self.assertRaisesRegex(mod.AuditHold,'LAB126_TLS_HANDLER'):self.audit()

    def test_22_clone3_substitution_hold(self):
        p='musl/src/thread/arm/clone.s'
        self._change_pin(p,TOKENS[p].replace('#120','#435'))
        with self.assertRaisesRegex(mod.AuditHold,'MUSL_LEGACY_CLONE'):self.audit()

    def test_23_threads_tls_flag_removed_hold(self):
        p='musl/src/thread/pthread_create.c'
        self._change_pin(p,TOKENS[p].replace('CLONE_SETTLS','CLONE_NEWTLS'))
        with self.assertRaisesRegex(mod.AuditHold,'PTHREAD_CREATE_SOURCE'):self.audit()

    def test_24_clock_fallback_removed_hold(self):
        p='musl/src/time/clock_gettime.c'
        self._change_pin(p,TOKENS[p].replace('r!=-ENOSYS','r!=-ENOTSUP'))
        with self.assertRaisesRegex(mod.AuditHold,'CLOCK_GETTIME_FALLBACK'):self.audit()

    def test_25_statx_fallback_removed_hold(self):
        p='musl/src/stat/fstatat.c'
        self._change_pin(p,TOKENS[p].replace('fstatat_kstat','direct_only'))
        with self.assertRaisesRegex(mod.AuditHold,'FSTATAT_FALLBACK'):self.audit()

    def test_26_fake_entropy_fallback_rejected(self):
        p='musl/src/misc/getentropy.c'
        self._change_pin(p,TOKENS[p]+' /dev/urandom\n')
        with self.assertRaisesRegex(mod.AuditHold,'GETRANDOM_ENTROPY_FALLBACK_SOURCE_CHANGED'):self.audit()

    def test_27_evidence_milestone_tamper_hold(self):
        self._modify_evidence('milestone','R3877.51.2')
        with self.assertRaisesRegex(mod.AuditHold,'R51_SELECTED_PASS_EVIDENCE_CHANGED'):self.audit()

    def test_28_evidence_symbol_count_tamper_hold(self):
        self._modify_evidence('previous_live_kallsyms_symbol_names_present',13)
        with self.assertRaisesRegex(mod.AuditHold,'R51_SELECTED_PASS_EVIDENCE_CHANGED'):self.audit()

    def test_29_evidence_kernel_change_hold(self):
        self._modify_evidence('kernel_release','6.0.0')
        with self.assertRaisesRegex(mod.AuditHold,'R51_SELECTED_PASS_EVIDENCE_CHANGED'):self.audit()

    def test_30_evidence_config_change_hold(self):
        val=evidence();val['kconfig_allowlist_status']['CONFIG_FUTEX']='n';self.report.write_text(json.dumps(val))
        with self.assertRaisesRegex(mod.AuditHold,'R51_CONFIG_VALUES_CHANGED'):self.audit()

    def test_31_evidence_digest_change_hold(self):
        self._modify_evidence('compressed_sha256','0'*64)
        with self.assertRaisesRegex(mod.AuditHold,'R51_SELECTED_PASS_EVIDENCE_CHANGED'):self.audit()

    def test_32_no_input_preflight(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code=mod.main([])
        self.assertEqual(code,2)
        v=json.loads(out.getvalue())
        self.assertEqual(v['result'],'HOLD')
        self.assertEqual(v['kindle_ssh_sessions'],0)

    def test_33_extra_source_is_ignored(self):
        p=self.src/'extra.txt';p.write_text('extra')
        self.assertTrue(self.audit()['result'].startswith('PASS_'))

    def test_34_source_semantics_dont_prove_live_tls(self):
        self.assertFalse(self.audit()['source_audit']['kernel_arm_tls_private_dispatch_runtime_verified'])

    def test_35_older_kernel_assessment_scope(self):
        self.assertFalse(self.audit()['source_audit']['conditional_compilation_verified'])

    def test_36_original_tar_patch_not_proven(self):
        self.assertFalse(self.audit()['source_audit']['patched_musl_init_tls_source_and_built_loader_equivalence_verified'])

    def test_37_full_config_not_required(self):
        self.assertNotIn('raw_config',self.audit())

    def test_38_digest_function(self):
        self.assertEqual(mod.git_blob_sha1(b'x'),hashlib.sha1(b'blob 1\0x').hexdigest())

    def test_39_report_is_selected_sanitized_not_raw(self):
        self.assertEqual(len(evidence()['kconfig_allowlist_status']),18)

    def test_40_failed_entropy_getrandom_pattern(self):
        p='musl/src/linux/getrandom.c'
        self._change_pin(p,TOKENS[p].replace('SYS_getrandom','SYS_getentropy'))
        with self.assertRaisesRegex(mod.AuditHold,'GETRANDOM_WRAPPER'):self.audit()

    def _change_pin(self,p,text):
        (self.src/p).write_text(text)
        self.pins[p]=mod.git_blob_sha1(text.encode())

    def _modify_evidence(self,k,v):
        b=evidence();b[k]=v;self.report.write_text(json.dumps(b))

if __name__=='__main__':unittest.main()
