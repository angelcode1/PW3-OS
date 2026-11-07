#!/usr/bin/env python3
"""R3877.44: explicitly authorized, disposable local ARMv7 BusyBox QEMU recheck.

No Docker activity in preflight. No Kindle, flash, privileged Docker, binfmt
registration, host mounts, networking, or use of the private R13 staging tree.
This is a diagnostic, not an image build or boot gate.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import uuid

MILESTONE = "R3877.44"
HOLD = "NOT_BOOTABLE"
PARENT = "pw3-r3877-signed-alpine:3.24.3-armv7-dc1ddfaf03ed"
HELPER = "tonistiigi/binfmt:qemu-v10.0.4"
HELPER_DIGEST = "tonistiigi/binfmt@sha256:8f58e6214f4cc9dc83ce8f5acad1ece508eb6b20e696a8c1e9f274481982c541"
QEMU_ARM_SHA256 = "3347b95a4006c1eb19b93ba09469a2c42b04fe5d89a430ce96cbf2a2367cf5c1"
HISTORIC_EXIT = 127
HISTORIC_STDERR = "-help: applet not found\n"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def elf_summary(path):
    data = Path(path).read_bytes()[:65536]
    if len(data) < 52 or data[:4] != b"\x7fELF" or data[5] != 1:
        raise ValueError("ELF_MISSING_OR_NOT_LITTLE_ENDIAN")
    elf_class = data[4]
    if elf_class not in (1, 2):
        raise ValueError("ELF_CLASS_UNSUPPORTED")
    machine = struct.unpack_from("<H", data, 18)[0]
    e_flags = struct.unpack_from("<I", data, 36 if elf_class == 1 else 48)[0]
    return {"bits": 32 if elf_class == 1 else 64, "machine": machine, "e_flags": f"0x{e_flags:08x}"}


def classify_historic(exit_code, output):
    if exit_code == HISTORIC_EXIT and output == HISTORIC_STDERR:
        return "BUSYBOX_SINGLE_HYPHEN_HELP_APPLET_ERROR"
    return "HOLD_UNCLASSIFIED"


def classify_probe(name, rc, output):
    if name == "qemu_version":
        return "PASS" if rc == 0 and "qemu-arm version 10.0.4" in output else "HOLD"
    if name == "busybox_double_dash_help":
        return "PASS" if rc == 0 and "BusyBox" in output else "HOLD"
    if name == "busybox_true":
        return "PASS" if rc == 0 and not output else "HOLD"
    if name == "busybox_uname_machine":
        return "PASS" if rc == 0 and re.fullmatch(r"[A-Za-z0-9_-]{2,32}\s*", output) else "HOLD"
    return "HOLD"


class DockerFailure(RuntimeError):
    pass


def docker(args, *, timeout=80, allow_nonzero=False):
    if not isinstance(args, (list, tuple)) or not all(isinstance(a, str) for a in args):
        raise DockerFailure("INVALID_ARGV")
    cp = subprocess.run(["docker", *args], capture_output=True, text=True, errors="replace", timeout=timeout, check=False)
    if len(cp.stdout) + len(cp.stderr) > 1_000_000:
        raise DockerFailure("OVERSIZE_DOCKER_OUTPUT")
    if cp.returncode and not allow_nonzero:
        # Avoid exposing arbitrary raw command errors to a published report.
        raise DockerFailure("DOCKER_OPERATION_FAILED: " + args[0])
    return cp


def inspect_image(ref):
    cp = docker(["image", "inspect", ref])
    try:
        j = json.loads(cp.stdout)
        if not isinstance(j, list) or len(j) != 1:
            raise ValueError()
        image = j[0]
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", image["Id"]):
            raise ValueError()
        return image
    except (ValueError, KeyError, IndexError, TypeError) as ex:
        raise DockerFailure("IMAGE_INSPECT_JSON_INVALID") from ex


def emit(report):
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


def preflight():
    return {
        "milestone": MILESTONE,
        "result": "HOLD",
        "diagnostic": "R3877_44_OFFLINE_PREFLIGHT_NO_DOCKER",
        "r3877_6_historic_probe": {
            "exit_code": HISTORIC_EXIT,
            "output_sha256": hashlib.sha256(HISTORIC_STDERR.encode()).hexdigest(),
            "classification": classify_historic(HISTORIC_EXIT, HISTORIC_STDERR),
            "previous_classifier_unreliable_for_this_output": True,
        },
        "authorized_qemu_execution_performed": False,
        "firmware_write_performed": False,
        "boot_performed": False,
        "physical_device_access_performed": False,
        "immutable_hold": HOLD,
    }


def execute():
    report = preflight()
    report.update({
        "diagnostic": "R3877_44_OFFLINE_QEMU_RECHECK_ATTEMPTED",
        "result": "HOLD",
        "offline_qemu_authorized": True,
        "authorized_qemu_execution_performed": False,
        "parent_image_unchanged": False,
        "disposable_image_removed": False,
        "temporary_containers_removed": False,
        "no_guest_network_or_host_mounts": True,
        "binfmt_registration_changed": False,
        "privileged_container_invoked": False,
        "runtime_probes": {},
    })
    prep_id = None
    helper_id = None
    derived_id = None
    baseline_parent_id = None
    errors = []
    try:
        version = docker(["version", "--format", "{{json .Server}}"])
        j = json.loads(version.stdout)
        # These may be camel case variants in different Docker versions.
        os_arch = str(j.get("Arch", j.get("Architecture", ""))).lower()
        if os_arch not in ("arm64", "aarch64"):
            raise DockerFailure("DOCKER_SERVER_NOT_AARCH64")
        report["docker_server_architecture"] = os_arch

        parent = inspect_image(PARENT)
        baseline_parent_id = parent["Id"]
        if parent.get("Os") != "linux" or parent.get("Architecture") != "arm" or parent.get("Variant", "") not in ("v7", "7"):
            raise DockerFailure("PARENT_NOT_LINUX_ARMV7")
        helper = inspect_image(HELPER)
        if helper.get("Os") != "linux" or helper.get("Architecture") not in ("arm64", "aarch64"):
            raise DockerFailure("HELPER_NOT_LINUX_ARM64")
        if HELPER_DIGEST not in helper.get("RepoDigests", []):
            raise DockerFailure("HELPER_REPO_DIGEST_PIN_MISMATCH")
        report["original_image_id_sha256"] = baseline_parent_id
        report["helper_image_id_sha256"] = helper["Id"]

        suffix = uuid.uuid4().hex[:14]
        prep_name = "pw3-r44-prep-" + suffix
        helper_name = "pw3-r44-helper-" + suffix
        with tempfile.TemporaryDirectory(prefix="pw3-r44-") as d:
            root = Path(d)
            helper_id = docker(["create", "--platform", "linux/arm64", "--network", "none",
                                "--name", helper_name, "--entrypoint", "/bin/true", HELPER]).stdout.strip()
            if not re.fullmatch(r"[0-9a-f]{64}", helper_id):
                raise DockerFailure("HELPER_CONTAINER_ID_INVALID")
            # An ARM64 QEMU executable copied from a STOPPED helper, never run on macOS.
            qemu_path = root / "qemu-arm-static"
            docker(["cp", "-L", helper_id + ":/usr/bin/qemu-arm", str(qemu_path)])
            if sha256_file(qemu_path) != QEMU_ARM_SHA256:
                raise DockerFailure("QEMU_BINARY_SHA256_PIN_MISMATCH")
            if elf_summary(qemu_path)["machine"] != 183 or elf_summary(qemu_path)["bits"] != 64:
                raise DockerFailure("QEMU_NOT_AARCH64_ELF64")

            prep_id = docker(["create", "--platform", "linux/arm/v7", "--network", "none",
                              "--name", prep_name, "--entrypoint", "/bin/true", PARENT]).stdout.strip()
            if not re.fullmatch(r"[0-9a-f]{64}", prep_id):
                raise DockerFailure("PREPARATION_CONTAINER_ID_INVALID")
            busybox = root / "busybox"
            docker(["cp", "-L", prep_id + ":/bin/busybox", str(busybox)])
            elf = elf_summary(busybox)
            if elf["bits"] != 32 or elf["machine"] != 40:
                raise DockerFailure("BUSYBOX_NOT_ARM32_ELF")
            report["busybox_elf"] = elf
            report["busybox_sha256"] = sha256_file(busybox)

            # Writes only to the stopped, disposable copy; never to the tagged parent.
            docker(["cp", str(qemu_path), prep_id + ":/usr/bin/qemu-arm-static"])
            cp = docker(["commit", prep_id], timeout=90)
            derived_id = cp.stdout.strip()
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", derived_id):
                raise DockerFailure("DERIVED_IMAGE_ID_INVALID")
            derived = inspect_image(derived_id)
            if derived["Id"] != derived_id or derived.get("Architecture") != "arm" or derived.get("Variant") not in ("v7", "7"):
                raise DockerFailure("DERIVED_PLATFORM_OR_ID_MISMATCH")
            report["disposable_image_id_sha256"] = derived_id

            probes = [
                ("qemu_version", ["--version"]),
                ("busybox_double_dash_help", ["/bin/busybox", "--help"]),
                ("busybox_true", ["/bin/busybox", "true"]),
                ("busybox_uname_machine", ["/bin/busybox", "uname", "-m"]),
            ]
            for name, argv in probes:
                report["authorized_qemu_execution_performed"] = True
                cp = docker(["run", "--rm", "--platform", "linux/arm/v7", "--network", "none",
                             "--read-only", "--pids-limit", "64", "--memory", "256m", "--cap-drop=ALL",
                             "--security-opt=no-new-privileges", "--entrypoint", "/usr/bin/qemu-arm-static",
                             derived_id, *argv], timeout=90, allow_nonzero=True)
                output = cp.stdout + cp.stderr
                status = classify_probe(name, cp.returncode, output)
                report["runtime_probes"][name] = {
                    "status": status,
                    "exit_code": cp.returncode,
                    "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
                    "output_prefix": output[:300] if name in ("busybox_double_dash_help", "qemu_version", "busybox_uname_machine") else "",
                }
                if status != "PASS":
                    raise DockerFailure("GUEST_PROBE_HOLD:" + name)
            report["diagnostic"] = "R3877_44_ARM32_BUSYBOX_QEMU_PROBES_PASSED_NOT_BOOTABLE"
            report["result"] = "PASS_ARM32_BUSYBOX_QEMU_ONLY"
    except (DockerFailure, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        errors.append(str(exc).split("\n")[0][:130])
        report["result"] = "HOLD"
    finally:
        # Cleanup only named/identified resources we just created.
        cleanup = []
        for cid in (prep_id, helper_id):
            if cid:
                try:
                    cp = docker(["rm", "-f", cid], allow_nonzero=True)
                    cleanup.append(("container", cp.returncode == 0))
                except (DockerFailure, OSError, subprocess.TimeoutExpired):
                    cleanup.append(("container", False))
        if derived_id:
            try:
                cp = docker(["image", "rm", "--no-prune", derived_id], allow_nonzero=True)
                cleanup.append(("image", cp.returncode == 0))
            except (DockerFailure, OSError, subprocess.TimeoutExpired):
                cleanup.append(("image", False))
        report["temporary_containers_removed"] = bool(prep_id and helper_id) and all(ok for kind, ok in cleanup if kind == "container")
        report["disposable_image_removed"] = bool(derived_id) and all(ok for kind, ok in cleanup if kind == "image")
        if baseline_parent_id:
            try:
                report["parent_image_unchanged"] = inspect_image(PARENT)["Id"] == baseline_parent_id
            except DockerFailure:
                report["parent_image_unchanged"] = False
        if not report["parent_image_unchanged"] or not report["temporary_containers_removed"] or not report["disposable_image_removed"]:
            if report["result"].startswith("PASS"):
                report["result"] = "HOLD_CLEANUP_OR_PARENT_ID_UNVERIFIED"
            errors.append("CLEANUP_OR_PARENT_IMAGE_CHECK_INCOMPLETE")
        if errors:
            report["error_category"] = errors[0]
        report["immutable_hold"] = HOLD
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--authorize-offline-qemu", action="store_true", help="explicitly run in disposable offline Docker guests; never touches Kindle")
    args = ap.parse_args(argv)
    report = execute() if args.authorize_offline_qemu else preflight()
    emit(report)
    return 0 if report.get("result") == "PASS_ARM32_BUSYBOX_QEMU_ONLY" else 2


if __name__ == "__main__":
    sys.exit(main())
