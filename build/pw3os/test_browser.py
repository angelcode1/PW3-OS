"""NetSurf packaging and offscreen gating regression tests (no Kindle access)."""
from pathlib import Path
import importlib.util
import struct
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("browser_package",HERE/"browser_package.py")
browser=importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)


def index(package="netsurf-framebuffer",version="3.11-r1"):
    return f"P:{package}\nV:{version}\nA:armv7\nD:so:libc.musl-armv7.so.1\n\n"


class TestNetSurf(unittest.TestCase):
    def test_pinned_apk(self):
        with tempfile.TemporaryDirectory() as folder:
            a=Path(folder)/"APKINDEX.main"
            b=Path(folder)/"APKINDEX.community"
            a.write_text("P:musl\nV:1.0\n\n")
            b.write_text(index())
            self.assertEqual(browser.require_netsurf([a,b])["version"],"3.11-r1")
            b.write_text(index(version="3.12-r0"))
            with self.assertRaises(RuntimeError):
                browser.require_netsurf([a,b])
            b.write_text("P:other\nV:1\n\n")
            with self.assertRaises(RuntimeError):
                browser.require_netsurf([a,b])
            a.unlink()
            with self.assertRaises(FileNotFoundError):
                browser.require_netsurf([a,b])

    def test_elf_staging_checks(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            binary=root/browser.NETSURF_EXECUTABLE
            binary.parent.mkdir(parents=True)
            (root/"usr/share/netsurf").mkdir(parents=True)
            hdr=bytearray(52)
            hdr[:6]=b"\x7fELF\x01\x01"
            struct.pack_into("<H",hdr,18,40)
            binary.write_bytes(hdr)
            pkgs=["community/netsurf-framebuffer-3.11-r1"]
            status=browser.verify_browser_staged(root,pkgs)
            self.assertEqual(status["state"],"staged-unverified")
            self.assertFalse(status["runtime_verified"])
            self.assertFalse(status["epdc_verified"])
            self.assertFalse(status["input_verified"])
            with self.assertRaises(RuntimeError):
                browser.verify_browser_staged(root,[])
            hdr[18]=0
            binary.write_bytes(hdr)
            with self.assertRaises(RuntimeError):
                browser.verify_browser_staged(root,pkgs)

    def test_offscreen_launcher_never_uses_linux_fb(self):
        shell=(HERE/"codex-browser.sh").read_text()
        self.assertIn(" -f ram ",shell)
        self.assertIn("--offscreen-test",shell)
        self.assertNotIn("/dev/fb",shell)
        self.assertNotIn("browser-backend-verified",shell)
        self.assertIn("exit 78",shell)

    def test_builder_bundles_netsurf_without_menu_exposure(self):
        code=(HERE/"build_image.py").read_text()
        self.assertIn("NETSURF_PACKAGE",code)
        self.assertIn("verify_browser_staged(root,packages)",code)
        self.assertIn("codex-browser",code)
        self.assertIn("browser-smoke.html",code)
        self.assertNotIn("Browser|",code)
        self.assertIn("'browser':browser",code)

    def test_home_quote_list_unchanged_pending_user_replacements(self):
        from sys import path
        path.insert(0,str(HERE))
        from codex_home import patch_codex_home
        sample='static const char *const footers[] = {"turn the page"};\n'+\
            'for (const char *p = "INKWELL"; *p; p++) {}'
        patched=patch_codex_home(sample)
        self.assertIn('"Codex"',patched)
        self.assertIn('"turn the page"',patched)


if __name__ == "__main__":
    unittest.main()
