"""R4043725 synthetic standard-library unit tests. NO HARDWARE."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("R4043725-INVENTORY-COUNT-READONLY.py")
spec = importlib.util.spec_from_file_location("r3725", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestInventory(unittest.TestCase):
    def test_empty_stage_counts_agree(self):
        with tempfile.TemporaryDirectory() as d:
            result = mod.audit(Path(d), 0)
            self.assertTrue(result["independent_scanners_agree"])
            self.assertEqual(result["result"], "STANDALONE_INVENTORY_COUNTS_MATCH")

    def test_simple_nested_files(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "lib").mkdir()
            (root / "lib" / "ld.so").write_bytes(b"\0")
            (root / "file").write_bytes(b"hello")
            result = mod.audit(root, 2)
            self.assertEqual(result["current_regular_files"], 2)
            self.assertEqual(result["lstat_inode_type_counts"]["directories"], 1)

    def test_count_gap_is_hold(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "file").write_bytes(b"")
            result = mod.audit(Path(d), 3)
            self.assertEqual(result["prior_baseline_delta"], -2)
            self.assertEqual(result["result"], "INVENTORY_COUNT_GAP_HOLD")
            self.assertFalse(result["historic_inventory_membership_compared"])

    def test_symlinks_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "lib").mkdir()
            (root / "lib" / "real").write_bytes(b"abc")
            (root / "alias").symlink_to("lib")
            (root / "lib" / "alias").symlink_to("real")
            result = mod.audit(root, 1)
            self.assertEqual(result["current_regular_files"], 1)
            self.assertEqual(result["lstat_inode_type_counts"]["symlinks"], 2)
            self.assertTrue(result["independent_scanners_agree"])

    def test_absolute_link_never_followed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "outside").symlink_to("/private/etc/passwd")
            result = mod.audit(root, 0)
            self.assertEqual(result["symlink_literal_summary"]["absolute_symlink_literals"], 1)
            self.assertEqual(result["current_regular_files"], 0)

    def test_parent_link_counted_without_resolution(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "link").symlink_to("../wherever")
            result = mod.audit(root, 0)
            self.assertEqual(result["symlink_literal_summary"]["symlinks_with_parent_components"], 1)

    def test_stage_root_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "alias").symlink_to(root)
            with self.assertRaises(mod.Hold):
                mod.audit(root / "alias", 0)

    def test_missing_stage_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(mod.Hold):
                mod.audit(Path(d) / "missing", 0)

    def test_nonregular_node(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "file").write_bytes(b"hello")
            result = mod.audit(root, 1)
            self.assertEqual(result["lstat_inode_type_counts"]["regular_files"], 1)
            self.assertEqual(result["lstat_inode_type_counts"]["other_nodes"], 0)


if __name__ == "__main__":
    unittest.main()
