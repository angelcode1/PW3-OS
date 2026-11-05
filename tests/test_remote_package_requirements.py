"""Acceptance-contract tests only; no package fetch, stage mutation or device I/O."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "research" / "package-requirements" / "remote-transfers.json"


class TestRemotePackageRequirements(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PLAN.read_text(encoding="utf-8"))

    def test_exact_package_set(self):
        self.assertEqual(set(self.data["requested_packages"]), {
            "openssh", "openssh-server", "openssh-sftp-server", "rsync"})

    def test_architecture(self):
        self.assertEqual(self.data["target_arch"], "armv7")

    def test_sftp_required_for_modern_scp(self):
        self.assertIn("scp_default_sftp_without_dash_O", self.data["desired_capabilities"])
        self.assertIn("openssh-sftp-server", self.data["requested_packages"])

    def test_rsync_ebook_transfer(self):
        self.assertIn("rsync_over_ssh_incremental_ebook_transfers", self.data["desired_capabilities"])

    def test_not_installed(self):
        self.assertFalse(self.data["image_integrated"])
        self.assertFalse(self.data["service_enabled"])

    def test_deferred_state(self):
        self.assertEqual(self.data["status"], "DEFERRED_UNTIL_FULL_VALIDATION")
        self.assertFalse(self.data["independent_boot_and_recovery_verified"])

    def test_staging_and_device_gates(self):
        for key in ("current_stage_modifications_authorized", "boot_authorized",
                    "device_access_authorized", "firmware_write_authorized", "prune_authorized"):
            with self.subTest(key=key):
                self.assertFalse(self.data[key])

    def test_required_validation_gates(self):
        for key in ("kernel_userspace_abi_verified", "offline_arm_guest_integration_verified",
                    "sftp_upload_download_verified", "modern_scp_without_legacy_mode_verified",
                    "rsync_incremental_ebook_transfer_verified"):
            with self.subTest(key=key):
                self.assertFalse(self.data[key])

    def test_not_bootable(self):
        self.assertEqual(self.data["immutable_hold"], "NOT_BOOTABLE")


if __name__ == "__main__":
    unittest.main()
