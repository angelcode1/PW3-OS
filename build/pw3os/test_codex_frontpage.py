"""Regress a minimally changed *original* Codex app grid.

The only supported UI change is removing the live clock and enlarging day/date.
"""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from codex_frontpage import patch_codex_frontpage

# Exact original upstream sections. Source transformation must leave these
# unchanged, including geometry, touch/drag scaling, slider and footer.
ORIGINAL_LAYOUT = """static void layout(void) {
    /* Three columns hold nine apps. More than that goes to four columns,
     * which keeps the rows the same height. */
    int ncol = napps > 9 ? 4 : 3, cw = (W - 2 * MARGIN) / ncol;
    /* A fourth row makes the cells shorter, and draw_app scales to them. */
    int nrow = (napps + ncol - 1) / ncol;
    cell_h = nrow * CELL_H > GRID_BOTTOM - GRID_Y ? (GRID_BOTTOM - GRID_Y) / nrow : CELL_H;
    for (int i = 0; i < napps; i++) apps[i].r = (rect){MARGIN + (i % ncol) * cw, GRID_Y + (i / ncol) * cell_h, cw, cell_h};
    slider_x0 = MARGIN + 90;
    slider_x1 = W - MARGIN - 130;
    slider_r = (rect){MARGIN, SLIDER_Y - 20, W - 2 * MARGIN, SLIDER_H + 40};
}
"""

ORIGINAL_APP = """static void draw_app(const app *a) {
    int cx = a->r.x + a->r.w / 2, cy = a->r.y + 92;
    fill(a->r.x, a->r.y, a->r.w, a->r.h, WHITE);
    float k = cell_h / (float)CELL_H;
    cy = a->r.y + (int)(92 * k);
    ring(cx, cy, 78 * k, 3, 0x40);
    icon(a->icon, cx, cy, 128 * k);
    text_center(&f_ui_bold, k < 1 ? 28 : 32, cx, a->r.y + (int)(186 * k) - (k < 1 ? 4 : 0), a->label, BLACK);
}
"""

ORIGINAL_IDLE = """        time_t now = time(0);
        event e = input_wait((60 - now % 60) * 1000);
        now = time(0);
        if (e.type == EV_NONE) {
            draw_status();
            draw_clock();
            refresh(0, 0, W, RULE_Y - 20, WF_GL16, 0, 0);
            continue;
        }"""

ORIGINAL_PRESS = """int r = (int)(84 * cell_h / (float)CELL_H);
                    press_on((rect){cx - r, apps[i].r.y + 6, 2 * r, (int)(172 * cell_h / (float)CELL_H)});"""

FIXTURE = """#define GRID_BOTTOM 1262
#define SLIDER_Y 1290
#define CLOCK_Y 70
#define RULE_Y 440
#define GRID_Y 490
""" + ORIGINAL_LAYOUT + """
/* ---- drawing ------------------------------------------------------------- */
static void draw_clock(void) {
    char hm[16], date[64];
    time_t now = time(0);
    struct tm *tm = localtime(&now);
    strftime(hm, sizeof hm, "%H:%M", tm);
    strftime(date, sizeof date, "%A, %-d %B", tm);
}
static int app_at(int x, int y) { return -1; }
""" + ORIGINAL_APP + """
static void draw_home(int flash) {
    draw_clock();
    ornament(RULE_Y);
    for (int i = 0; i < napps; i++) draw_app(&apps[i]);
    draw_slider();
    codex_draw_footer();
}
static void click_handler(void) {
    """ + ORIGINAL_PRESS + """
}
static void event_loop(void) {
""" + ORIGINAL_IDLE + """
}
for (const char *p = "Codex"; *p; p++) {}
"""


class TestCodexFrontpage(unittest.TestCase):
    def test_date_fills_existing_clock_region_without_time(self):
        s = patch_codex_frontpage(FIXTURE)
        self.assertIn('strftime(weekday, sizeof weekday, "%A"', s)
        self.assertIn('strftime(month, sizeof month, "%B"', s)
        self.assertIn('snprintf(date_line, sizeof date_line, "%d %s"', s)
        self.assertIn('text(&f_serif_bold, weekday_px, MARGIN - 8, CLOCK_Y + 4', s)
        self.assertIn('text(&f_serif_italic, date_px, MARGIN - 8, CLOCK_Y + 186', s)
        self.assertIn('text(&f_serif_italic, 48, MARGIN, CLOCK_Y + 301', s)
        self.assertIn("text_width(&f_serif_bold", s)
        self.assertIn("text_width(&f_serif_italic", s)
        self.assertIn("int weekday_px = 178;", s)
        self.assertIn("int date_px = 118;", s)
        self.assertNotIn("int weekday_px = 142;", s)
        self.assertNotIn('strftime(hm', s)
        self.assertNotIn('"%H:%M"', s)
        self.assertNotIn("draw_clock", s)
        self.assertIn("draw_date_header();", s)

    def test_original_grid_slider_and_press_are_unchanged(self):
        s = patch_codex_frontpage(FIXTURE)
        self.assertIn(ORIGINAL_LAYOUT, s)
        self.assertIn(ORIGINAL_APP, s)
        self.assertIn(ORIGINAL_PRESS, s)
        self.assertIn("#define GRID_BOTTOM 1262", s)
        self.assertIn("#define SLIDER_Y 1290", s)
        self.assertIn("ornament(RULE_Y)", s)
        self.assertIn("draw_slider();\n    codex_draw_footer();", s)
        self.assertNotIn("napps == 5", s)
        self.assertNotIn("apps[0].r =", s)
        self.assertNotIn("apps[1].r =", s)

    def test_no_minute_refresh_but_wake_and_app_redraw_intact(self):
        s = patch_codex_frontpage(FIXTURE)
        self.assertIn("input_wait(-1)", s)
        self.assertNotIn("input_wait((60 - now % 60)", s)
        self.assertNotIn("refresh(0, 0, W, RULE_Y - 20", s)
        self.assertIn("draw_home(int flash)", s)
        self.assertIn('for (const char *p = "CODEX"', s)

    def test_source_anchor_changes_fail_closed(self):
        with self.assertRaises(ValueError):
            patch_codex_frontpage(FIXTURE.replace("draw_clock(void)", "draw_time(void)"))
        with self.assertRaises(ValueError):
            patch_codex_frontpage(FIXTURE.replace(
                "input_wait((60 - now % 60) * 1000)", "input_wait(120000)"))


if __name__ == "__main__":
    unittest.main()
