import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

p = Path(__file__).resolve().parents[1] / "tools/collect_pw3_readonly.py"
spec = importlib.util.spec_from_file_location("collector", p)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)

class CollectorTests(unittest.TestCase):
    def test_dry_run_default(self):
        r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("DRY_RUN_ONLY", r.stdout)

    def test_host_argument_rejection(self):
        with self.assertRaises(ValueError):
            c.remote_ssh("-bad", 2222, "uname -a")

    def test_port_rejection(self):
        with self.assertRaises(ValueError):
            c.remote_ssh("192.168.8.102", 0, "uname -a")

    def test_no_user_storage(self):
        paths = " ".join(c.OPTIONAL_FILES)
        self.assertNotIn("/mnt/us", paths)
        self.assertNotIn("id_rsa", paths)

    def test_symlinks_denied(self):
        self.assertIn('[ -L "$p" ]', c.file_script("/etc/fstab"))

    def test_fixed_read_only_probes(self):
        for cmd in c.PROBES.values():
            self.assertNotIn("mount ", cmd)
            self.assertNotIn("rm ", cmd)
            self.assertNotIn("lipc-", cmd)

    def test_limits(self):
        self.assertLessEqual(c.MAX_BYTES, 32768)

if __name__ == "__main__":
    unittest.main()
