"""Source-anchored, fail-closed static Codex front-page redesign.

Only the compiled Home UI is changed. No kernel suspend, device input or EPDC
interfaces are modified; this removes the once-per-minute home refresh.
"""

DATE_HERO = r"""static void draw_date_hero(void) {
    char day_number[8], weekday[64], month_year[64], fitted[96];
    time_t now = time(0);
    struct tm *today = localtime(&now);
    if (!today) return;
    strftime(day_number, sizeof day_number, "%d", today);
    strftime(weekday, sizeof weekday, "%A", today);
    strftime(month_year, sizeof month_year, "%B %Y", today);
    fill(0, CLOCK_Y, W, RULE_Y - CLOCK_Y - 20, WHITE);
    /* Reuse the former clock's large Cormorant serif, now completely static. */
    text(&f_serif_bold, 264, MARGIN - 10, CLOCK_Y + 12, day_number, BLACK);
    text(&f_ui_bold, 25, 416, CLOCK_Y + 47, "TODAY", 0x70);
    text_fit(&f_serif_bold, 96, weekday, W - 416 - MARGIN, fitted, sizeof fitted);
    text(&f_serif_bold, 96, 416, CLOCK_Y + 103, fitted, BLACK);
    text_fit(&f_serif_italic, 54, month_year, W - 416 - MARGIN, fitted, sizeof fitted);
    text(&f_serif_italic, 54, 416, CLOCK_Y + 233, fitted, 0x35);
}

"""

LAYOUT = r"""static void layout(void) {
    int usable = W - 2 * MARGIN;
    const int gap = 22;
    if (napps == 5) {
        /* Two hero reading apps; three supporting applications beneath them. */
        int large_w = (usable - gap) / 2;
        apps[0].r = (rect){MARGIN, GRID_Y, large_w, 292};
        apps[1].r = (rect){MARGIN + large_w + gap, GRID_Y,
                           usable - large_w - gap, 292};
        int row_y = GRID_Y + 292 + 22;
        int small_w = (usable - 2 * gap) / 3;
        for (int i = 2; i < 5; i++) {
            int x = MARGIN + (i - 2) * (small_w + gap);
            int w = (i == 4) ? W - MARGIN - x : small_w;
            apps[i].r = (rect){x, row_y, w, 232};
        }
    } else {
        /* Keep a safe general layout for future Browser / additional apps. */
        int ncol = napps > 9 ? 4 : 3;
        int nrow = (napps + ncol - 1) / ncol;
        if (nrow < 1) nrow = 1;
        int cw = usable / ncol;
        int available = GRID_BOTTOM - GRID_Y - (nrow - 1) * 14;
        int ch = available / nrow;
        if (ch > 250) ch = 250;
        for (int i = 0; i < napps; i++) {
            apps[i].r = (rect){MARGIN + (i % ncol) * cw,
                               GRID_Y + (i / ncol) * (ch + 14), cw, ch};
        }
    }
    slider_x0 = MARGIN + 90;
    slider_x1 = W - MARGIN - 130;
    slider_r = (rect){MARGIN, SLIDER_Y - 20,
                      W - 2 * MARGIN, SLIDER_H + 40};
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


def replace_once(source: str, before: str, after: str) -> str:
    if source.count(before) != 1:
        raise ValueError("Upstream Home anchor changed: " + before[:95])
    return source.replace(before, after, 1)


def replace_section(source: str, start: str, end: str, replacement: str) -> str:
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError("Upstream Home section boundary changed")
    head, remaining = source.split(start, 1)
    old_section, tail = remaining.split(end, 1)
    if not old_section.strip():
        raise ValueError("Upstream Home section unexpectedly empty")
    return head + replacement + end + tail


def patch_codex_frontpage(source: str) -> str:
    source = replace_section(source, "static void layout(void) {",
                             "/* ---- drawing ", LAYOUT)
    source = replace_section(source, "static void draw_clock(void) {",
                             "static int app_at(", DATE_HERO)
    source = replace_once(source, "#define GRID_BOTTOM 1262",
                          "#define GRID_BOTTOM 1095")
    source = replace_once(source, "#define SLIDER_Y 1290",
                          "#define SLIDER_Y 1145")
    source = replace_once(source, "    draw_clock();\n    ornament(RULE_Y);",
                          "    draw_date_hero();\n    ornament(RULE_Y);")
    source = replace_once(source, "    draw_slider();\n    codex_draw_footer();",
                          "    draw_slider();\n    ornament(1255);\n    codex_draw_footer();")
    source = replace_once(source, "    float k = cell_h / (float)CELL_H;",
                          "    float k = a->r.h / (float)CELL_H;\n"
                          "    if (a->r.h >= 280)\n"
                          "        frame(a->r.x + 8, a->r.y + 5,\n"
                          "              a->r.w - 16, a->r.h - 10, 2, 0xC0);")
    source = replace_once(source,
                          "int r = (int)(84 * cell_h / (float)CELL_H);",
                          "int r = (int)(84 * apps[i].r.h / (float)CELL_H);")
    source = replace_once(source, ORIGINAL_IDLE,
                          "        event e = input_wait(-1);\n"
                          "        if (e.type == EV_NONE) continue;")
    source = replace_once(source, 'for (const char *p = "Codex"; *p; p++)',
                          'for (const char *p = "CODEX"; *p; p++)')
    if "draw_clock()" in source or "input_wait((60 - now % 60)" in source:
        raise ValueError("Live clock or periodic repaint remains")
    return source
