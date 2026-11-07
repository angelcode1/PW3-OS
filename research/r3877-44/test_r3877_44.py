import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("r44", HERE / "pw3_r3877_44_busybox_qemu_recheck.py")
r44 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r44)


class R44HostTests(unittest.TestCase):
    def test_historical_classifier_exact(self):
        self.assertEqual(r44.classify_historic(127, "-help: applet not found\n"), "BUSYBOX_SINGLE_HYPHEN_HELP_APPLET_ERROR")

    def test_historical_classifier_refuses_blank(self):
        self.assertEqual(r44.classify_historic(127, ""), "HOLD_UNCLASSIFIED")

    def test_historical_classifier_refuses_missing_loader(self):
        self.assertEqual(r44.classify_historic(127, "No such file or directory\n"), "HOLD_UNCLASSIFIED")

    def test_historical_classifier_refuses_changed_exit(self):
        self.assertEqual(r44.classify_historic(0, "-help: applet not found\n"), "HOLD_UNCLASSIFIED")

    def test_historical_output_hash_matches_user(self):
        self.assertEqual(hashlib.sha256(r44.HISTORIC_STDERR.encode()).hexdigest(), "686d46a259767f1b59961c24aa5e885e1bb178829e9bd8886f34b68723d6ac8c")

    def test_correct_help_pass(self):
        self.assertEqual(r44.classify_probe("busybox_double_dash_help", 0, "BusyBox v1.37.0\n"), "PASS")

    def test_wrong_help_never_passes(self):
        self.assertEqual(r44.classify_probe("busybox_double_dash_help", 127, "-help: applet not found\n"), "HOLD")

    def test_help_missing_banner_never_passes(self):
        self.assertEqual(r44.classify_probe("busybox_double_dash_help", 0, "usage\n"), "HOLD")

    def test_qemu_version_pass(self):
        self.assertEqual(r44.classify_probe("qemu_version", 0, "qemu-arm version 10.0.4"), "PASS")

    def test_qemu_version_wrong_version_hold(self):
        self.assertEqual(r44.classify_probe("qemu_version", 0, "qemu-arm version 10.2.3"), "HOLD")

    def test_busybox_true_pass(self):
        self.assertEqual(r44.classify_probe("busybox_true", 0, ""), "PASS")

    def test_busybox_true_unexpected_output_hold(self):
        self.assertEqual(r44.classify_probe("busybox_true", 0, "Oops\n"), "HOLD")

    def test_uname_pass(self):
        self.assertEqual(r44.classify_probe("busybox_uname_machine", 0, "armv7l\n"), "PASS")

    def test_uname_unsafe_multiline_hold(self):
        self.assertEqual(r44.classify_probe("busybox_uname_machine", 0, "a\nb\n"), "HOLD")

    def test_unknown_probe_hold(self):
        self.assertEqual(r44.classify_probe("unexpected", 0, ""), "HOLD")

    def test_preflight_has_no_execution(self):
        with patch.object(r44, "docker", side_effect=AssertionError("Docker used!")):
            x = r44.preflight()
        self.assertFalse(x["authorized_qemu_execution_performed"])
        self.assertEqual(x["immutable_hold"], "NOT_BOOTABLE")

    def test_cli_preflight_no_docker_exit2(self):
        with patch.object(r44, "docker", side_effect=AssertionError("Docker used!")):
            out = io.StringIO()
            with redirect_stdout(out):
                code = r44.main([])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(out.getvalue())["result"], "HOLD")

    def test_cli_requires_explicit_flag(self):
        with patch.object(r44, "execute", side_effect=AssertionError("Unexpected execution")):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r44.main([]), 2)

    def test_cli_authorized_result(self):
        with patch.object(r44, "execute", return_value={"result": "PASS_ARM32_BUSYBOX_QEMU_ONLY", "immutable_hold": "NOT_BOOTABLE"}):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(r44.main(["--authorize-offline-qemu"]), 0)

    def test_invalid_docker_arg_raises(self):
        with self.assertRaises(r44.DockerFailure):
            r44.docker([1234])

    def test_elf32_arm(self):
        b = bytearray(64)
        b[:6] = b"\x7fELF\x01\x01"
        struct.pack_into("<H", b, 18, 40)
        struct.pack_into("<I", b, 36, 0x05000400)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "busybox"
            p.write_bytes(b)
            self.assertEqual(r44.elf_summary(p), {"bits": 32, "machine": 40, "e_flags": "0x05000400"})

    def test_elf64_aarch64(self):
        b = bytearray(64)
        b[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", b, 18, 183)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "qemu-arm"
            p.write_bytes(b)
            self.assertEqual(r44.elf_summary(p)["machine"], 183)

    def test_bad_elf_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad"
            p.write_bytes(b"not an ELF")
            with self.assertRaises(ValueError):
                r44.elf_summary(p)

    def test_wrong_endian_elf_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad"
            p.write_bytes(b"\x7fELF\x01\x02" + b"\x00" * 60)
            with self.assertRaises(ValueError):
                r44.elf_summary(p)

    def test_sha256_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test"
            p.write_bytes(b"abc")
            self.assertEqual(r44.sha256_file(p), hashlib.sha256(b"abc").hexdigest())

    def test_inspect_json_malformed_hold(self):
        cp = subprocess.CompletedProcess([], 0, "not JSON", "")
        with patch.object(r44, "docker", return_value=cp):
            with self.assertRaises(r44.DockerFailure):
                r44.inspect_image("some-image")

    def test_inspect_wrong_count_hold(self):
        cp = subprocess.CompletedProcess([], 0, "[]", "")
        with patch.object(r44, "docker", return_value=cp):
            with self.assertRaises(r44.DockerFailure):
                r44.inspect_image("some-image")

    def test_inspect_valid(self):
        image = {"Id": "sha256:" + "1" * 64, "Architecture": "arm", "Variant": "v7"}
        cp = subprocess.CompletedProcess([], 0, json.dumps([image]), "")
        with patch.object(r44, "docker", return_value=cp):
            self.assertEqual(r44.inspect_image("something"), image)

    def test_frozen_refs(self):
        self.assertIn("3.24.3-armv7", r44.PARENT)
        self.assertEqual(len(r44.QEMU_ARM_SHA256), 64)
        self.assertIn("qemu-v10.0.4", r44.HELPER)


if __name__ == "__main__":
    unittest.main()
