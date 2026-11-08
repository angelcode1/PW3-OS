"""Host-only static/fail-closed regression tests. No network, Docker or Kindle."""
import copy
import hashlib
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

S=Path(__file__).with_name('pw3_r3877_50_public_lab126_syscall_crosswalk.py')
spec=importlib.util.spec_from_file_location('r50',S)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

NUMS={
 'brk':45,'exit_group':248,'getgid32':200,'getuid32':199,'ioctl':54,'mmap2':192,
 'mprotect':125,'rt_sigprocmask':175,'set_tid_address':256,'setgid32':214,
 'setuid32':213,'uname':122,'write':4,'writev':146
}

def sources():
    hdr='/* arch/arm/include/asm/unistd.h */\n#define __NR_SYSCALL_BASE 0\n'
    mapping={f'dummy_{i}':i for i in range(340)}
    mapping.update(NUMS)
    for name,n in sorted(mapping.items()):
        hdr+=f'#define __NR_{name} (__NR_SYSCALL_BASE+ {n})\n'
    calls='/* linux/arch/arm/kernel/calls.S */\n/* This file is included thrice in entry-common.S */\n'
    inverted={NUMS[k]:v for k,v in r.ENTRY_EXPECTED.items()}
    for start in range(0,376,5):
        calls+=f'/* {start} */\n'
        for i in range(start,min(start+5,376)):
            calls+=f'CALL({inverted.get(i,"sys_dummy")})\n'
    calls+='#ifndef syscalls_counted\n#endif\n.rept syscalls_padding\nCALL(sys_ni_syscall)\n.endr\n'
    return hdr.encode(),calls.encode()

def report():
    p={}
    for k,(count,names) in r.BASELINE.items():
        p[k]={'exit_code':0,'status':'TRACE_OBSERVED_CLEAN_STREAM',
              'untraced_control_verified':True,'guest_argv_verified_by_inspect':True,
              'trace':{'syscall_record_count':count,'trace_enosys_record_count':0,
                       'trace_unknown_record_count':0,'syscall_names':sorted(names)}}
    for n in ('true','uname','echo'):
        p[f'busybox_{n}_control']={'status':'PASS','exit_code':0,'expected_applet_output_matches':True}
    return {'milestone':'R3877.49.3','result':'PASS_QEMU_SYSCALL_NAMES_AND_UNTRACED_APPLET_CONTROLS_ONLY',
            'immutable_hold':'NOT_BOOTABLE','independent_untraced_controls_verified':True,
            'original_image_id_sha256':r.PARENT_IMAGE_ID,'busybox_sha256':r.BUSYBOX_HASH,'qemu_binary_sha256':r.QEMU_HASH,
            'all_created_containers_removed':True,'original_image_unchanged':True,
            'authorized_qemu_execution_performed':True,
            'boot_performed':False,'firmware_write_performed':False,'physical_device_access_performed':False,
            'host_mounts_or_guest_network_enabled':False,'vendor_linux_3_0_35_syscalls_verified':False,
            'runtime_probes':p}

def accepted(h=None,c=None,p=None):
    H,C=sources();H=h if h is not None else H;C=c if c is not None else C
    return r.audit(p if p is not None else report(),H,C,
                   expected_header=r.sha_git_blob(H),expected_calls=r.sha_git_blob(C))

