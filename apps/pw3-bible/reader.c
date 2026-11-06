#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef PW3_HOST
#define FONT_DIR "./fonts/"
#include "vendor/eink.h"
#endif

typedef struct { int page, verse; } Location;
typedef struct { char kind; Location to; char *text; } Row;
typedef struct { Location place; int line; } Visit;

static FILE *archive;
static uint32_t total, day_start, *offsets;
static char *storage;
static Row *rows;
static size_t row_count;
static Visit current, history[64];
static size_t depth;
static const char *preview_date;
static int chapter_book, chapter_num;
#ifndef PW3_HOST
static void audio_on_page(void);
#endif

static int read_u32(uint32_t *value) {
    unsigned char bytes[4];
    if (fread(bytes, 1, 4, archive) != 4) return 0;
    *value = (uint32_t)bytes[0] | (uint32_t)bytes[1] << 8 |
             (uint32_t)bytes[2] << 16 | (uint32_t)bytes[3] << 24;
    return 1;
}

static int open_archive(const char *path) {
    char magic[8];
    archive = fopen(path, "rb");
    if (!archive || fread(magic, 1, 8, archive) != 8 ||
        memcmp(magic, "PW3BIB1", 8) != 0 ||
        !read_u32(&total) || !read_u32(&day_start) ||
        total > 100000 || day_start < 1 || day_start + 1460u > total) return 0;
    offsets = calloc(total + 1, sizeof *offsets);
    if (!offsets || !read_u32(&offsets[0]) || offsets[0] != 16 + 4 * (total + 1)) return 0;
    for (uint32_t n = 1; n <= total; n++) {
        if (!read_u32(&offsets[n]) || offsets[n] <= offsets[n - 1] ||
            offsets[n] - offsets[n - 1] > 1024 * 1024) return 0;
    }
    if (fseek(archive, 0, SEEK_END) != 0) return 0;
    return ftell(archive) == (long)offsets[total];
}

static Location resolve(Location place) {
    if (place.page != -1) return place;
    static const int prefix[] = {0,31,59,90,120,151,181,212,243,273,304,334,365};
    time_t now = time(NULL);
    struct tm *local = localtime(&now);
    int month = local ? local->tm_mon + 1 : 1;
    int day = local ? local->tm_mday : 1;
    if (preview_date) {
        int m, d;
        char tail;
        if (sscanf(preview_date, "%d-%d%c", &m, &d, &tail) == 2 &&
            m >= 1 && m <= 12 && d >= 1 && d <= prefix[m] - prefix[m - 1] + (m == 2)) {
            month = m;
            day = d;
        }
    }
    if (month == 2 && day == 29) day = 28;
    return (Location){(int)day_start + 4 * (prefix[month - 1] + day - 1) + place.verse, 0};
}

static char *field(char **line) {
    char *start = *line;
    if (start) {
        *line = strchr(start, '\t');
        if (*line) *(*line)++ = 0;
    }
    return start;
}

static int number(const char *str, int low, int high, int *out) {
    if (!str || !*str) return 0;
    char *end;
    long val = strtol(str, &end, 10);
    if (*end || val < low || val > high) return 0;
    *out = (int)val;
    return 1;
}

