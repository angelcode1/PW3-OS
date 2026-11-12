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

    def test_runtime_dependency_closure_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            a=Path(folder)/"APKINDEX.main"
            b=Path(folder)/"APKINDEX.community"
            a.write_text("P:musl\nV:1.2\np:so:libc.musl-armv7.so.1\n\n")
            b.write_text(index())
            result=browser.verify_netsurf_closure(
                [a,b], ["community/netsurf-framebuffer-3.11-r1"])
            self.assertIn("musl",result)
            self.assertIn("netsurf-framebuffer",result)
            b.write_text(index().replace(
                "so:libc.musl-armv7.so.1", "so:libmissing.so.9"))
            with self.assertRaises(RuntimeError):
                browser.verify_netsurf_closure(
                    [a,b],["community/netsurf-framebuffer-3.11-r1"])
            with self.assertRaises(RuntimeError):
                browser.verify_netsurf_closure([a,b],[])

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
        self.assertIn("--capture-offscreen",shell)
        self.assertIn('CODEX_BROWSER_ATTENDED',shell)
        self.assertIn('SDL_VIDEODRIVER=dummy',shell)
        self.assertIn('CODEX_SDL_CAPTURE_ENABLE=PW3_ATTENDED',shell)
        self.assertNotIn("/dev/fb",shell)
        self.assertNotIn("browser-backend-verified",shell)
        self.assertIn("exit 78",shell)

    def test_pw3_browser_preview_and_touch_probe_are_explicitly_gated(self):
        panel=(HERE/"codex-browser-panel-preview.c").read_text()
        touch=(HERE/"codex-browser-touch-probe.c").read_text()
        builder=(HERE/"build_image.py").read_text()
        self.assertIn("CODEX_BROWSER_PANEL_TRIAL",panel)
        self.assertIn('isatty(STDIN_FILENO)',panel)
        self.assertIn("CODEX_PW3_BROWSER_SCREEN_RESTORED",panel)
        self.assertIn("MXCFB_SEND_UPDATE_PW3 0x4048462eu",panel)
        self.assertIn("_Static_assert(sizeof(struct pw3_update) == 72",panel)
        self.assertIn("CODEX_BROWSER_TOUCH_TRIAL",touch)
        self.assertIn('O_RDONLY|O_CLOEXEC|O_NONBLOCK|O_NOFOLLOW',touch)
        self.assertNotIn("EVIOCGRAB",touch.split("#define PANEL_W")[1])
        self.assertIn("ABS_MT_TRACKING_ID",touch)
        self.assertIn("codex_touch_translate",touch)
        self.assertIn("codex-browser-touch-probe",builder)
        self.assertIn("codex-browser-panel-preview",builder)

    def test_isolated_armv7_trial_does_not_open_display(self):
        trial=(HERE/"codex-browser-trial.sh").read_text()
        self.assertIn("--offscreen-test",trial)
        self.assertIn(" -f ram ",trial)
        self.assertIn("LD_LIBRARY_PATH",trial)
        self.assertNotIn("/dev/fb",trial)
        self.assertNotIn("ioctl",trial)
        self.assertIn("exit 78",trial)
        builder=(HERE/"build_image.py").read_text()
        self.assertIn("package_netsurf_trial(",builder)
        self.assertIn("codex-netsurf-test-bundle.tar.gz",builder)
        self.assertIn("README-NETSURF-TRIAL.txt",builder)

    def test_headless_bridge_is_staged_without_boot_hooks(self):
        src=(HERE/"codex-sdl-live-capture.c").read_text()
        builder=(HERE/"build_image.py").read_text()
        launcher=(HERE/"codex-browser.sh").read_text()
        self.assertIn('OUTPUT_PW3 "/run/codex-browser/codex-live-sdl.bmp"',src)
        self.assertIn('ENABLE_PW3 "PW3_ATTENDED"',src)
        self.assertIn('void SDL_UpdateRect',src)
        self.assertNotIn('"/dev/fb0"',src)
        self.assertNotIn("MXCFB_SEND_UPDATE",src)
        self.assertIn('crosscompile_browser_shared(',builder)
        self.assertIn("libcodex-sdl-capture.so",builder)
        self.assertIn("verify_direct_sdl.py",builder)
        self.assertIn('CODEX_BROWSER_ATTENDED',launcher)
        self.assertIn('SDL_VIDEODRIVER=dummy',launcher)
        self.assertNotIn('LD_PRELOAD=',launcher.split('--offscreen-test)')[1].split('--capture-offscreen)')[0])

    def test_sdl_visual_ci_uses_isolated_xvfb(self):
        script=(HERE/"codex-browser-visual-ci.sh").read_text()
        fixture=(HERE/"browser-smoke.html").read_text()
        verifier=(HERE/"verify_browser_capture.py").read_text()
        self.assertIn("Xvfb :117",script)
        self.assertIn(" -f sdl ",script)
        self.assertIn("CODEX_BROWSER_VISUAL_CI",script)
        self.assertIn("-nolisten tcp",script)
        self.assertIn('chown -R "$CODEX_CI_HOST_UID:$CODEX_CI_HOST_GID"',script)
        self.assertIn("trap cleanup EXIT INT TERM",script)
        workflow=(HERE.parent.parent/".github/workflows/codex-netsurf-offscreen.yml").read_text()
        self.assertIn('CODEX_CI_HOST_UID="$(id -u)"',workflow)
        self.assertIn('CODEX_CI_HOST_GID="$(id -g)"',workflow)
        self.assertNotIn("/dev/fb",script)
        self.assertIn("#cc2a77",fixture)
        self.assertIn("proof_magenta",verifier)
        self.assertIn("2000",verifier)

    def test_builder_bundles_netsurf_without_menu_exposure(self):
        code=(HERE/"build_image.py").read_text()
        self.assertIn("NETSURF_PACKAGE",code)
        self.assertIn("verify_browser_staged(root,packages)",code)
        self.assertIn("codex-browser",code)
        self.assertIn("browser-smoke.html",code)
        self.assertNotIn("Browser|",code)
        self.assertIn("'browser':browser",code)

    def test_home_footer_is_local_and_contains_five_passages(self):
        from sys import path
        path.insert(0,str(HERE))
        from codex_home import patch_codex_home, VERSES
        sample = ('static const char *const footers[] = {\n'
                  '    "turn the page",\n'
                  '    "ink on glass, linux underneath"\n'
                  '};\n'
                  'static void draw_home(int flash) {\n'
                  '    time_t now = time(0);\n'
                  '    text_center(&f_hand, 46, W / 2, H - 82, '
                  'footers[(now / 86400) % (sizeof footers / sizeof *footers)], 0x50);\n'
                  '}\n'
                  'for (const char *p = "INKWELL"; *p; p++) {}')
        patched = patch_codex_home(sample)
        self.assertEqual(len(VERSES),5)
        self.assertIn('"Codex"',patched)
        for passage in VERSES:
            self.assertEqual(patched.count('"' + passage + '"'),1)
        self.assertNotIn('"turn the page"',patched)
        self.assertNotIn('ink on glass, linux underneath',patched)
        self.assertIn('codex_draw_footer();',patched)
        self.assertIn('text_wrap(&f_hand',patched)
        self.assertIn('sizeof footers / sizeof footers[0]',patched)
        self.assertNotIn('fopen(',patched)
        with self.assertRaises(ValueError):
            patch_codex_home('upstream footer removed')


if __name__ == "__main__":
    unittest.main()