class OfflineChecks(unittest.TestCase):
    def test_synthetic_complete_pass(self):
        a=accepted()
        self.assertEqual(a['result'],'PASS_PINNED_PUBLIC_LAB126_SOURCE_SYSCALL_CROSSWALK_ONLY')
        self.assertEqual(len(a['source_crosswalk']),14)
        self.assertEqual(a['observed_guest_qemu_trace_record_count'],55)
        self.assertFalse(a['actual_vendor_syscall_dispatch_verified'])
    def test_no_sources_default_no_side_effects(self):
        with patch.object(r,'safe_read',side_effect=AssertionError('No filesystem access')):
            out=io.StringIO()
            with redirect_stdout(out): self.assertEqual(r.main([]),2)
        j=json.loads(out.getvalue());self.assertEqual(j['result'],'HOLD')
    def test_missing_one_option_holds(self):
        with redirect_stdout(io.StringIO()) as o:
            self.assertEqual(r.main(['--header','somefile']),2)
        self.assertEqual(json.loads(o.getvalue())['hold_category'],'ALL_THREE_PINNED_INPUTS_REQUIRED')
    def test_positive_cli_synthetic_requires_real_pins(self):
        h,c=sources()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'h').write_bytes(h);(root/'c').write_bytes(c);(root/'r').write_text(json.dumps(report()))
            with redirect_stdout(io.StringIO()) as o:
                rc=r.main(['--header',str(root/'h'),'--calls',str(root/'c'),'--r49-report',str(root/'r')])
            self.assertEqual(rc,2)
            self.assertEqual(json.loads(o.getvalue())['hold_category'],'PUBLIC_SOURCE_GIT_BLOB_PIN_MISMATCH')
    def test_static_bundle_exact_pins(self):
        self.assertEqual(len(r.HEADER_BLOB),40);self.assertEqual(len(r.CALLS_BLOB),40)
        self.assertEqual(r.UPSTREAM_V3_HEADER_BLOB,r.HEADER_BLOB)
        self.assertEqual(len(r.ENTRY_EXPECTED),14)
        self.assertEqual(sum(x[0] for x in r.BASELINE.values()),55)
    def test_program_not_declared_kindled(self):
        a=accepted()
        for k in ('actual_vendor_syscall_dispatch_verified','target_musl_linux_3_0_35_compatibility_verified',
                  'source_to_running_kernel_binary_reproducibility_verified','recovery_verified'):
            self.assertIs(a[k],False)
        self.assertEqual(a['kindle_ssh_sessions'],0)
    def test_changed_pin_refused(self):
        h,c=sources()
        with self.assertRaisesRegex(r.AuditHold,'PIN_MISMATCH'):
            r.audit(report(),h,c)
    def test_kernel_header_comment_ignored(self):
        h,c=sources();self.assertEqual(r.parse_header(h+b'/* #define __NR_brk (__NR_SYSCALL_BASE+ 77) */\n')['brk'],45)
    def test_header_missing_sentinel_holds(self):
        h,c=sources();h=h.replace(b'__NR_brk (__NR_SYSCALL_BASE+ 45)',b'__NR_brk (__NR_SYSCALL_BASE+ 46)')
        with self.assertRaisesRegex(r.AuditHold,'SENTINELS'):
            r.parse_header(h)
    def test_header_missing_marker_holds(self):
        h,c=sources();h=h.replace(b'arch/arm/include/asm/unistd.h',b'other-source')
        with self.assertRaisesRegex(r.AuditHold,'MARKER'):
            r.parse_header(h)
    def test_calls_missing_marker_holds(self):
        h,c=sources();c=c.replace(b'included thrice',b'included once')
        with self.assertRaisesRegex(r.AuditHold,'MARKER'):
            r.parse_calls(c)
    def test_calls_group_order_holds(self):
        h,c=sources();c=c.replace(b'/* 125 */',b'/* 126 */')
        with self.assertRaisesRegex(r.AuditHold,'GROUP_MARKER'):
            r.parse_calls(c)
    def test_missing_call_holds(self):
        h,c=sources();c=c.replace(b'CALL(sys_mmap2)',b'')
        with self.assertRaisesRegex(r.AuditHold,'CARDINALITY'):
            r.parse_calls(c)
    def test_wrong_source_mapping_holds(self):
        h,c=sources();c=c.replace(b'CALL(sys_mmap2)',b'CALL(sys_ni_syscall)')
        with self.assertRaisesRegex(r.AuditHold,'HEADER_TO_CALLS_MISMATCH:mmap2'):
            accepted(c=c)
    def test_invalid_baseline_result_holds(self):
        x=report();x['result']='HOLD'
        with self.assertRaisesRegex(r.AuditHold,'BASELINE_NOT_A_PASS'):
            accepted(p=x)
    def test_wrong_image_id_holds(self):
        x=report();x['original_image_id_sha256']='sha256:'+'0'*64
        with self.assertRaisesRegex(r.AuditHold,'RUNTIME_PINS_MISMATCH'):
            accepted(p=x)
    def test_untraced_output_mismatch_holds(self):
        x=report();x['runtime_probes']['busybox_true_control']['expected_applet_output_matches']=False
        with self.assertRaisesRegex(r.AuditHold,'UNTRACED_CONTROL_FAILED'):
            accepted(p=x)
    def test_unrecognized_syscall_holds(self):
        x=report();x['runtime_probes']['busybox_true_trace']['trace']['syscall_names'].append('openat2')
        with self.assertRaisesRegex(r.AuditHold,'TRACE_NAME_SET_CHANGED'):
            accepted(p=x)
    def test_changed_syscall_records_holds(self):
        x=report();x['runtime_probes']['busybox_true_trace']['trace']['syscall_record_count']=18
        with self.assertRaisesRegex(r.AuditHold,'TRACE_COUNTS_CHANGED'):
            accepted(p=x)
    def test_enosys_holds(self):
        x=report();x['runtime_probes']['busybox_true_trace']['trace']['trace_enosys_record_count']=1
        with self.assertRaisesRegex(r.AuditHold,'TRACE_COUNTS_CHANGED'):
            accepted(p=x)
    def test_unverified_cleanup_holds(self):
        x=report();x['all_created_containers_removed']=False
        with self.assertRaisesRegex(r.AuditHold,'EXECUTION_OR_CLEANUP_INVALID'):
            accepted(p=x)
    def test_writes_to_device_holds(self):
        x=report();x['firmware_write_performed']=True
        with self.assertRaisesRegex(r.AuditHold,'SAFETY_OR_SCOPE_INVALID'):
            accepted(p=x)
    def test_missing_local_file_holds(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(r.AuditHold,'MISSING_OR_SYMLINK'):
                r.safe_read(Path(td)/'missing',2000)
    def test_symlink_holds(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'original').write_bytes(b'abc');(p/'link').symlink_to('original')
            with self.assertRaisesRegex(r.AuditHold,'MISSING_OR_SYMLINK'):
                r.safe_read(p/'link',2000)
    def test_no_network_docker_or_device_calls_in_script(self):
        code=S.read_text()
        for mod in ('requests','urllib','socket','subprocess','paramiko'):
            self.assertNotIn('import '+mod,code)
        self.assertNotIn('docker run',code)
        self.assertNotIn('ssh root@',code)

if __name__=='__main__':unittest.main()