static int load(Location place) {
    place = resolve(place);
    if (place.page < 0 || (uint32_t)place.page >= total) return 0;
    size_t length = offsets[place.page + 1] - offsets[place.page];
    char *buf = malloc(length + 1);
    if (!buf) return 0;
    Row *parsed = NULL;
    int metadata_book = 0, metadata_chapter = 0;
    if (fseek(archive, (long)offsets[place.page], SEEK_SET) ||
        fread(buf, 1, length, archive) != length || buf[length - 1] != '\n') goto fail;
    buf[length] = 0;
    if (memchr(buf, 0, length)) goto fail;
    size_t count = 0, i = 0;
    for (char *p = buf; *p; p++) count += *p == '\n';
    parsed = calloc(count, sizeof *parsed);
    if (!parsed) goto fail;
    for (char *next = buf; i < count; i++) {
        char *line = next;
        next = strchr(line, '\n');
        if (!next) goto fail;
        *next++ = 0;
        char *tag = field(&line);
        if (!tag || !*tag || tag[1] || !line || (i == 0) != (*tag == 'T')) goto fail;
        Row *row = &parsed[i];
        row->kind = *tag;
        switch (*tag) {
            case 'B': case 'G':
                if (!number(field(&line), -1, (int)total - 1, &row->to.page) ||
                    !number(field(&line), 0, 999, &row->to.verse) ||
                    (row->to.page == -1 && (row->to.verse < 1 || row->to.verse > 3))) goto fail;
                break;
            case 'V':
                if (!number(field(&line), 1, 999, &row->to.verse)) goto fail;
                break;
            case 'A':
                if (metadata_book || !number(field(&line), 1, 73, &metadata_book) ||
                    !number(field(&line), 1, 150, &metadata_chapter) || line) goto fail;
                row->text = "";
                continue;
            case 'P': case 'T':
                break;
            default:
                goto fail;
        }
        if (!line) goto fail;
        row->text = line;
    }
    free(storage);
    free(rows);
    storage = buf;
    rows = parsed;
    row_count = count;
    chapter_book = metadata_book;
    chapter_num = metadata_chapter;
    return 1;
fail:
    free(buf);
    free(parsed);
    return 0;
}

static int jump(Location place, int remember) {
    place = resolve(place);
    if (!load(place)) return 0;
    if (remember) {
        if (depth == sizeof history / sizeof history[0]) {
            memmove(history, history + 1, (depth - 1) * sizeof *history);
            depth--;
        }
        history[depth++] = current;
    }
    current = (Visit){place, 0};
#ifndef PW3_HOST
    audio_on_page();
#endif
    return 1;
}

static void back(void) {
    if (depth) {
        Visit previous = history[depth - 1];
        if (load(previous.place)) {
            current = previous;
            depth--;
#ifndef PW3_HOST
            audio_on_page();
#endif
        }
    }
}

static int verify(void) {
    for (uint32_t page = 0; page < total; page++) {
        if (!load((Location){(int)page, 0})) {
            fprintf(stderr, "Invalid page %u\n", page);
            return 1;
        }
    }
    printf("Validated %u pages and link fields\n", total);
    return 0;
}

#ifdef PW3_HOST
static int terminal(void) {
    char input[80];
    for (;;) {
        printf("\n%s\n\n", rows[0].text);
        int item = 0, active = current.place.verse == 0;
        for (size_t i = 1; i < row_count; i++) {
            Row row = rows[i];
            if (row.kind == 'B' || row.kind == 'G') printf("%2d. %s\n", ++item, row.text);
            else if (row.kind == 'V') {
                if (row.to.verse == current.place.verse) active = 1;
                if (active) printf("%d  %s\n", row.to.verse, row.text);
            } else puts(row.text);
        }
        printf("\nNumber, b for back, h for home, q to quit > ");
        fflush(stdout);
        if (!fgets(input, sizeof input, stdin) || input[0] == 'q') return 0;
        if (input[0] == 'b') back();
        else if (input[0] == 'h') { jump((Location){0, 0}, 0); depth = 0; }
        else {
            input[strcspn(input, "\n")] = 0;
            int wanted;
            if (!number(input, 1, item, &wanted)) continue;
            for (size_t i = 1; i < row_count; i++) {
                if ((rows[i].kind == 'B' || rows[i].kind == 'G') && --wanted == 0) {
                    jump(rows[i].to, 1);
                    break;
                }
            }
        }
    }
}
#else
typedef struct { char *label; int col, span, height; Location to; } Line;
typedef struct { int x, y, width, height; Location to; } Hit;
static Line *lines;
static size_t line_count, capacity;
static Hit hits[128];
static size_t hit_count;
static int margin, grid_cols, px, page_end, passage;
#include "audio_ui.h"

