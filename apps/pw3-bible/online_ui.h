#ifndef PW3_BIBLE_ONLINE_UI_H
#define PW3_BIBLE_ONLINE_UI_H
/* Runtime chapter display only. No disk cache and no cf-signed support. */
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define ONLINE_MAX 64
#define ONLINE_PAGE 6
#define ONLINE_VERSES 200

typedef struct { int volume; char code[24], title[160]; } OnlineEdition;
static OnlineEdition online_catalog[ONLINE_MAX];
static int online_count, online_selected = -1, online_popup, online_page;
static int online_valid, online_failed, online_last_book, online_last_chapter;
static char *online_verses[ONLINE_VERSES];
static Hit online_button_hit, online_option_hits[ONLINE_PAGE];
static Hit online_prev_hit, online_next_hit;
static int online_option_count;

static int online_hit(Hit h, int x, int y) {
    return x >= h.x && x < h.x + h.width && y >= h.y && y < h.y + h.height;
}

static void online_clear(void) {
    for (int i = 0; i < ONLINE_VERSES; ++i) {
        free(online_verses[i]);
        online_verses[i] = NULL;
    }
    online_valid = online_failed = 0;
}

static void online_init(void) {
    FILE *input = fopen("./online-translations.tsv", "r");
    if (!input) return;
    char line[512];
    while (online_count < ONLINE_MAX && fgets(line, sizeof line, input)) {
        if (line[0] == '#' || line[0] == '\n') continue;
        char *first = strchr(line, '\t');
        if (!first) continue;
        *first++ = 0;
        char *second = strchr(first, '\t');
        if (!second) continue;
        *second++ = 0;
        second[strcspn(second, "\r\n")] = 0;
        char *end;
        long volume = strtol(line, &end, 10);
        if (*end || volume <= 0 || volume > 999999 ||
            !*first || strlen(first) >= sizeof online_catalog[0].code ||
            !*second || strlen(second) >= sizeof online_catalog[0].title) continue;
        OnlineEdition *edition = &online_catalog[online_count++];
        edition->volume = (int)volume;
        strcpy(edition->code, first);
        strcpy(edition->title, second);
    }
    fclose(input);
}

/* Child uses the local allowlist and fixed public-CDN hostname. The only
 * bytes returned are verse lines; the parent retains them in RAM. */
static int online_fetch(int volume, int book, int chapter) {
    int fds[2];
    if (pipe(fds)) return 0;
    pid_t pid = fork();
    if (pid < 0) {
        close(fds[0]); close(fds[1]);
        return 0;
    }
    if (pid == 0) {
        close(fds[0]);
        if (dup2(fds[1], STDOUT_FILENO) < 0) _exit(127);
        close(fds[1]);
        FILE *null = fopen("/dev/null", "w");
        if (null) {
            dup2(fileno(null), STDERR_FILENO);
            fclose(null);
        }
        char v[16], b[16], c[16];
        snprintf(v, sizeof v, "%d", volume);
        snprintf(b, sizeof b, "%d", book);
        snprintf(c, sizeof c, "%d", chapter);
        execlp("python3", "python3", "./online_verse.py", v, b, c, (char *)NULL);
        _exit(127);
    }
    close(fds[1]);
    FILE *stream = fdopen(fds[0], "r");
    int ok = stream != NULL, received = 0;
    size_t total_bytes = 0;
    if (stream) {
        char line[8192];
        while (fgets(line, sizeof line, stream)) {
            size_t n = strlen(line);
            total_bytes += n;
            if (total_bytes > 1024 * 1024 || n < 5 ||
                n == sizeof(line) - 1 || line[0] != 'V' || line[1] != '\t') {
                ok = 0; break;
            }
            char *tab = strchr(line + 2, '\t');
            if (!tab) { ok = 0; break; }
            *tab++ = 0;
            char *end = NULL;
            long verse = strtol(line + 2, &end, 10);
            tab[strcspn(tab, "\r\n")] = 0;
            if (*end || verse < 1 || verse >= ONLINE_VERSES ||
                !*tab || online_verses[verse]) { ok = 0; break; }
            online_verses[verse] = strdup(tab);
            if (!online_verses[verse]) { ok = 0; break; }
            ++received;
        }
        fclose(stream);
    } else close(fds[0]);
    int status = 0, waited;
    do { waited = waitpid(pid, &status, 0); } while (waited < 0 && errno == EINTR);
    if (!ok || waited != pid || !WIFEXITED(status) || WEXITSTATUS(status) || !received)
        return 0;
    return 1;
}

static void online_load_current(void) {
    online_clear();
    if (online_selected < 0 || online_selected >= online_count ||
        !chapter_book || !chapter_num) return;
    online_valid = online_fetch(online_catalog[online_selected].volume,
                                chapter_book, chapter_num);
    online_failed = !online_valid;
    if (!online_valid) online_clear(); /* removes partial child output */
    if (!online_valid) online_failed = 1;
}

