"""R3877.60.3: host-only launch-permission and fail-closed diagnostic tests.

No real Docker, ARM execution, network, mounting, or Kindle activity.
"""
import io
import json
from pathlib import Path
import stat
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

import pw3_r3877_60_3_qemu_enosys as m


def completed(code=0, stdout='', stderr=''):
    return SimpleNamespace(returncode=code, stdout=stdout, stderr=stderr)


def sample_state(status='exited', running=False, oom=False, exit_code=0, error=''):
    return {'Status':status,'Running':running,'OOMKilled':oom,'ExitCode':exit_code,'Error':error}


class ModeAndStartSafety(unittest.TestCase):
    def test_01_default_preflight_calls_no_docker(self):
        with patch.object(m.base,'docker',side_effect=AssertionError('Docker must not be touched')):
            with redirect_stdout(io.StringIO()) as output:
                code=m.main([])
        self.assertEqual(code,2)
        j=json.loads(output.getvalue())
        self.assertEqual(j['milestone'],'R3877.60.3')
        self.assertFalse(j['docker_used'])
        self.assertFalse(j['host_seccomp_injection_performed'])
        self.assertEqual(j['immutable_hold'],'NOT_BOOTABLE')

    def test_02_pinned_launcher_and_arm_modes_verified(self):
        self.assertTrue(m.verify_pins())
        for p,role in ((m.LAUNCHER,'launcher'),(m.ARM,'arm_probe')):
            self.assertTrue(m.require_executable_mode(p,role))
            self.assertEqual(stat.S_IMODE(p.stat().st_mode)&0o111,0o111)

    def test_03_default_without_only_writable_opt_in(self):
        with patch.object(m.base,'docker',side_effect=AssertionError('Docker must not be touched')):
            with redirect_stdout(io.StringIO()) as output:
                code=m.main(['--allow-disposable-writable-layer'])
        self.assertEqual(code,2)
        self.assertEqual(json.loads(output.getvalue())['hold_category'],
                         'WRITABLE_OPT_IN_REQUIRES_OFFLINE_QEMU_AUTHORIZATION')

    def test_04_readable_but_not_executable_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'launcher';p.write_bytes(b'not an ELF')
            p.chmod(0o644)
            with self.assertRaisesRegex(m.Hold,'EXECUTABLE_MODE_UNVERIFIED:launcher'):
                m.require_executable_mode(p,'launcher')

    def test_05_only_owner_execute_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'launcher';p.write_bytes(b'x');p.chmod(0o744)
            with self.assertRaisesRegex(m.Hold,'EXECUTABLE_MODE_UNVERIFIED'):
                m.require_executable_mode(p,'launcher')

    def test_06_world_writable_executable_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'launcher';p.write_bytes(b'x');p.chmod(0o777)
            with self.assertRaisesRegex(m.Hold,'EXECUTABLE_MODE_UNVERIFIED'):
                m.require_executable_mode(p,'launcher')

    def test_07_group_writable_executable_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'launcher';p.write_bytes(b'x');p.chmod(0o775)
            with self.assertRaisesRegex(m.Hold,'EXECUTABLE_MODE_UNVERIFIED'):
                m.require_executable_mode(p,'launcher')

    def test_08_regular_read_execute_is_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'launcher';p.write_bytes(b'x');p.chmod(0o755)
            self.assertTrue(m.require_executable_mode(p,'launcher'))

    def test_09_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'real';p.write_bytes(b'x');p.chmod(0o755)
            link=Path(d)/'link';link.symlink_to(p)
            with self.assertRaisesRegex(m.Hold,'EXECUTABLE_FILE_UNSAFE'):
                m.require_executable_mode(link,'launcher')

    def test_10_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(m.Hold,'EXECUTABLE_FILE_UNSAFE'):
                m.require_executable_mode(Path(d)/'missing','launcher')

    def test_11_invalid_role_rejected(self):
        with self.assertRaisesRegex(m.Hold,'EXECUTABLE_ROLE_INVALID'):
            m.require_executable_mode(m.LAUNCHER,'unknown')

    def test_12_docker_permission_denied_redacted(self):
        d=m.classify_start_result('arm_control',completed(1,stderr='Error: permission denied /Users/example/private'),
                                  sample_state(status='created',exit_code=128,error='private filepath'))
        self.assertEqual(d['docker_start_error_classification'],'DOCKER_START_PERMISSION_DENIED')
        self.assertEqual(d['state_status'],'created')
        self.assertFalse(d['raw_output_published'])
        self.assertTrue(d['state_error_present'])
        self.assertNotIn('/Users/',json.dumps(d))

    def test_13_exec_format_error_classified(self):
        d=m.classify_start_result('arm_control',completed(1,stderr='exec format error'),sample_state('created'))
        self.assertEqual(d['docker_start_error_classification'],'DOCKER_START_EXEC_FORMAT_ERROR')

    def test_14_missing_interpreter_classified(self):
        d=m.classify_start_result('arm_control',completed(1,stderr='no such file or directory'),sample_state('created'))
        self.assertEqual(d['docker_start_error_classification'],'DOCKER_START_MISSING_FILE_OR_INTERPRETER')

    def test_15_op_not_permitted_classified(self):
        d=m.classify_start_result('arm_control',completed(1,stderr='Operation not permitted'),sample_state('created'))
        self.assertEqual(d['docker_start_error_classification'],'DOCKER_START_OPERATION_NOT_PERMITTED')

    def test_16_unclassified_error_is_not_claimed_success(self):
        d=m.classify_start_result('arm_control',completed(1,stderr='odd error'),sample_state('created'))
        self.assertEqual(d['docker_start_error_classification'],'DOCKER_START_FAILED_UNCLASSIFIED')

    def test_17_successful_exit_reported_without_premature_claim(self):
        d=m.classify_start_result('arm_control',completed(0,stdout='R60_HOST_FILTER_INSTALLED\n'),sample_state())
        self.assertEqual(d['state_status'],'exited')
        self.assertEqual(d['state_exit_code'],0)
        self.assertEqual(d['docker_start_error_classification'],'NO_CLASSIFIED_DOCKER_START_ERROR')
        self.assertFalse(d['state_oomkilled'])

    def test_18_oom_state_retained(self):
        d=m.classify_start_result('stat_control',completed(1),sample_state(oom=True,exit_code=137))
        self.assertTrue(d['state_oomkilled'])
        self.assertEqual(d['state_exit_code'],137)

    def test_19_missing_oom_is_explicitly_unknown(self):
        bad=sample_state();bad.pop('OOMKilled')
        d=m.classify_start_result('stat_trace',completed(0),bad)
        self.assertIsNone(d['state_oomkilled'])

    def test_20_unrecognized_status_redacted(self):
        d=m.classify_start_result('arm_trace',completed(1),sample_state(status='private unusual status'))
        self.assertEqual(d['state_status'],'UNKNOWN')
        self.assertNotIn('private',json.dumps(d))

    def test_21_bad_probe_name_rejected(self):
        with self.assertRaisesRegex(m.Hold,'GUEST_PROBE_NAME_UNKNOWN'):
            m.classify_start_result('host-command',completed(0),sample_state())

    def test_22_bad_state_type_rejected(self):
        with self.assertRaisesRegex(m.Hold,'DOCKER_GUEST_STATE_NOT_OBJECT'):
            m.classify_start_result('arm_control',completed(0),'bad')

    def test_23_host_mounts_still_disallowed(self):
        args=m.create_guest(['/bin/busybox','stat'],False)
        self.assertIn('--network',args)
        self.assertIn('none',args)
        self.assertIn('--cap-drop',args)
        self.assertIn('ALL',args)
        self.assertIn('--user',args)
        self.assertNotIn('--privileged',args)
        self.assertNotIn('--mount',args)
        self.assertNotIn('--volume',args)

    def test_24_guest_prestart_readback_checks_enforced(self):
        import inspect
        code=inspect.getsource(m.run)
        self.assertIn("require_executable_mode(readback,'launcher')",code)
        self.assertIn("'qemu' if remote==GUEST_QEMU else 'arm_probe'",code)
        self.assertLess(code.index("require_executable_mode(readback,'launcher')"),
                        code.index("cp=base.docker(['start','--attach',cid]"))
        self.assertLess(code.index("classify_start_result(name,cp,state)"),
                        code.index("raise Hold('GUEST_EXIT_OOM_STATE_UNVERIFIED:'"))

    def test_25_immutable_pins_and_volume_cleanup(self):
        import inspect
        s=inspect.getsource(m.run)
        self.assertIn("['rm','-f','-v',cid]",s)
        self.assertIn("['volume','inspect',name]",s)
        self.assertIn('base.HELPER_DIGEST',s)
        self.assertEqual(m.MILESTONE,'R3877.60.3')

    def test_26_no_seccomp_profile_override(self):
        self.assertNotIn('--security-opt seccomp=unconfined',' '.join(m.create_guest(('/bin/busybox','true'),False)))

    def test_27_trusted_exact_elf_digests(self):
        self.assertEqual(m.bounded_digest(m.LAUNCHER,16384),m.LAUNCHER_SHA)
        self.assertEqual(m.bounded_digest(m.ARM,16384),m.ARM_SHA)

if __name__=='__main__':unittest.main()
