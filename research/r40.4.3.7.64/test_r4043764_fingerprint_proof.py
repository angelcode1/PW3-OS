import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).with_name('R4043764-COMPAT-BRK-FINGERPRINT-PROOF.py')
spec = importlib.util.spec_from_file_location('r3764_proof', SCRIPT)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class FingerprintProofTest(unittest.TestCase):
    def test_reconstruction_matches_reported_blob_and_length(self):
        result = p.calculate(p.read_reference())
        self.assertEqual(result['reconstructed_size_bytes'], 59593)
        self.assertEqual(result['reconstructed_blob_git_sha1'], 'b4ed2a1f317de6c11f75582327d847b30eae2547')
        self.assertEqual(result['reconstructed_sha256'], p.RECONSTRUCTED_SHA256)

    def test_staged_reference_pin_unchanged(self):
        source = p.read_reference()
        self.assertEqual(len(source), 59582)
        self.assertEqual(p.git_blob(source), p.OLD_BLOB_SHA1)

    def test_only_exact_original_config_key_is_accepted(self):
        source = p.read_reference()
        self.assertEqual(source.count(p.BEFORE), 1)
        with self.assertRaisesRegex(ValueError, 'REFERENCE_PIN_MISMATCH_HOLD'):
            p.calculate(source.replace(p.BEFORE, p.AFTER))

    def test_no_runtime_or_provenance_claim(self):
        result = p.calculate(p.read_reference())
        for name in ('boot_authorized', 'device_access_authorized', 'firmware_write_authorized',
                     'amazon_config_full_bytes_compared', 'actual_amazon_archive_opened',
                     'actual_pw3_running_kernel_verified', 'r13_image_provenance_authenticated',
                     'kernel_abi_runtime_compatibility_verified', 'guest_execution_authorized'):
            self.assertFalse(result[name], name)
        self.assertEqual(result['immutable_hold'], 'NOT_BOOTABLE')

    def test_no_unsafe_execution(self):
        code = SCRIPT.read_text()
        for forbidden in ('subprocess', 'requests.', 'urllib', 'tarfile', 'os.system(', 'extractall('):
            self.assertNotIn(forbidden, code)

if __name__ == '__main__':
    unittest.main()
