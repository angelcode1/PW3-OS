"""Build-time Codex home branding and locally rotating wisdom footer.

All five passages are compiled into the home program: no network or quote API.
The initial asterisks around the first verse were Markdown emphasis, not text.
"""
import re

VERSES = (
    "The fear of the LORD is the beginning of knowledge;",
    "For the LORD gives wisdom; from his mouth come knowledge and understanding.",
    "When pride comes, then comes disgrace, but with humility comes wisdom.",
    "How much better to get wisdom than gold, to get insight rather than silver!",
    "Do not be wise in your own eyes; fear the LORD and shun evil.",
)

FOOTER_DRAW = r"""
typedef struct { int px; int y; } codex_footer_context;

/* Called by eink.h's word-wrap helper; preserve the entire line. */
static void codex_footer_line(const char *part, int len, void *arg) {
    codex_footer_context *ctx = (codex_footer_context *)arg;
    char line[256];
    if (len <= 0 || (size_t)len >= sizeof line) return;
    memcpy(line, part, (size_t)len);
    line[len] = 0;
    text_center(&f_hand, ctx->px, W / 2, ctx->y, line, 0x50);
    ctx->y += ctx->px + 2;
}

static void codex_draw_footer(void) {
    time_t now = time(0);
    struct tm *today = localtime(&now);
    unsigned day_index = today ? (unsigned)today->tm_yday
                               : (unsigned long)(now / 86400);
    const char *verse = footers[day_index %
                                (sizeof footers / sizeof footers[0])];
    const int max_w = W - 2 * MARGIN;
    int px = 38;
    int lines = text_wrap(&f_hand, px, verse, max_w, NULL, NULL);
    while (lines > 2 && px > 24) {
        px -= 2;
        lines = text_wrap(&f_hand, px, verse, max_w, NULL, NULL);
    }
    /* Align the complete verse above a fixed bottom margin, even if it
     * needs three lines at the smallest permitted font size. */
    codex_footer_context context = {
        px, H - 28 - lines * (px + 3)
    };
    text_wrap(&f_hand, px, verse, max_w, codex_footer_line, &context);
}

"""


def patch_codex_home(source: str) -> str:
    source = re.sub(r"(?i)inkwell", "Codex", source)
    table = re.search(
        r"static const char \*const footers\[\] = \{.*?\};",
        source, flags=re.DOTALL,
    )
    if not table:
        raise ValueError("upstream home footer table changed")
    encoded = ",\n".join("    " + '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"' for v in VERSES)
    source = source[:table.start()] + (
        "static const char *const footers[] = {\n" + encoded + "\n};\n\n"
        + FOOTER_DRAW
    ) + source[table.end():]
    original = (
        "    time_t now = time(0);\n"
        "    text_center(&f_hand, 46, W / 2, H - 82, "
        "footers[(now / 86400) % (sizeof footers / sizeof *footers)], 0x50);"
    )
    if source.count(original) != 1:
        raise ValueError("upstream home footer draw call changed")
    source = source.replace(original, "    codex_draw_footer();", 1)
    if 'for (const char *p = "INKWELL"' in source or        "ink on glass, linux underneath" in source:
        raise ValueError("original home branding/footer remains")
    return source