static void online_on_page(void) {
    if (chapter_book == online_last_book && chapter_num == online_last_chapter) return;
    online_last_book = chapter_book;
    online_last_chapter = chapter_num;
    online_popup = 0;
    online_load_current();
}

static void online_draw_controls(int top, int margin, int px) {
    if (!online_count || !chapter_book) return;
    int y = top - 2 * px - 1;
    online_button_hit = (Hit){margin, y, W - margin * 2, 2 * px, {-2, 0}};
    frame(online_button_hit.x, y, online_button_hit.width, online_button_hit.height, 2, BLACK);
    char label[220], clipped[220];
    if (online_selected < 0)
        snprintf(label, sizeof label, "Text: Offline v");
    else
        snprintf(label, sizeof label, "Text: %s %s v",
                 online_catalog[online_selected].code,
                 online_valid ? "(online)" : "(unavailable; offline shown)");
    text_fit(&f_ui, px - 2, label, online_button_hit.width - 18, clipped, sizeof clipped);
    text(&f_ui, px - 2, margin + 9, y + px / 2, clipped, BLACK);
    if (!online_popup) return;
    int x = margin + 10, width = W - 2 * margin - 20;
    int height = 2 * px + 6, top_y = H / 5;
    fill(x, top_y - 12, width, ONLINE_PAGE * height + 3 * height + 18, WHITE);
    frame(x, top_y - 12, width, ONLINE_PAGE * height + 3 * height + 18, 3, BLACK);
    int first = online_page * ONLINE_PAGE;
    online_option_count = 0;
    for (int index = first; index < first + ONLINE_PAGE && index <= online_count; ++index) {
        int row = online_option_count++;
        Hit h = (Hit){x + 10, top_y + row * height, width - 20, height - 4, {-2, 0}};
        online_option_hits[row] = h;
        frame(h.x, h.y, h.width, h.height, 1, BLACK);
        const char *name = index == 0 ? "Offline (built-in)" : online_catalog[index - 1].title;
        text_fit(&f_ui, px - 3, name, h.width - 18, clipped, sizeof clipped);
        text(&f_ui, px - 3, h.x + 8, h.y + px / 2, clipped, BLACK);
    }
    int nav_y = top_y + ONLINE_PAGE * height + 3;
    online_prev_hit = (Hit){x + 10, nav_y, (width - 30) / 2, height, {-2, 0}};
    online_next_hit = (Hit){x + 20 + (width - 30) / 2, nav_y, (width - 30) / 2, height, {-2, 0}};
    frame(online_prev_hit.x, nav_y, online_prev_hit.width, height - 4, 1, BLACK);
    frame(online_next_hit.x, nav_y, online_next_hit.width, height - 4, 1, BLACK);
    text_center(&f_ui, px - 3, online_prev_hit.x + online_prev_hit.width / 2,
                nav_y + px / 2, online_page ? "Previous" : "-", BLACK);
    text_center(&f_ui, px - 3, online_next_hit.x + online_next_hit.width / 2,
                nav_y + px / 2, (online_page + 1) * ONLINE_PAGE <= online_count ? "Next" : "-", BLACK);
    char page_label[60];
    snprintf(page_label, sizeof page_label, "Page %d / %d",
             online_page + 1, (online_count + ONLINE_PAGE) / ONLINE_PAGE);
    text_center(&f_ui, px - 3, W / 2, nav_y + height + px / 2, page_label, BLACK);
}

/* Returns 2 when displayed text must be reflowed; 1 when only redraw is needed. */
static int online_handle_tap(int x, int y) {
    if (!online_count || !chapter_book) return 0;
    if (online_popup) {
        int first = online_page * ONLINE_PAGE;
        for (int i = 0; i < online_option_count; ++i) {
            if (online_hit(online_option_hits[i], x, y)) {
                int selected = first + i - 1; /* -1 selects offline text */
                online_popup = 0;
                if (online_selected == selected) return 1;
                online_selected = selected;
                online_load_current();
                return 2;
            }
        }
        if (online_hit(online_prev_hit, x, y) && online_page) {
            online_page--;
            return 1;
        }
        if (online_hit(online_next_hit, x, y) &&
            (online_page + 1) * ONLINE_PAGE <= online_count) {
            online_page++;
            return 1;
        }
        online_popup = 0;
        return 1;
    }
    if (online_hit(online_button_hit, x, y)) {
        online_popup = 1;
        online_page = (online_selected + 1) / ONLINE_PAGE;
        audio_popup = 0;
        return 1;
    }
    return 0;
}
#endif
