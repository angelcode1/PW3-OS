#!/usr/bin/env python3
"""Host-only synthetic R3877.49.1 tests; no Docker daemon or Kindle operations."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r491', HERE / 'pw3_r3877_49_1_trace_output_diagnostic.py')
r491 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r491)

PARENT_ID = r491.PARENT_ID


def guest_info(argv, readonly=True):
    return {
        'Image': PARENT_ID, 'State': {'Status':'created','Running':False},
        'Path':'/usr/bin/qemu-arm-static', 'Args':list(argv),
        'Config': {'User':'65534:65534','Entrypoint':['/usr/bin/qemu-arm-static']},
        'HostConfig': {'ReadonlyRootfs':readonly,'NetworkMode':'none','Privileged':False,
                       'Binds':None,'Devices':None,'DeviceRequests':None,
                       'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges'],
                       'PidsLimit':64,'Memory':268435456}, 'Mounts': []}


class UnitTests(unittest.TestCase):
    def test_default_preflight_zero_docker(self):
        with patch.object(r491,'docker',side_effect=AssertionError('No Docker permitted')):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r491.main([]),2)
            self.assertEqual(r491.preflight()['result'],'HOLD')
    def test_writable_flag_alone_refuses_without_docker(self):
        with patch.object(r491,'docker',side_effect=AssertionError('No Docker permitted')):
            stream=io.StringIO()
            with redirect_stdout(stream):
                self.assertEqual(r491.main(['--allow-disposable-writable-layer']),2)
            self.assertEqual(json.loads(stream.getvalue())['error_category'], 'WRITABLE_OPT_IN_REQUIRES_QEMU_AUTHORIZATION')
    def test_explicit_authorized_arg(self):
        with patch.object(r491,'run',return_value={'result':'PASS_QEMU_ARMV7_SYSCALL_TRACE_OBSERVATION_ONLY'}) as method:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r491.main(['--authorize-offline-qemu']),0)
            method.assert_called_once_with(False)
    def test_explicit_writable_opt_in_arg(self):
        with patch.object(r491,'run',return_value={'result':'HOLD'}) as method:
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r491.main(['--authorize-offline-qemu','--allow-disposable-writable-layer']),2)
            method.assert_called_once_with(True)
    def test_header_and_pins(self):
        self.assertTrue(r491.HEX_IMAGE.fullmatch(r491.PARENT_ID))
        self.assertEqual(len(r491.QEMU_SHA256),64)
        self.assertEqual(len(r491.BUSYBOX_SHA256),64)
        self.assertEqual(len(r491.PROBES),4)
        self.assertEqual(r491.PROBES[1][1],('-strace','-0','/bin/busybox','/bin/busybox','true'))
    def test_strict_guest_default_policy(self):
        self.assertTrue(r491.validate_guest(guest_info(['--version']), ('--version',), True))
    def test_writable_mode_requires_writable_inspect(self):
        with self.assertRaisesRegex(r491.Hold,'ROOTFS_POLICY'):
            r491.validate_guest(guest_info(['--version']), ('--version',), False)
    def test_readonly_mode_requires_readonly_inspect(self):
        with self.assertRaisesRegex(r491.Hold,'ROOTFS_POLICY'):
            r491.validate_guest(guest_info(['--version'],False), ('--version',), True)
    def test_network_denied(self):
        g=guest_info(['--version']);g['HostConfig']['NetworkMode']='bridge'
        with self.assertRaisesRegex(r491.Hold,'NETWORK'):
            r491.validate_guest(g,('--version',),True)
    def test_privileged_denied(self):
        g=guest_info(['--version']);g['HostConfig']['Privileged']=True
        with self.assertRaisesRegex(r491.Hold,'PRIVILEGE'):
            r491.validate_guest(g,('--version',),True)
    def test_capabilities_denied(self):
        g=guest_info(['--version']);g['HostConfig']['CapDrop']=[]
        with self.assertRaisesRegex(r491.Hold,'CAPABILITIES'):
            r491.validate_guest(g,('--version',),True)
    def test_bind_denied(self):
        g=guest_info(['--version']);g['HostConfig']['Binds']=['/host:/target']
        with self.assertRaisesRegex(r491.Hold,'MOUNT'):
            r491.validate_guest(g,('--version',),True)
    def test_devices_denied(self):
        g=guest_info(['--version']);g['HostConfig']['Devices']=[{'PathOnHost':'/dev/disk'}]
        with self.assertRaisesRegex(r491.Hold,'DEVICE'):
            r491.validate_guest(g,('--version',),True)
    def test_uid_denied(self):
        g=guest_info(['--version']);g['Config']['User']='0'
        with self.assertRaisesRegex(r491.Hold,'IDENTITY'):
            r491.validate_guest(g,('--version',),True)
    def test_resource_limits_denied(self):
        g=guest_info(['--version']);g['HostConfig']['Memory']=0
        with self.assertRaisesRegex(r491.Hold,'RESOURCE_LIMIT'):
            r491.validate_guest(g,('--version',),True)
    def test_stopped_required(self):
        g=guest_info(['--version']);g['State']['Status']='running'
        with self.assertRaisesRegex(r491.Hold,'STOPPED'):
            r491.validate_guest(g,('--version',),True)
    def test_arg_exact_required(self):
        g=guest_info(['-help'])
        with self.assertRaisesRegex(r491.Hold,'ARGV'):
            r491.validate_guest(g,('--help',),True)
    def test_cp_readonly_classification(self):
        e=r491.classify_cp_error(subprocess.CompletedProcess([],1,'','Error response from daemon: container rootfs is marked read-only\n'))
        self.assertEqual(e['classification'],'READONLY_ROOTFS_COPY_REJECTED')
        self.assertNotIn('Error response',json.dumps(e))
        self.assertFalse(e['raw_error_published'])
    def test_cp_ro_filesystem_alternative(self):
        e=r491.classify_cp_error(subprocess.CompletedProcess([],1,'','read-only file system'))
        self.assertEqual(e['classification'],'READONLY_ROOTFS_COPY_REJECTED')
    def test_cp_unknown_failure_not_relaxed(self):
        e=r491.classify_cp_error(subprocess.CompletedProcess([],1,'','permission denied'))
        self.assertEqual(e['classification'],'DOCKER_CP_FAILURE_UNCLASSIFIED')
    def test_cp_no_error_not_classified_ro(self):
        e=r491.classify_cp_error(subprocess.CompletedProcess([],0,'',''))
        self.assertEqual(e['classification'],'DOCKER_CP_FAILURE_UNCLASSIFIED')
    def test_diff_pin_accepts_only_emulator_and_ancestors(self):
        with patch.object(r491,'docker',return_value=subprocess.CompletedProcess([],0,'C /usr/bin\nA /usr/bin/qemu-arm-static\n','')):
            self.assertTrue(r491.audit_diff('a'*64)['allowed_changes_only'])
    def test_diff_rejects_file_written_by_guest(self):
        with patch.object(r491,'docker',return_value=subprocess.CompletedProcess([],0,'A /usr/bin/qemu-arm-static\nA /etc/pwned\n','')):
            with self.assertRaisesRegex(r491.Hold,'UNEXPECTED_FILESYSTEM'):
                r491.audit_diff('a'*64)
    def test_diff_rejects_absent_emulator(self):
        with patch.object(r491,'docker',return_value=subprocess.CompletedProcess([],0,'','')):
            with self.assertRaisesRegex(r491.Hold,'UNEXPECTED_FILESYSTEM'):
                r491.audit_diff('a'*64)
    def test_guest_create_writable_and_readonly_separated(self):
        self.assertIn('--read-only',r491.guest_create(('--version',),True))
        self.assertNotIn('--read-only',r491.guest_create(('--version',),False))
        for flag in ('--network','--cap-drop','--pids-limit','--memory','--security-opt','--pull'):
            self.assertIn(flag,r491.guest_create(('--version',),False))
    def test_probe_versions(self):
        self.assertTrue(r491.probe_ok('qemu_version',0,'qemu-arm version 10.0.4 (v10.0.4)'))
        self.assertTrue(r491.probe_ok('busybox_true_trace',0,''))
        self.assertTrue(r491.probe_ok('busybox_uname_trace',0,'armv7l\n'))
        self.assertTrue(r491.probe_ok('busybox_echo_trace',0,r491.ECHO_MARKER+'\n'))
        self.assertFalse(r491.probe_ok('busybox_uname_trace',0,'aarch64\n'))
        self.assertFalse(r491.probe_ok('busybox_echo_trace',0,'wrong\n'))
    def test_parser_names_and_no_sensitive_arguments(self):
        raw='123 mmap2(0xdeadbeef,4096,3) = 0x1234\n123 openat(AT_FDCWD,"/private/file",0) = -1 errno=2\n'
        out=r491.parse_qemu_trace('HELLO\n',raw)
        self.assertEqual(out['syscall_record_count'],2)
        self.assertEqual(out['syscall_names'],['mmap2','openat'])
        self.assertNotIn('/private',json.dumps({k:v for k,v in out.items() if k!='normalized_program_output'}))
        self.assertEqual(out['normalized_program_output'],'HELLO\n')
    def test_parser_enosys_and_unknown(self):
        raw='98 clock_gettime64(0) = -1 errno=38 (Function not implemented)\n98 Unknown syscall 999\n'
        x=r491.parse_qemu_trace('',raw)
        self.assertEqual(x['trace_enosys_record_count'],1)
        self.assertEqual(x['trace_unknown_record_count'],1)
        self.assertEqual(x['syscall_names'],['clock_gettime64'])
        self.assertEqual(x['post_v3_mainline_syscall_name_candidates_seen'],['clock_gettime64'])
    def test_parser_no_trace_is_not_a_pass(self):
        x=r491.parse_qemu_trace('armv7l\n','')
        self.assertEqual(x['syscall_record_count'],0)
    def test_parser_malformed_very_long_line_refused(self):
        with self.assertRaisesRegex(r491.Hold,'TRACE_LINE_OVERSIZE'):
            r491.parse_qemu_trace('','x'*8193)
    def test_parser_capture_budget_refused(self):
        with self.assertRaisesRegex(r491.Hold,'TRACE_CAPTURE_OVERSIZE'):
            r491.parse_qemu_trace('x'*1000001,'')
    def test_parser_ordinary_stdout_not_dropped(self):
        x=r491.parse_qemu_trace(r491.ECHO_MARKER+'\n','101 write(1,0,2) = 2\n')
        self.assertEqual(x['normalized_program_output'],r491.ECHO_MARKER+'\n')
    def test_parser_unknown_names_have_no_raw_paths(self):
        x=r491.parse_qemu_trace('','232 some_syscall(0x111, "/file") = -1\n')
        self.assertEqual(x['syscall_names'],['some_syscall'])
    def test_invalid_docker_argv(self):
        with self.assertRaisesRegex(r491.Hold,'INVALID_DOCKER_ARGV'):
            r491.docker(['cp',None])
    def test_inspect_empty_json(self):
        with patch.object(r491,'docker',return_value=subprocess.CompletedProcess([],0,'[]','')):
            with self.assertRaisesRegex(r491.Hold,'INSPECT_INVALID'):
                r491.inspect('image','x')
    def test_elf_and_sha(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'elf';b=bytearray(64);b[:6]=b'\x7fELF\x01\x01';struct.pack_into('<H',b,18,40);struct.pack_into('<I',b,36,0x05000400);p.write_bytes(b)
            self.assertEqual(r491.elf_summary(p),{'bits':32,'machine':40,'e_flags':'0x05000400'})
            self.assertEqual(r491.sha256_file(p),hashlib.sha256(b).hexdigest())
    def test_no_image_build_commit_or_host_mount_in_source(self):
        source=Path(r491.__file__).read_text()
        for forbidden in ("docker(['commit'", "docker(['build'", "docker(['import'", "docker(['pull'", "docker(['run'", "docker(['volume'", "docker(['mount'", "docker(['exec'"):
            self.assertNotIn(forbidden,source)


class SyntheticLifecycle(unittest.TestCase):
    def simulate(self, *, allow_writable=True, cp_error='read-only file system', diff_extra=False,
                 missing_trace=False, fail_applet=False, unknown_trace=False, extra_true_stdout=False):
        containers={};issued=[];seq=[0]
        def fake_docker(argv,timeout=100,allow_nonzero=False):
            a=list(argv);issued.append(a)
            if a[:2]==['version','--format']:
                return subprocess.CompletedProcess(a,0,json.dumps({'Arch':'arm64'}),'')
            if a[:2]==['image','inspect']:
                if a[2]==r491.PARENT:
                    js={'Id':PARENT_ID,'Os':'linux','Architecture':'arm','Variant':'v7'}
                elif a[2]==r491.HELPER:
                    js={'Id':'sha256:'+'2'*64,'Os':'linux','Architecture':'arm64','RepoDigests':[r491.HELPER_DIGEST]}
                else:raise AssertionError(a)
                return subprocess.CompletedProcess(a,0,json.dumps([js]),'')
            if a[0]=='create':
                seq[0]+=1;cid=f'{seq[0]:064x}';name=a[a.index('--name')+1]
                if 'guest-' in name:
                    arr=a[a.index(r491.PARENT)+1:]
                    js=guest_info(arr,readonly='--read-only' in a)
                else:
                    js={'Image':'sha256:'+'2'*64 if 'helper' in name else PARENT_ID,
                        'State':{'Status':'created','Running':False}}
                containers[cid]=js
                return subprocess.CompletedProcess(a,0,cid+'\n','')
            if a[:2]==['container','inspect']:
                if a[2] not in containers:
                    return subprocess.CompletedProcess(a,1,'','Error: No such container: '+a[2])
                return subprocess.CompletedProcess(a,0,json.dumps([containers[a[2]]]),'')
            if a[0]=='cp':
                dest=a[-1];src=a[-2]
                if ':' in dest and '/usr/bin/qemu-arm-static' in dest:
                    cid=dest.split(':')[0]
                    if containers[cid]['HostConfig']['ReadonlyRootfs']:
                        return subprocess.CompletedProcess(a,1,'',cp_error)
                    return subprocess.CompletedProcess(a,0,'','')
                if ':' not in dest:
                    p=Path(dest);p.parent.mkdir(parents=True,exist_ok=True)
                    b=bytearray(64);b[:6]=b'\x7fELF\x02\x01' if '/qemu' in src else b'\x7fELF\x01\x01'
                    struct.pack_into('<H',b,18,183 if '/qemu' in src else 40)
                    if '/qemu' not in src:struct.pack_into('<I',b,36,0x05000400)
                    p.write_bytes(b)
                    return subprocess.CompletedProcess(a,0,'','')
                raise AssertionError(a)
            if a[:2]==['start','--attach']:
                cid=a[2];c=containers[cid];arr=tuple(c['Args'])
                c['State']={'Status':'exited','Running':False,'OOMKilled':False,'ExitCode':0}
                out={('--version',):'qemu-arm version 10.0.4 (v10.0.4)\n',
                     ('-strace','-0','/bin/busybox','/bin/busybox','true'):'',
                     ('-strace','-0','/bin/busybox','/bin/busybox','uname','-m'):'armv7l\n',
                     ('-strace','-0','/bin/busybox','/bin/busybox','echo',r491.ECHO_MARKER):r491.ECHO_MARKER+'\n'}[arr]
                err='' if arr==('--version',) else '123 openat(AT_FDCWD,"/secret",0) = 4\n123 exit_group(0)\n'
                if extra_true_stdout and arr[-1]=='true':out='TRACE_ANOMALY: /private/sample\n'
                if unknown_trace and err:err='123 Unknown syscall 999\n'+err
                if missing_trace and 'uname' in arr:err=''
                if fail_applet and 'echo' in arr:
                    out='wrong\n';c['State']['ExitCode']=1
                return subprocess.CompletedProcess(a,0,out,err)
            if a[0]=='diff':
                return subprocess.CompletedProcess(a,0,'A /usr/bin/qemu-arm-static\n'+('A /etc/unexpected\n' if diff_extra else ''),'')
            if a[:2]==['rm','-f']:
                containers.pop(a[2],None)
                return subprocess.CompletedProcess(a,0,a[2],'')
            raise AssertionError(a)
        def fake_hash(p):
            return r491.BUSYBOX_SHA256 if Path(p).name=='busybox' else r491.QEMU_SHA256
        with patch.object(r491,'docker',side_effect=fake_docker),patch.object(r491,'sha256_file',side_effect=fake_hash):
            result=r491.run(allow_writable=allow_writable)
        return result,issued,containers
    def test_full_three_applet_trace(self):
        r,issued,containers=self.simulate()
        self.assertEqual(r['result'],'PASS_QEMU_ARMV7_SYSCALL_TRACE_OBSERVATION_ONLY',r)
        self.assertEqual(len(r['runtime_probes']),4)
        self.assertTrue(all(r['runtime_probes'][n]['trace']['syscall_record_count']>=2 for n in r491.TRACE_PROBES))
        self.assertTrue(r['all_created_containers_removed'])
        self.assertTrue(r['original_image_unchanged'])
        self.assertFalse(r['vendor_linux_3_0_35_syscalls_verified'])
        self.assertEqual(containers,{})
        self.assertFalse(any(x[0] in ('run','commit','build','import','pull') for x in issued))
    def test_readonly_without_writable_optin_stops_before_execution(self):
        r,issued,containers=self.simulate(allow_writable=False)
        self.assertEqual(r['result'],'HOLD')
        self.assertEqual(r['error_category'],'READONLY_COPY_REJECTED_WRITABLE_FALLBACK_NOT_AUTHORIZED')
        self.assertFalse(r['authorized_qemu_execution_performed'])
        self.assertTrue(r['all_created_containers_removed'])
        self.assertFalse(any(x[0]=='start' for x in issued))
    def test_permission_denied_does_not_open_writable_fallback(self):
        r,issued,_=self.simulate(cp_error='permission denied')
        self.assertEqual(r['result'],'HOLD')
        self.assertEqual(r['error_category'],'READONLY_GUEST_COPY_FAILED_UNCLASSIFIED')
        self.assertFalse(any(x[0]=='start' for x in issued))
    def test_unexpected_trace_stdout_leads_to_hold_but_reports_bounded_shape(self):
        r,issued,containers=self.simulate(extra_true_stdout=True)
        self.assertEqual(r['result'],'HOLD')
        self.assertEqual(r['error_category'],'GUEST_PROBE_FAILED:busybox_true_trace')
        info=r['runtime_probes']['busybox_true_trace']
        self.assertEqual(info['exit_code'],0)
        self.assertFalse(info['expected_applet_output_matches'])
        self.assertTrue(info['unexpected_program_output_never_suppressed'])
        self.assertGreater(info['trace']['normalized_program_output_bytes'],0)
        self.assertEqual(info['trace']['nontrace_stdout_line_count'],1)
        self.assertTrue(r['all_created_containers_removed'])
        public=json.dumps(r)
        self.assertNotIn('TRACE_ANOMALY',public)
        self.assertNotIn('/private/sample',public)
        self.assertEqual(containers,{})
        self.assertEqual(len([a for a in issued if a[:2]==['start','--attach']]),2)

    def test_missing_guest_trace_holds(self):
        r,issued,containers=self.simulate(missing_trace=True)
        self.assertEqual(r['result'],'HOLD')
        self.assertEqual(r['error_category'],'NO_QEMU_GUEST_SYSCALL_TRACE:busybox_uname_trace')
        self.assertTrue(r['all_created_containers_removed'])
        self.assertEqual(containers,{})
    def test_unexpected_guest_output_holds(self):
        r,_,_=self.simulate(fail_applet=True)
        self.assertEqual(r['result'],'HOLD')
        self.assertEqual(r['error_category'],'GUEST_PROBE_FAILED:busybox_echo_trace')
    def test_diff_extra_refused_before_guest_start(self):
        r,issued,_=self.simulate(diff_extra=True)
        self.assertEqual(r['result'],'HOLD')
        self.assertFalse(any(x[0]=='start' for x in issued))
    def test_unknown_syscall_is_reported_not_kernel_compatible(self):
        r,_,_=self.simulate(unknown_trace=True)
        self.assertEqual(r['result'],'PASS_QEMU_ARMV7_SYSCALL_TRACE_OBSERVATION_ONLY')
        self.assertTrue(all(r['runtime_probes'][n]['trace']['trace_unknown_record_count']==1 for n in r491.TRACE_PROBES))
        self.assertFalse(r['vendor_linux_3_0_35_syscalls_verified'])


class UnmatchedOutputDiagnosticTests(unittest.TestCase):
    def test_nontrace_stdout_captured_without_contents(self):
        raw='42 brk(0) = 4\n'
        x=r491.parse_qemu_trace('QEMU-extra: /private/path pwd=SECRET\n',raw)
        self.assertEqual(x['syscall_record_count'],1)
        self.assertEqual(x['nontrace_stdout_line_count'],1)
        self.assertEqual(x['nontrace_stderr_line_count'],0)
        self.assertGreater(x['normalized_program_output_bytes'],0)
        public={k:v for k,v in x.items() if k!='normalized_program_output'}
        s=json.dumps(public)
        for secret in ('QEMU-extra','/private/path','SECRET','pwd='):
            self.assertNotIn(secret,s)
        item=x['unclassified_line_samples'][0]
        self.assertEqual(item['channel'],'stdout')
        self.assertEqual(item['classification'],'OTHER_UNCLASSIFIED')
        self.assertLessEqual(len(item['character_class_prefix']),64)
    def test_pid_like_missing_parenthesis_is_not_silently_dropped(self):
        x=r491.parse_qemu_trace('','234 exit_group => unknown\n')
        self.assertEqual(x['syscall_record_count'],0)
        self.assertEqual(x['normalized_program_output'],'234 exit_group => unknown\n')
        self.assertEqual(x['unclassified_line_samples'][0]['classification'],
                         'PID_PREFIX_NOT_RECOGNISED_AS_SYSCALL')
    def test_blank_line_is_visible(self):
        x=r491.parse_qemu_trace('\r\n','101 brk(0) = 0\n')
        self.assertEqual(x['unclassified_line_count'],1)
        self.assertEqual(x['unclassified_line_samples'][0]['classification'],'BLANK_UNCLASSIFIED')
        self.assertFalse(r491.probe_ok('busybox_true_trace',0,x['normalized_program_output']))
    def test_safe_ascii_character_classes(self):
        m=r491.unmatched_line_metadata('p9: /etc/passwd\x1b\n', 'stdout')
        self.assertEqual(m['character_class_prefix'],'A9*_*AAA*AAAAAAE')
        self.assertNotIn('/etc/passwd',json.dumps(m))
    def test_samples_limited_to_eight_with_exact_counts(self):
        x=r491.parse_qemu_trace('X\n'*40,'101 brk(0) = 4\n')
        self.assertEqual(x['unclassified_line_count'],40)
        self.assertEqual(len(x['unclassified_line_samples']),8)
    def test_no_nontrace_has_zero_bytes_and_samples(self):
        x=r491.parse_qemu_trace('','101 brk(0) = 4\n')
        self.assertEqual(x['normalized_program_output_bytes'],0)
        self.assertEqual(x['unclassified_line_samples'],[])
    def test_invalid_channel_is_rejected(self):
        with self.assertRaisesRegex(r491.Hold,'TRACE_CHANNEL_INVALID'):
            r491.unmatched_line_metadata('X','other')
    def test_unclassified_eight_kib_line_rejected(self):
        with self.assertRaisesRegex(r491.Hold,'TRACE_UNCLASSIFIED_LINE_INVALID'):
            r491.unmatched_line_metadata('X'*8193,'stderr')

if __name__=='__main__':
    unittest.main()
