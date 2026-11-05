"""R4043732 synthetic-only attributes tests: never write real stage or access PW3."""
import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

HERE = Path(__file__).parent
SCRIPT = HERE / "R4043732-ARM-NUMERIC-ATTRIBUTES-READONLY.py"
spec = importlib.util.spec_from_file_location("r3732_under_test", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
PARENT = m.pinned_parent(HERE / m.PARENT_NAME)


def leb(n):
    buf = bytearray()
    while True:
        byte = n & 127
        n >>= 7
        buf.append(byte | (128 if n else 0))
        if not n:
            return bytes(buf)


def attrs(pairs=(), endian="<", extra=b""):
    payload = b"".join(leb(tag) + leb(value) for tag, value in pairs) + extra
    block = b"\x01" + struct.pack(endian + "I", 5 + len(payload)) + payload
    vendor = b"aeabi\x00" + block
    return b"A" + struct.pack(endian + "I", 4 + len(vendor)) + vendor


def elf_with_attributes(raw, contents):
    buf = bytearray(contents)
    attr_offset = len(buf)
    buf += raw
    while len(buf) % 4:
        buf += b"\0"
    shoff = len(buf)
    sh = bytearray(40)
    struct.pack_into("<I", sh, 4, 0x70000003)
    struct.pack_into("<II", sh, 16, attr_offset, len(raw))
    buf += sh
    struct.pack_into("<I", buf, 32, shoff)
    struct.pack_into("<HHH", buf, 46, 40, 1, 0)
    return bytes(buf)


class TestNumeric(unittest.TestCase):
    def test_parent_pin_success(self):
        self.assertTrue(PARENT.decode_aeabi(attrs([(6, 10)]))["cpu_arch_tag_present"])

    def test_parent_pin_refuses_modified(self):
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / m.PARENT_NAME
            src.write_bytes(b"tampered")
            with self.assertRaises(m.Hold) as ctx:
                m.pinned_parent(src)
            self.assertEqual(ctx.exception.category, "PARENT_SHA_MISMATCH")

    def test_parent_pin_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            link = Path(d) / m.PARENT_NAME
            link.symlink_to(HERE / m.PARENT_NAME)
            with self.assertRaises(m.Hold):
                m.pinned_parent(link)

    def test_numeric_values_and_unreported_vfp(self):
        blob = attrs([(6, 10), (10, 3), (27, 1)])
        got = m.parse_numeric_attributes(blob, "<", PARENT)
        self.assertEqual([got[t] for t in (6, 10, 27)], [10, 3, 1])
        self.assertIsNone(got[28])

    def test_big_endian(self):
        blob = attrs([(6, 11), (27, 2)], ">")
        self.assertEqual(m.parse_numeric_attributes(blob, ">", PARENT)[27], 2)
        with self.assertRaises(m.Hold):
            m.parse_numeric_attributes(blob, "<", PARENT)

    def test_unknown_tag_holds(self):
        with self.assertRaises(m.Hold) as ctx:
            m.parse_numeric_attributes(attrs([(6, 10)], extra=leb(150) + leb(1)), "<", PARENT)
        self.assertEqual(ctx.exception.category, "ATTRIBUTE_UNSUPPORTED_TAG_HOLD")

    def test_old_wrong_tag_length_refused(self):
        buf = bytearray(attrs([(6, 10)]))
        pos = 1 + 4 + 6 + 1
        length, = struct.unpack_from("<I", buf, pos)
        struct.pack_into("<I", buf, pos, length - 1)
        with self.assertRaises(m.Hold):
            m.parse_numeric_attributes(bytes(buf), "<", PARENT)

    def test_subsection_oversize_holds(self):
        buf = bytearray(attrs([(6, 10)]))
        struct.pack_into("<I", buf, 1 + 4 + 6 + 1, 99999)
        with self.assertRaises(m.Hold) as ctx:
            m.parse_numeric_attributes(bytes(buf), "<", PARENT)
        self.assertEqual(ctx.exception.category, "ATTRIBUTE_SUBSECTION_BOUNDS_HOLD")

    def test_section_header_extraction(self):
        fix_spec = importlib.util.spec_from_file_location("r3730_fixture", HERE / "support_r3730_fixture.py")
        fix = importlib.util.module_from_spec(fix_spec)
        fix_spec.loader.exec_module(fix)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "source"
            path.write_bytes(elf_with_attributes(attrs([(6, 10), (10, 3), (27, 1)]), fix.elf32()))
            p30 = PARENT.verify_import(HERE / PARENT.R30, PARENT.R30, PARENT.R30_SHA)
            p29 = p30.load_r29(HERE / p30.R29_NAME)
            p26 = p29.load_pinned(HERE / "R4043726-INTERP-GUEST-RESOLVE-READONLY.py")
            values = m.read_numeric_tags(PARENT, p26, path)
            self.assertEqual([values[t] for t in (6, 10, 27)], [10, 3, 1])
            self.assertIsNone(values[28])

    def test_relation_equal_different_missing(self):
        candidate = {6: 10, 10: 3, 27: 1, 28: None}
        inputs = [{6: 10, 10: 3, 27: 1},
                  {6: 12, 10: 3, 27: None},
                  {6: None, 10: 2, 27: 2}]
        out = m.summarize(inputs, candidate)
        self.assertEqual(out["source_vs_alternative_numeric_relation_counts"]["CPU_ARCH"],
                         {"NUMERIC_VALUE_DIFFERENT": 1, "NUMERIC_VALUE_EQUAL": 1,
                          "ONE_OR_BOTH_UNDECLARED": 1})
        self.assertEqual(out["source_vs_alternative_numeric_relation_counts"]["ABI_VFP_ARGS"],
                         {"ONE_OR_BOTH_UNDECLARED": 3})

    def test_twelve_aggregate_counts(self):
        candidate = {6: 10, 10: 3, 27: 1}
        out = m.summarize([candidate] * 12, candidate)
        self.assertEqual(out["source_numeric_tag_categories"]["CPU_ARCH"], {"VALUE_10": 12})
        self.assertEqual(out["source_vs_alternative_numeric_relation_counts"]["FP_ARCH"],
                         {"NUMERIC_VALUE_EQUAL": 12})
        self.assertEqual(out["alternative_numeric_tags"]["ABI_VFP_ARGS"], "UNDECLARED")

    def test_no_guest_paths_in_comparison(self):
        out = m.summarize([{6: 10}] * 12, {6: 10})
        self.assertNotIn("/lib/", str(out))
        self.assertNotIn("ld-gamma", str(out))

    def test_full_synthetic_stage(self):
        spec = importlib.util.spec_from_file_location("r3730_fixture", HERE / "support_r3730_fixture.py")
        fix = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fix)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "bin").mkdir()
            (root / "lib").mkdir()
            (root / "usr/lib").mkdir(parents=True)
            raw = attrs([(6, 10), (7, 65), (9, 2), (10, 3), (27, 1), (18, 4), (26, 2)])
            (root / "usr/lib/ld-gamma.so").write_bytes(elf_with_attributes(raw, fix.elf32()))
            (root / "usr/lib/ld-delta.so").write_bytes(fix.elf32(dynamic=False))
            for i in range(19):
                interp = b"/lib/ld-gamma.so\0" if i < 12 else b"/usr/lib/ld-delta.so\0"
                if 2 <= i < 12:
                    interp += b"\0\0"
                content = fix.elf32(interp=interp)
                if i < 12:
                    content = elf_with_attributes(raw, content)
                (root / "bin" / ("src-%03d" % i)).write_bytes(content)
            for i in range(62):
                (root / "bin" / ("other-%03d" % i)).write_bytes(fix.elf32(dynamic=False))
            for i in range(1363):
                (root / ("ordinary-%04d" % i)).write_bytes(b"TEXT")
            for i in range(335):
                (root / ("link-%04d" % i)).symlink_to("ordinary-%04d" % (i % 1363))
            out = m.audit(root, HERE, HERE / PARENT.ORIGINAL_R3731, PARENT)
            self.assertEqual(out["result"], "ARM_NUMERIC_ATTRIBUTES_RELATION_CLASSIFIED_ONLY")
            self.assertEqual(out["source_elf_count"], 12)
            self.assertEqual(out["source_vs_alternative_numeric_relation_counts"]["CPU_ARCH"],
                             {"NUMERIC_VALUE_EQUAL": 12})
            self.assertFalse(out["numeric_tag_equality_implies_runtime_compatibility"])
            self.assertFalse(out["guest_interpreter_path_resolved"])
            self.assertFalse(out["boot_authorized"])
            self.assertNotIn("ld-gamma", str(out))


if __name__ == "__main__":
    unittest.main()
