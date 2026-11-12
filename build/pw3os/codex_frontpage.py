"""Targeted, source-anchored Codex Home change: replace the clock with a
large day/date header, but preserve the original app grid and all other layout.

The e-ink display is redrawn on real user events only, not every minute.
"""

DATE_HEADER = r"""static void draw_date_header(void) {
    char weekday[64], month[64], date_line[100], year[16];
    time_t now = time(0);
    struct tm *today = localtime(&now);
    if (!today) return;
    if (!strftime(weekday, sizeof weekday, "%A", today)) return;
    if (!strftime(month, sizeof month, "%B", today)) return;
    snprintf(date_line, sizeof date_line, "%d %s", today->tm_mday, month);
    snprintf(year, sizeof year, "%04d", today->tm_year + 1900);

    /* Original clock rectangle, app grid, slider and ornament are unchanged. */
    fill(0, CLOCK_Y, W, RULE_Y - 20 - CLOCK_Y, WHITE);
    const int max_w = W - 2 * MARGIN;

    /* Keep the original large time font for the weekday and calendar date. */
    int weekday_px = 142;
    while (weekday_px > 70 &&
           text_width(&f_serif_bold, weekday_px, weekday) > max_w)
        weekday_px -= 4;
    text(&f_serif_bold, weekday_px, MARGIN - 8, CLOCK_Y + 8,
         weekday, BLACK);

    int date_px = 130;
    while (date_px > 68 &&
           text_width(&f_serif_bold, date_px, date_line) > max_w)
        date_px -= 4;
    text(&f_serif_bold, date_px, MARGIN - 8, CLOCK_Y + 151,
         date_line, BLACK);

    /* Smaller italic year closes the original clock's vertical space. */
    text(&f_serif_italic, 58, MARGIN, CLOCK_Y + 283, year, 0x30);
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
        raise ValueError("Upstream Home anchor changed: " + before[:90])
    return source.replace(before, after, 1)


def replace_section(source: str, start: str, end: str, replacement: str) -> str:
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError("Upstream Home date section boundary changed")
    head, remaining = source.split(start, 1)
    previous, tail = remaining.split(end, 1)
    if not previous.strip():
        raise ValueError("Upstream Home date section is empty")
    return head + replacement + end + tail


def patch_codex_frontpage(source: str) -> str:
    # Preserve layout(), draw_app(), slider/drag behaviour, home footer and
    # every coordinate macro exactly as supplied by the pinned upstream.
    source = replace_section(source, "static void draw_clock(void) {",
                             "static int app_at(", DATE_HEADER)
    source = replace_once(source, "    draw_clock();\n    ornament(RULE_Y);",
                          "    draw_date_header();\n    ornament(RULE_Y);")
    source = replace_once(source, ORIGINAL_IDLE,
                          "        event e = input_wait(-1);\n"
                          "        if (e.type == EV_NONE) continue;")
    source = replace_once(source, 'for (const char *p = "Codex"; *p; p++)',
                          'for (const char *p = "CODEX"; *p; p++)')
    if ("draw_clock" in source or "input_wait((60 - now % 60)" in source
            or 'strftime(hm' in source):
        raise ValueError("Live clock or periodic refresh still present")
    return source