static int add_line(const char *s, size_t size, int col, int span, int height, Location to) {
    if (line_count == capacity) {
        size_t next = capacity ? 2 * capacity : 256;
        Line *grown = realloc(lines, next * sizeof *lines);
        if (!grown) return 0;
        lines = grown;
        capacity = next;
    }
    char *label = malloc(size + 1);
    if (!label) return 0;
    memcpy(label, s, size);
    label[size] = 0;
    lines[line_count++] = (Line){label, col, span, height, to};
    return 1;
}

static void add_text_line(const char *text_line, int n, void *ctx) {
    int *ok = ctx;
    if (*ok) *ok = add_line(text_line, (size_t)n, 0, grid_cols, px + 11, (Location){-2, 0});
}

static int make_lines(int seek_verse) {
    for (size_t i = 0; i < line_count; i++) free(lines[i].label);
    line_count = 0;
    int col = 0;
    int ok = 1;
    int anchor = 0;
    passage = 0;
    margin = W / 24;
    px = W / 30;
    grid_cols = 5;
    for (size_t i = 1; i < row_count; i++) {
        Row row = rows[i];
        if (row.kind == 'A') continue;
        if (row.kind == 'G') {
            ok = add_line(row.text, strlen(row.text), col, 1, px * 2, row.to);
            col = (col + 1) % grid_cols;
        } else {
            col = 0;
            if (row.kind == 'B') {
                ok = add_line(row.text, strlen(row.text), 0, grid_cols, px * 2, row.to);
            } else {
                if (row.kind == 'V') {
                    passage = 1;
                    if (row.to.verse == current.place.verse) anchor = (int)line_count;
                    size_t length = strlen(row.text) + 12;
                    char *numbered = malloc(length);
                    if (!numbered) return 0;
                    snprintf(numbered, length, "%d  %s", row.to.verse, row.text);
                    text_wrap(&f_ui, px, numbered, W - 2 * margin - 8, add_text_line, &ok);
                    free(numbered);
                } else {
                    text_wrap(&f_ui, px, row.text, W - 2 * margin - 8, add_text_line, &ok);
                }
                if (ok) ok = add_line("", 0, 0, grid_cols, px / 3, (Location){-2, 0});
            }
        }
        if (!ok) return 0;
    }
    if (seek_verse) current.line = anchor;
    if (current.line < 0 || (size_t)current.line >= line_count) current.line = 0;
    return 1;
}

static int next_row(int first) {
    int next = first + 1;
    while ((size_t)next < line_count && lines[next].col) next++;
    return next;
}

static void draw(void) {
    int box = px * 2, top = box * 2 + margin / 2 +
        (audio_visible && chapter_book ? 3 * px : 0), bottom = H - box - 8;
    fill(0, 0, W, H, WHITE);
    char heading[220];
    text_fit(&f_ui, px + 3, rows[0].text, W - 2 * margin - (passage ? px * 4 : 0), heading, sizeof heading);
    text(&f_ui, px + 3, margin, margin / 3, heading, BLACK);
    if (passage) text_right(&f_ui, px - 2, W - margin, margin / 3, "Go to", BLACK);
    text(&f_ui, px - 2, margin, box, "Home", BLACK);
    text_center(&f_ui, px - 2, W / 2, box, "Back", BLACK);
    text_right(&f_ui, px - 2, W - margin, box, "Exit", BLACK);
    fill(margin, top - 5, W - 2 * margin, 2, BLACK);
    hit_count = 0;
    int unit = (W - 2 * margin) / grid_cols;
    int y = top;
    int first = current.line;
    while ((size_t)first < line_count && y + lines[first].height <= bottom) {
        int end = next_row(first);
        for (int n = first; n < end; n++) {
            const Line *line = &lines[n];
            int x = margin + line->col * unit, width = unit * line->span;
            if (line->to.page != -2) {
                char clipped[256];
                frame(x + 2, y + 3, width - 5, line->height - 6, 2, BLACK);
                text_fit(&f_ui, px - 2, line->label, width - 20, clipped, sizeof clipped);
                if (line->span == 1) text_center(&f_ui, px - 2, x + width / 2, y + px / 2, clipped, BLACK);
                else text(&f_ui, px - 2, x + 10, y + px / 2, clipped, BLACK);
                if (hit_count < sizeof hits / sizeof hits[0]) {
                    hits[hit_count++] = (Hit){x, y, width, line->height, line->to};
                }
            } else {
                text(&f_ui, px, x, y, line->label, BLACK);
            }
        }
        y += lines[first].height;
        first = end;
    }
    page_end = first;
    fill(margin, bottom, W - 2 * margin, 2, BLACK);
    if (current.line) text(&f_ui, px - 2, margin, bottom + px / 3, "< Previous", BLACK);
    if ((size_t)page_end < line_count)
        text_right(&f_ui, px - 2, W - margin, bottom + px / 3, "Next >", BLACK);
    audio_draw_controls(top, margin, px);
}

