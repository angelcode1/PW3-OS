"""Source-anchored, fail-closed static Codex front-page redesign.

Only the compiled Home UI is changed. No kernel suspend, device input or EPDC
interfaces are modified; this removes the once-per-minute home refresh.
"""

DATE_HERO = r"""static void draw_date_hero(void) {
    char day_number[8], weekday[64], month_year[64], fitted[96];
    time_t now = time(0);
    struct tm *today = localtime(&now);
    if (!today) return;
    snprintf(day_number, sizeof day_number, "%d", today->tm_mday);
    strftime(weekday, sizeof weekday, "%A", today);
    strftime(month_year, sizeof month_year, "%B %Y", today);
    fill(0, CLOCK_Y, W, RULE_Y - CLOCK_Y - 20, WHITE);
    /* Portrait book-cover hierarchy: caption, weekday, giant numeral, month. */
    text_center(&f_ui_bold, 23, W / 2, CLOCK_Y + 6, "TODAY", 0x70);
    text_fit(&f_serif_italic, 62, weekday, W - 2 * MARGIN, fitted, sizeof fitted);
    text_center(&f_serif_italic, 62, W / 2, CLOCK_Y + 46, fitted, 0x35);
    text_center(&f_serif_bold, 205, W / 2, CLOCK_Y + 114, day_number, BLACK);
    text_fit(&f_serif_italic, 50, month_year, W - 2 * MARGIN, fitted, sizeof fitted);
    text_center(&f_serif_italic, 50, W / 2, CLOCK_Y + 283, fitted, 0x35);
}

"""

LAYOUT = r"""static void layout(void) {
    int usable = W - 2 * MARGIN;
    const int gap = 18;
    if (napps == 5) {
        /* The two reading slots are FULL WIDTH and VERTICALLY STACKED. */
        apps[0].r = (rect){MARGIN, GRID_Y, usable, 166};
        apps[1].r = (rect){MARGIN, GRID_Y + 180, usable, 166};
        int row_y = GRID_Y + 360;
        int small_w = (usable - 2 * gap) / 3;
        for (int i = 2; i < 5; i++) {
            int x = MARGIN + (i - 2) * (small_w + gap);
            int w = (i == 4) ? W - MARGIN - x : small_w;
            apps[i].r = (rect){x, row_y, w, 200};
        }
    } else {
        /* Safe compact fallback for 1..16 apps when Browser becomes available. */
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
    source = replace_once(source, """    float k = cell_h / (float)CELL_H;
    cy = a->r.y + (int)(92 * k);
    ring(cx, cy, 78 * k, 3, 0x40);
    icon(a->icon, cx, cy, 128 * k);
    text_center(&f_ui_bold, k < 1 ? 28 : 32, cx, a->r.y + (int)(186 * k) - (k < 1 ? 4 : 0), a->label, BLACK);""",
    """    if (a->r.w > W / 2) {
        /* Portrait full-width app row: icon on left, large text on right. */
        int ix = a->r.x + 116, iy = a->r.y + a->r.h / 2;
        char fitted[96];
        frame(a->r.x + 4, a->r.y + 4,
              a->r.w - 8, a->r.h - 8, 2, 0xB0);
        ring(ix, iy, 55, 2, 0x40);
        icon(a->icon, ix, iy, 92);
        text_fit(&f_serif_bold, 63, a->label,
                 a->r.w - 270, fitted, sizeof fitted);
        text(&f_serif_bold, 63, a->r.x + 232, a->r.y + 43,
             fitted, BLACK);
    } else {
        float k = a->r.h / (float)CELL_H;
        cy = a->r.y + (int)(92 * k);
        ring(cx, cy, 78 * k, 3, 0x40);
        icon(a->icon, cx, cy, 128 * k);
        text_center(&f_ui_bold, k < 1 ? 28 : 32, cx,
                    a->r.y + (int)(186 * k) - (k < 1 ? 4 : 0),
                    a->label, BLACK);
    }""")
    source = replace_once(source,
                          """int r = (int)(84 * cell_h / (float)CELL_H);
                    press_on((rect){cx - r, apps[i].r.y + 6, 2 * r, (int)(172 * cell_h / (float)CELL_H)});""",
                          """if (apps[i].r.w > W / 2) {
                        press_on((rect){apps[i].r.x + 48, apps[i].r.y + 9,
                                        136, apps[i].r.h - 18});
                    } else {
                        int r = (int)(84 * apps[i].r.h / (float)CELL_H);
                        press_on((rect){cx - r, apps[i].r.y + 6,
                                        2 * r, (int)(172 * apps[i].r.h / (float)CELL_H)});
                    }""")
    source = replace_once(source, ORIGINAL_IDLE,
                          "        event e = input_wait(-1);\n"
                          "        if (e.type == EV_NONE) continue;")
    source = replace_once(source, 'for (const char *p = "Codex"; *p; p++)',
                          'for (const char *p = "CODEX"; *p; p++)')
    if "draw_clock()" in source or "input_wait((60 - now % 60)" in source:
        raise ValueError("Live clock or periodic repaint remains")
    return source
