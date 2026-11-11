import gzip
import hashlib
import importlib.util
import io
from pathlib import Path
import os
import tarfile
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("pw3_ko_updater", HERE / "koreader_update.py")
upd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upd)

class UpdaterTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        overrides = {
            "HOME": self.root / "koreader-data",
            "CACHE": self.root / "cache",
            "RELEASES": self.root / "releases",
            "CURRENT": self.root / "koreader",
            "STATE": self.root / "cache/state.json",
            "PENDING": self.root / "cache/pending.json",
            "LOG": self.root / "cache/events.log",
        }
        for key, value in overrides.items():
            cp = patch.object(upd, key, value)
            cp.start()
            self.addCleanup(cp.stop)
        upd.RELEASES.mkdir()
        upd.CACHE.mkdir()
    def create_tar(self, extra=None):
        archive = self.root / "demo.targz"
        with tarfile.open(archive, "w:gz") as t:
            def add(name, content=b"ok", mode=0o644):
                member = tarfile.TarInfo(name)
                member.size = len(content)
                member.mode = mode
                t.addfile(member, io.BytesIO(content))
            for name in upd.NEEDED:
                add("koreader/" + name, b"v2099.01" if name == "git-rev" else b"ok")
            add("koreader/fbink", mode=0o755)
            if extra:
                add(extra, b"unsafe")
        with gzip.open(archive, "rb") as f:
            raw = f.read()
        meta = {"revision": "v2099.01", "filename": "koreader-kindlepw2-v2099.01.targz",
                "tar_sha1": hashlib.sha1(raw).hexdigest(), "tar_size": len(raw)}
        return archive, meta
    def test_verified_uncompressed_hash_and_perms(self):
        archive, meta = self.create_tar()
        upd.verified_tar(archive, meta)
        dest = self.root / "unpack"
        upd.unpack(archive, dest)
        self.assertTrue((dest / "reader.lua").is_file())
        self.assertTrue(os.access(dest / "fbink", os.X_OK))
    def test_hash_mismatch_blocks(self):
        archive, meta = self.create_tar()
        meta["tar_sha1"] = "0" * 40
        with self.assertRaises(SystemExit):
            upd.verified_tar(archive, meta)
    def test_traversal_blocks(self):
        archive, meta = self.create_tar("koreader/../../escape")
        with self.assertRaises(SystemExit):
            upd.unpack(archive, self.root / "unpack")
        self.assertFalse((self.root / "escape").exists())
    def make_legacy(self):
        upd.CURRENT.mkdir()
        (upd.CURRENT / "reader.lua").write_text("original")
        candidate = upd.RELEASES / "v2099.01"
        candidate.mkdir()
        (candidate / "reader.lua").write_text("candidate")
        upd.atomic_json(upd.PENDING, {"revision": "v2099.01", "candidate": str(candidate)})
    def test_switch_and_automatic_rollback(self):
        self.make_legacy()
        with patch.object(upd, "smoke"):
            upd.activate()
        self.assertTrue(upd.CURRENT.is_symlink())
        self.assertEqual((upd.CURRENT / "reader.lua").read_text(), "candidate")
        self.assertTrue(upd.finish(False))
        self.assertEqual((upd.CURRENT / "reader.lua").read_text(), "original")
    def test_switch_and_healthy_accept(self):
        self.make_legacy()
        with patch.object(upd, "smoke"):
            upd.activate()
        self.assertFalse(upd.finish(True))
        self.assertEqual(upd.get_json(upd.STATE)["phase"], "healthy")
        self.assertEqual((upd.CURRENT / "reader.lua").read_text(), "candidate")
    def test_no_rollback_when_not_first_run(self):
        self.assertFalse(upd.finish(False))
    def test_userpatch_outside_app(self):
        launcher=(HERE / "pw3-koreader-managed.sh").read_text()
        lua=(HERE / "2-pw3os-autoupdate.lua").read_text()
        self.assertIn("KO_HOME=/mnt/us/pw3os/koreader-data", launcher)
        self.assertIn('python3 "$MANAGER" activate', launcher)
        self.assertIn('python3 "$MANAGER" first-launch-failed', launcher)
        self.assertIn("OTAManager:fetchAndProcessUpdate()", lua)
        self.assertIn("Device:install()", lua)

if __name__ == "__main__":
    unittest.main()
