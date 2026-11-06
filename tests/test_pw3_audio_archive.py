"""Host tests for the additive Bible reading-page audio metadata record."""
import pathlib
import shutil
import struct
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
READER = ROOT / "apps" / "pw3-bible" / "reader.c"


def write_archive(path, metadata):
    pages = [("T\tGenesis 1\n" + metadata).encode()] + [b"T\tHome\n"] * 1461
    offsets = [16 + 4 * (len(pages) + 1)]
    for page in pages:
        offsets.append(offsets[-1] + len(page))
    with open(path, "wb") as f:
        f.write(struct.pack("<8sII", b"PW3BIB1\0", len(pages), 1))
        f.write(struct.pack("<" + str(len(offsets)) + "I", *offsets))
        f.writelines(pages)


@unittest.skipUnless(shutil.which("cc"), "C compiler required")
class AudioArchiveTests(unittest.TestCase):
    def test_new_reader_accepts_metadata_and_rejects_malformed(self):
        with tempfile.TemporaryDirectory() as td:
            binary = pathlib.Path(td) / "reader-host"
            subprocess.run(["cc", "-O2", "-DPW3_HOST", str(READER), "-o", str(binary)], check=True)
            good = pathlib.Path(td) / "good.pw3"
            write_archive(good, "A\t1\t1\n")
            passed = subprocess.run([str(binary), str(good), "--verify"], capture_output=True, text=True)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertIn("Validated 1462 pages", passed.stdout)
            bad = pathlib.Path(td) / "bad.pw3"
            write_archive(bad, "A\t74\t1\n")
            failed = subprocess.run([str(binary), str(bad), "--verify"], capture_output=True)
            self.assertNotEqual(failed.returncode, 0)
            double = pathlib.Path(td) / "duplicate.pw3"
            write_archive(double, "A\t1\t1\nA\t1\t2\n")
            self.assertNotEqual(subprocess.run([str(binary), str(double), "--verify"],
                                               capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
