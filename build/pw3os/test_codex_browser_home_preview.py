"""Safety and integration checks for the optional Codex Home Browser Test tile."""
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

class HomeBrowserPreview(unittest.TestCase):
    def test_launcher_does_not_manage_or_stop_home_process(self):
        s=(HERE/"codex-browser-home-preview.sh").read_text()
        self.assertIn('"$PANEL" --home-origin-check',s)
        self.assertIn("CODEX_BROWSER_PANEL_TRIAL=HOME_PREVIEW",s)
        self.assertIn("CODEX_SDL_INPUT_ENABLE=PW3_HOME_PREVIEW",s)
        self.assertIn('trap cleanup EXIT',s)
        self.assertIn("--confirm-home",s)
        self.assertIn('"file://$HTML"',s)
        self.assertIn('browser-interactive.html',s)
        self.assertIn('CODEX_BROWSER_LIVE_TRIAL=EXPLICIT "$FAST"',s)
        self.assertNotIn('python3 "$PY" --follow-seconds 33',s)
        self.assertNotIn("kill -TERM \"$home_pid\"",s)
        self.assertNotIn("kill -STOP \"$home_pid\"",s)
        self.assertNotIn("kill -CONT \"$home_pid\"",s)
        self.assertNotIn(" /dev/tty ",s)
        self.assertNotIn("https://",s)
        self.assertNotIn("alpine-os.img",s)
        self.assertIn('FAST_ONCE="$R/.fast-refresh-once"',s)
        self.assertIn('rm -f "$FAST_ONCE"',s)
        self.assertIn('--fast-follow-seconds 33',s)
        self.assertIn('CODEX_BROWSER_PANEL_TRIAL=HOME_FAST_PREVIEW',s)
        self.assertIn('--confirm-home-fast',s)
        self.assertIn('home-panel.log',s)
        self.assertIn('if [ "$mode" = fast ]; then',s)

    def test_interactive_fixture_has_link_and_visible_scroll_targets(self):
        s=(HERE/"browser-interactive.html").read_text()
        self.assertIn('href="#finish"',s)
        self.assertIn('id="finish"',s)
        self.assertIn('href="#top"',s)
        self.assertIn("PAGE FOUR",s)
        for i in ("ONE","TWO","THREE"):
            self.assertIn("PAGE "+i,s)
        self.assertIn('min-height:420px',s)

    def test_explicit_only_not_added_to_default_menu(self):
        s=(HERE/"build_image.py").read_text()
        self.assertIn("browser['home_preview_enabled_by_default']=False",s)
        self.assertIn("codex-browser-home-preview.sh",s)
        self.assertIn("browser-interactive.html",s)
        self.assertIn("codex-browser-fast-frames",s)
        self.assertNotIn("Browser Test|globe|",s)
        self.assertIn("out/'codex-browser-home-preview'",s)
        self.assertIn("out/'browser-interactive.html'",s)
        self.assertIn("codex-browser-panel-fast.c",s)
        self.assertIn("out/'codex-browser-panel-fast'",s)

    def test_panel_gates_home_and_ssh_separately(self):
        s=(HERE/"codex-browser-panel-preview.c").read_text()
        self.assertIn('strcmp(argv[1], "--home-origin-check")',s)
        self.assertIn('strcmp(argv[3], "--confirm-home")',s)
        self.assertIn('strcmp(gate, "HOME_PREVIEW")',s)
        self.assertIn('codex_browser_from_home()',s)
        self.assertIn('strcmp(gate, "EXPLICIT")',s)

    def test_fast_presenter_is_independent_and_hardware_gated(self):
        s=(HERE/"codex-browser-panel-fast.c").read_text()
        self.assertIn('strcmp(argv[3],"--confirm-home-fast")',s)
        self.assertIn('"HOME_FAST_PREVIEW"',s)
        self.assertIn('codex_browser_from_home()',s)
        self.assertIn('UPDATE_PARTIAL 0u',s)
        self.assertIn('WF_DU 1u',s)
        self.assertIn('WF_GC16 2u',s)
        self.assertIn('CODEX_BROWSER_FAST_SCREEN_RESTORED',s)
        self.assertIn('should_full_refresh(have_frame,partial_burst,changed)',s)
        self.assertIn('#define FULL_AREA_PERCENT 45u',s)
        self.assertIn('WF_GC16,',s)
        self.assertNotIn('do_full?WF_GC16:WF_DU',s)
        self.assertNotIn('WF_DU,UPDATE_PARTIAL',s)
        self.assertNotIn('alpine-os.img',s)
        self.assertNotIn('kill -TERM',s)
        self.assertNotIn('BOOT_ALPINE_ONCE',s)

    def test_touch_hook_validates_home_parent(self):
        s=(HERE/"codex-sdl-touch-input.c").read_text()
        self.assertIn('strcmp(g,"PW3_HOME_PREVIEW")',s)
        self.assertIn('ancestry=codex_browser_from_home()',s)
        self.assertIn('strcmp(g,"PW3_ATTENDED")',s)

if __name__=="__main__":
    unittest.main()
