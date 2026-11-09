"""Host synthetic regression tests, no device SSH."""
import contextlib
import hashlib
import io
import json
import struct
import subprocess
import unittest
from unittest.mock import Mock
import pw3_r3877_77_arm_syscall as m


class Tests(unittest.TestCase):
    def test_elf_header(self):
        b = m.generate_elf()
        self.assertEqual(b[:4], b'\x7fELF')
        self.assertEqual(b[4:8], bytes([1, 1, 1, 0]))
        self.assertEqual(struct.unpack_from('<HH', b, 16), (2, 40))
        self.assertEqual(struct.unpack_from('<I', b, 36)[0], 0x05000000)
        self.assertEqual(struct.unpack_from('<I', b, 24)[0], 0x10100)

    def test_segment(self):
        b = m.generate_elf()
        self.assertEqual(struct.unpack_from('<8I', b, 52),
                         (1, 0, 0x10000, 0x10000, len(b), len(b), 5, 0x1000))

    def test_exact_program(self):
        b = m.generate_elf()
        self.assertEqual(b[256:288], struct.pack('<8I', *m.ARM_WORDS))
        self.assertEqual(b[288:], m.MARKER)
        self.assertEqual(m.ARM_WORDS[1], 0xE28F1014)
        self.assertLess(len(b), 512)

    def test_no_interpreter_or_dynamic(self):
        b = m.generate_elf()
        self.assertEqual(struct.unpack_from('<H', b, 44)[0], 1)
        self.assertNotIn(b'/lib/ld', b)
        self.assertNotIn(b'PT_INTERP', b)

    def test_remote_cmd_bounded(self):
        remote = m.make_remote(m.generate_elf())
        self.assertIn('NOPE' if False else 'sha256sum', remote)
        self.assertIn(hashlib.sha256(m.generate_elf()).hexdigest(), remote)
        self.assertIn(' /tmp:tmpfs|/dev/shm:tmpfs|/run:tmpfs)', remote)
        self.assertIn('trap', remote)
        self.assertNotIn('mount -', remote)
        self.assertNotIn('mmcblk', remote)

    def test_opt_in_default_no_ssh(self):
        def fail(*args, **kwargs):
            raise AssertionError('no ssh expected')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(m.main([], runner=fail), 2)
        self.assertEqual(json.loads(out.getvalue())['result'], 'HOLD')

    def test_untrusted_target_rejected(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(m.main(['--target', 'root@host:badport', '--acknowledge-single-process-tmpfs-execution'],
                                    runner=lambda *_a, **_k: None), 2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'], 'INVALID_TARGET_OR_PORT')

    def test_no_tmpfs(self):
        c = Mock(returncode=42, stdout=b'')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(m.main(['--acknowledge-single-process-tmpfs-execution'],
                                    runner=lambda *a, **k: c), 2)
        r = json.loads(out.getvalue())
        self.assertEqual(r['hold_category'], 'NO_EXISTING_EXECUTABLE_TMPFS')
        self.assertFalse(r['device_execution_performed'])

    def test_success_still_not_bootable(self):
        c = Mock(returncode=0, stdout=m.MARKER)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(m.main(['--acknowledge-single-process-tmpfs-execution'],
                                    runner=lambda *a, **k: c), 0)
        r = json.loads(out.getvalue())
        self.assertEqual(r['result'], 'PASS_SINGLE_ARM_EABI_SYSCALL_ONLY')
        self.assertEqual(r['immutable_hold'], 'NOT_BOOTABLE')
        self.assertFalse(r['kernel_glibc_musl_compatibility_verified'])

    def test_false_output_refused(self):
        c = Mock(returncode=0, stdout=m.MARKER + b'other')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(m.main(['--acknowledge-single-process-tmpfs-execution'],
                                    runner=lambda *a, **k: c), 2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'],
                         'REMOTE_OUTPUT_OR_EXIT_UNEXPECTED')

    def test_timeout(self):
        def timeout(*args, **kwargs):
            raise subprocess.TimeoutExpired('ssh', 45)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(m.main(['--acknowledge-single-process-tmpfs-execution'],
                                    runner=timeout), 2)
        self.assertEqual(json.loads(out.getvalue())['hold_category'], 'SSH_UNAVAILABLE_OR_TIMEOUT')

    def test_no_private_hash_output(self):
        c = Mock(returncode=42, stdout=b'')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            m.main(['--acknowledge-single-process-tmpfs-execution'],runner=lambda *a,**k:c)
        self.assertNotIn(hashlib.sha256(m.generate_elf()).hexdigest(), out.getvalue())


if __name__ == '__main__':
    unittest.main()
