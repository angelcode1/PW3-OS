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


    def test_old_busybox_compatibility(self):
        for command in c.PROBES.values():
            self.assertNotIn("grep -E", command)
        script = c.bounded_probe("kernel_version.txt", "uname -a")
        self.assertIn("dd bs=1 count=32768", script)
        self.assertNotIn("head -c", script)
        self.assertNotIn("/tmp/", script)

    def test_bounded_remote_capture_on_posix_shell(self):
        short = subprocess.run(["sh", "-c", c.bounded_probe("test", "printf 'abcdef'")],
                               capture_output=True, timeout=5)
        self.assertEqual(short.returncode, 0)
        self.assertEqual(short.stdout, b"abcdef")
        long = subprocess.run(["sh", "-c", c.bounded_probe("test", "yes a")],
                              capture_output=True, timeout=10)
        self.assertEqual(long.returncode, 0)
        self.assertEqual(len(long.stdout), c.MAX_BYTES)

    def test_library_inventory_avoids_remote_grep(self):
        self.assertEqual(c.PROBES["library_names.txt"],
                         "ls -1 /lib/ /usr/lib/ 2>/dev/null || true")

if __name__ == "__main__":
    unittest.main()
