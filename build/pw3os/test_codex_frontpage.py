"""Codex Home layout regression tests; intentionally require no Kindle device."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_frontpage import patch_codex_frontpage

FIXTURE = r'''#define GRID_BOTTOM 1262
#define SLIDER_Y 1290
static void layout(void) {
    int ncol = napps > 9 ? 4 : 3;
}
/* ---- drawing ------------------------------------------------------------- */
static void draw_clock(void) {
    char hm[16];
    time_t now = time(0);
    strftime(hm, sizeof hm, "%H:%M", localtime(&now));
}
static int app_at(int x, int y) { return -1; }
static void draw_app(const app *a) {
    float k = cell_h / (float)CELL_H;
}
static void draw_home(int flash) {
    draw_clock();
    ornament(RULE_Y);
    draw_slider();
    codex_draw_footer();
}
static void test_control(void) {
    int r = (int)(84 * cell_h / (float)CELL_H);
}
static void event_loop(void) {
        time_t now = time(0);
        event e = input_wait((60 - now % 60) * 1000);
        now = time(0);
        if (e.type == EV_NONE) {
            draw_status();
            draw_clock();
            refresh(0, 0, W, RULE_Y - 20, WF_GL16, 0, 0);
            continue;
        }
}
for (const char *p = "Codex"; *p; p++) {}
'''


class TestCodexFrontpage(unittest.TestCase):
    def test_static_date_and_no_periodic_refresh(self):
        s = patch_codex_frontpage(FIXTURE)
        self.assertIn('snprintf(day_number, sizeof day_number, "%d", today->tm_mday)', s)
        self.assertIn('strftime(weekday, sizeof weekday, "%A"', s)
        self.assertIn('strftime(month_year, sizeof month_year, "%B %Y"', s)
        self.assertIn('text(&f_serif_bold, 264', s)
        self.assertNotIn('strftime(hm', s)
        self.assertNotIn('draw_clock', s)
        self.assertIn('input_wait(-1)', s)
        self.assertNotIn('60 - now % 60', s)
        self.assertNotIn('refresh(0, 0, W, RULE_Y - 20', s)

    def test_reading_apps_are_large_and_utility_row_is_compact(self):
        s = patch_codex_frontpage(FIXTURE)
        self.assertIn('if (napps == 5)', s)
        self.assertIn('apps[0].r =', s)
        self.assertIn('apps[1].r =', s)
        self.assertIn('for (int i = 2; i < 5; i++)', s)
        self.assertIn('292', s)
        self.assertIn('232', s)
        self.assertIn('int ncol = napps > 9 ? 4 : 3;', s)
        self.assertIn('a->r.h / (float)CELL_H', s)
        self.assertIn('apps[i].r.h / (float)CELL_H', s)
        self.assertIn('SLIDER_Y 1145', s)
        self.assertIn('ornament(1255)', s)
        self.assertIn('for (const char *p = "CODEX"', s)

    def test_changes_fail_closed_if_upstream_changes(self):
        with self.assertRaises(ValueError):
            patch_codex_frontpage(FIXTURE.replace(
                'input_wait((60 - now % 60) * 1000)',
                'input_wait(120000)'))
        with self.assertRaises(ValueError):
            patch_codex_frontpage(FIXTURE.replace(
                'static void draw_clock(void)', 'static void draw_time(void)'))


if __name__ == "__main__":
    unittest.main()