static void turn(int step) {
    if (step > 0 && (size_t)page_end < line_count && page_end > current.line) current.line = page_end;
    if (step >= 0 || !current.line) return;
    int room = H - 6 * px - margin / 2 - 8;
    int first = current.line;
    do {
        int prior = first - 1;
        while (prior > 0 && lines[prior].col) prior--;
        if (room < lines[prior].height) break;
        room -= lines[prior].height;
        first = prior;
    } while (first);
    current.line = first;
}

static int kindle(void) {
    if (fb_open() || fonts_load()) {
        fputs("PW3 framebuffer or Inkwell font unavailable\n", stderr);
        return 1;
    }
    input_open();
    if (touchfd < 0) {
        fputs("PW3 touch input unavailable\n", stderr);
        return 1;
    }
    audio_visible = audio_run("ready", 0, 0, 0);
    if (!make_lines(1)) return 1;
    draw();
    refresh_all();
    for (;;) {
        event e = input_wait(-1);
        if (e.type == EV_POWER) break;
        if (e.type != EV_TAP) continue;
        if (audio_handle_tap(e.ux, e.uy)) {
            /* Native audio selector or Play/Pause was handled. */
        } else if (abs(e.ux - e.x) > W / 7) {
            turn(e.ux < e.x ? 1 : -1);
        } else if (e.uy >= H - px * 2 - 8) {
            turn(e.ux < W / 2 ? -1 : 1);
        } else if (passage && e.uy < px * 2) {
            if (jump(rows[1].to, 1) && !make_lines(1)) return 1;
        } else if (e.uy < 4 * px + margin / 2) {
            if (e.ux >= 2 * W / 3) break;
            if (e.ux < W / 3) {
                if (jump((Location){0, 0}, 0)) depth = 0;
            } else back();
            if (!make_lines(0)) return 1;
        } else {
            for (size_t i = 0; i < hit_count; i++) {
                Hit h = hits[i];
                if (e.ux >= h.x && e.ux < h.x + h.width && e.uy >= h.y && e.uy < h.y + h.height) {
                    if (jump(h.to, 1) && !make_lines(1)) return 1;
                    break;
                }
            }
        }
        draw();
        flip();
    }
    audio_stop();
    return 0;
}
#endif

int main(int argc, char **argv) {
    if (argc < 2 || argc > 4) {
        fprintf(stderr, "Usage: %s archive.pw3 [--verify | --date MM-DD]\n", argv[0]);
        return 2;
    }
    if (!open_archive(argv[1])) {
        fprintf(stderr, "Cannot open PW3 Bible archive: %s\n", argv[1]);
        return 1;
    }
    if (argc == 3 && strcmp(argv[2], "--verify") == 0) return verify();
    if (argc == 4 && strcmp(argv[2], "--date") == 0) preview_date = argv[3];
    else if (argc != 2) return 2;
    if (!jump((Location){0, 0}, 0)) return 1;
#ifdef PW3_HOST
    return terminal();
#else
    return kindle();
#endif
}
