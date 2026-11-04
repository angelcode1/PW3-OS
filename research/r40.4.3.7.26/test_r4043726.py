"""Synthetic-only tests, without proprietary stage, QEMU or hardware."""
import importlib.util
import io
from pathlib import Path
import struct
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("R4043726-INTERP-GUEST-RESOLVE-READONLY.py")
spec = importlib.util.spec_from_file_location("r3726", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def elf32(interp=b"/lib/ld.so\0", cls=1, endian="<", machine=40):
    if cls == 1:
        hsize, psize, phoffoff, structoff, offp, sizep = 52, 32, 28, 40, 4, 16
    else:
        hsize, psize, phoffoff, structoff, offp, sizep = 64, 56, 32, 52, 8, 32
    header = bytearray(hsize)
    header[:7] = b"\x7fELF" + bytes([cls, 1 if endian == "<" else 2, 1])
    struct.pack_into(endian + "HH", header, 16, 3, machine)
    struct.pack_into(endian + ("I" if cls == 1 else "Q"), header, phoffoff, hsize)
    struct.pack_into(endian + "HHH", header, structoff, hsize, psize, 1)
    ph = bytearray(psize)
    struct.pack_into(endian + "I", ph, 0, 3)
    struct.pack_into(endian + ("I" if cls == 1 else "Q"), ph, offp, hsize + psize)
    struct.pack_into(endian + ("I" if cls == 1 else "Q"), ph, sizep, len(interp))
    return bytes(header + ph + interp)


class TestElf(unittest.TestCase):
    def test_elf32_little(self):
        hdr, items = mod.inspect_elf(io.BytesIO(elf32()))
        self.assertEqual((hdr["cls"], hdr["machine"]), (1, 40))
        self.assertEqual(items, [("/lib/ld.so", False)])

    def test_elf32_big(self):
        hdr, items = mod.inspect_elf(io.BytesIO(elf32(endian=">")))
        self.assertEqual(hdr["data"], 2)
        self.assertEqual(items, [("/lib/ld.so", False)])

    def test_elf64(self):
        hdr, items = mod.inspect_elf(io.BytesIO(elf32(cls=2, machine=183)))
        self.assertEqual(hdr["cls"], 2)
        self.assertEqual(items, [("/lib/ld.so", False)])

    def test_padding(self):
        hdr, items = mod.inspect_elf(io.BytesIO(elf32(b"/lib/ld.so\0\0\0")))
        self.assertEqual(items, [("/lib/ld.so", True)])

    def test_embedded_nonzero_rejected(self):
        with self.assertRaises(mod.Hold):
            mod.inspect_elf(io.BytesIO(elf32(b"/lib/ld.so\0x\0")))

    def test_bad_elf_header(self):
        bad = bytearray(elf32())
        struct.pack_into("<I", bad, 28, 99999)
        with self.assertRaises(mod.Hold):
            mod.inspect_elf(io.BytesIO(bad))

    def test_non_elf(self):
        self.assertIsNone(mod.inspect_elf(io.BytesIO(b"not an elf")))

    def test_dotdot_literal_rejected(self):
        with self.assertRaises(mod.Hold):
            mod.interpreter_literal(b"/lib/../ld.so\0")


class TestGuestResolution(unittest.TestCase):
    def test_direct_regular(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            (r / "lib").mkdir()
            (r / "lib/ld.so").write_bytes(elf32())
            found, hops = mod.resolve_guest(r, "/lib/ld.so")
            self.assertEqual((found, hops), (r / "lib/ld.so", 0))

    def test_relative_symlink_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            (r / "usr/lib").mkdir(parents=True)
            (r / "usr/lib/ld.so").write_bytes(elf32())
            (r / "lib").symlink_to("usr/lib")
            (r / "usr/lib/alias").symlink_to("ld.so")
            found, hops = mod.resolve_guest(r, "/lib/alias")
            self.assertEqual((found, hops), (r / "usr/lib/ld.so", 2))

    def test_absolute_symlink_guest_remap(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            (r / "guest").mkdir()
            (r / "guest/ld.so").write_bytes(elf32())
            (r / "alias").symlink_to("/guest/ld.so")
            found, hops = mod.resolve_guest(r, "/alias")
            self.assertEqual((found, hops), (r / "guest/ld.so", 1))

    def test_relative_parent_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            (r / "usr/lib").mkdir(parents=True)
            (r / "usr/ld.so").write_bytes(elf32())
            (r / "usr/lib/alias").symlink_to("../ld.so")
            found, hops = mod.resolve_guest(r, "/usr/lib/alias")
            self.assertEqual((found, hops), (r / "usr/ld.so", 1))

    def test_escape_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            (r / "escape").symlink_to("../../etc/passwd")
            with self.assertRaises(mod.Hold) as ctx:
                mod.resolve_guest(r, "/escape")
            self.assertEqual(ctx.exception.code, "GUEST_ESCAPE_HOLD")

    def test_symlink_cycle_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            (r / "a").symlink_to("b")
            (r / "b").symlink_to("a")
            with self.assertRaises(mod.Hold) as ctx:
                mod.resolve_guest(r, "/a", max_symlinks=3)
            self.assertEqual(ctx.exception.code, "GUEST_SYMLINK_LIMIT_HOLD")

    def test_absent_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(mod.Hold) as ctx:
                mod.resolve_guest(Path(tmp), "/missing")
            self.assertEqual(ctx.exception.code, "GUEST_ABSENT_HOLD")

    def test_parent_file_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            (r / "file").write_bytes(b"hello")
            with self.assertRaises(mod.Hold) as ctx:
                mod.resolve_guest(r, "/file/child")
            self.assertEqual(ctx.exception.code, "GUEST_PARENT_NONDIR_HOLD")

    def test_abi_candidate_and_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            (r / "lib").mkdir()
            hdr, _ = mod.inspect_elf(io.BytesIO(elf32()))
            (r / "lib/ld.so").write_bytes(elf32())
            cat, hops = mod.classify_guest_target(r, "/lib/ld.so", hdr)
            self.assertEqual(cat, "GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE")
            self.assertEqual(hops, 0)
            (r / "lib/ld.so").write_bytes(elf32(machine=183))
            cat, _ = mod.classify_guest_target(r, "/lib/ld.so", hdr)
            self.assertEqual(cat, "GUEST_ELF_ABI_HEADER_MISMATCH_HOLD")

    def test_non_elf_regular_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            (r / "lib").mkdir()
            (r / "lib/ld.so").write_bytes(b"not an elf")
            hdr, _ = mod.inspect_elf(io.BytesIO(elf32()))
            cat, _ = mod.classify_guest_target(r, "/lib/ld.so", hdr)
            self.assertEqual(cat, "GUEST_REGULAR_NONELF_HOLD")

    def test_scan_zero_source_elf_not_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = Path(tmp)
            (r / "hello").write_bytes(b"plain text")
            summary = mod.scan(r, 1)
            self.assertEqual(summary["result"], "HOLD_BASELINE_OR_ELF_PARSE")
            self.assertFalse(summary["boot_authorized"])
            self.assertFalse(summary["prune_authorized"])
            self.assertFalse(summary["runtime_loader_resolved"])
            self.assertNotIn("/lib", str(summary))


class TestSyntheticStage(unittest.TestCase):
    def test_exact_synthetic_baseline_with_guest_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "lib").mkdir()
            (root / "bin").mkdir()
            # ELF loader itself has no PT_INTERP. Synthetic only; never executed.
            loader = bytearray(elf32())
            struct.pack_into("<H", loader, 44, 0)
            (root / "lib/ld.so").write_bytes(loader)
            for i in range(82):
                if i < 19:
                    interp = b"/lib/ld.so\0" + (b"\0\0" if i >= 9 else b"")
                    obj = elf32(interp)
                else:
                    obj = bytes(loader)
                (root / "bin" / ("elf-%03d" % i)).write_bytes(obj)
            summary = mod.scan(root, 83)
            self.assertEqual(summary["result"], "STATIC_INTERP_GUEST_PATH_CLASSIFICATION_ONLY")
            self.assertEqual(summary["counts"], {
                "rootfs_regular_files": 83, "elf_objects": 83,
                "interp_segments": 19, "strict_literal": 9,
                "padding_only_literal": 10})
            self.assertEqual(summary["path_resolution_counts"], {
                "GUEST_REGULAR_ELF_ABI_HEADER_CANDIDATE": 19})
            self.assertFalse(summary["runtime_loader_resolved"])
            self.assertNotIn("ld.so", str(summary))

    def test_malformed_source_elf_is_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "corrupt").write_bytes(b"\x7fELF\x01")
            summary = mod.scan(root, 1)
            self.assertEqual(summary["result"], "HOLD_BASELINE_OR_ELF_PARSE")
            self.assertEqual(summary["source_parse_holds"], {"ELF_SHORT_IDENT": 1})



if __name__ == "__main__":
    unittest.main()
