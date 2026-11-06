#ifndef PW3_BIBLE_AUDIO_UI_H
#define PW3_BIBLE_AUDIO_UI_H
/* Optional runtime UI, gated by actual BlueZ audio output. */
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static int audio_visible, audio_book, audio_chapter, audio_source;
static int audio_playing, audio_paused, audio_popup;
static const char *audio_error = "";
static Hit audio_source_hit, audio_play_hit, audio_option_hits[3];

static const char *audio_sources[] = {"KJV Drama", "CSB", "Breathe NLT"};
static const char *audio_ids[] = {"kjv", "csb", "breathe"};

static int audio_run(const char *action, int source, int book, int chapter) {
    pid_t pid = fork();
    if (pid < 0) return 0;
    if (!pid) {
        char b[12], c[12];
        snprintf(b, sizeof b, "%d", book);
        snprintf(c, sizeof c, "%d", chapter);
        if (strcmp(action, "play") == 0) {
            execlp("python3", "python3", "./audio_control.py", action,
                   audio_ids[source], b, c, (char *)NULL);
        } else {
            execlp("python3", "python3", "./audio_control.py", action, (char *)NULL);
        }
        _exit(127);
    }
    int status;
    while (waitpid(pid, &status, 0) < 0) {
        if (errno != EINTR) return 0;
    }
    return WIFEXITED(status) && WEXITSTATUS(status) == 0;
}

static void audio_stop(void) {
    if (audio_playing) audio_run("stop", audio_source, 0, 0);
    audio_playing = audio_paused = 0;
}

static void audio_on_page(void) {
    if (audio_book != chapter_book || audio_chapter != chapter_num) {
        audio_stop();
        audio_book = chapter_book;
        audio_chapter = chapter_num;
        audio_popup = 0;
        audio_error = "";
        if (audio_book && audio_book < 47 && audio_source == 2) audio_source = 0;
    }
}

static int audio_contains(Hit h, int x, int y) {
    return x >= h.x && x < h.x + h.width && y >= h.y && y < h.y + h.height;
}

static int audio_choices(void) { return audio_book >= 47 ? 3 : 2; }

static void audio_draw_controls(int top, int margin, int px) {
    if (!audio_visible || !audio_book) return;
    int unit = W - 2 * margin;
    int y = top - 2 * px - 1;
    audio_source_hit = (Hit){margin, y, unit * 3 / 5, px * 2, {-2, 0}};
    audio_play_hit = (Hit){margin + unit * 3 / 5 + 8, y,
                          unit * 2 / 5 - 8, px * 2, {-2, 0}};
    frame(audio_source_hit.x, audio_source_hit.y,
          audio_source_hit.width, audio_source_hit.height, 2, BLACK);
    frame(audio_play_hit.x, audio_play_hit.y,
          audio_play_hit.width, audio_play_hit.height, 2, BLACK);
    char source[120], clipped[120];
    snprintf(source, sizeof source, "Audio: %s v", audio_sources[audio_source]);
    text_fit(&f_ui, px - 2, source, audio_source_hit.width - 18, clipped, sizeof clipped);
    text(&f_ui, px - 2, audio_source_hit.x + 8, y + px / 2, clipped, BLACK);
    text_center(&f_ui, px - 2, audio_play_hit.x + audio_play_hit.width / 2,
                y + px / 2, audio_playing && !audio_paused ? "Pause" : "Play", BLACK);
    if (*audio_error)
        text(&f_ui, px - 5, margin, y + 2 * px + 1, audio_error, BLACK);
    if (!audio_popup) return;
    int n = audio_choices();
    int oy = H / 3, h = px * 2 + 12;
    fill(margin + 14, oy - 12, W - 2 * margin - 28, n * h + 38, WHITE);
    frame(margin + 14, oy - 12, W - 2 * margin - 28, n * h + 38, 3, BLACK);
    for (int i = 0; i < n; i++) {
        audio_option_hits[i] = (Hit){margin + 26, oy + i * h,
                                    W - 2 * margin - 52, h, {-2, 0}};
        frame(audio_option_hits[i].x, audio_option_hits[i].y,
              audio_option_hits[i].width, h - 4, 1, BLACK);
        text(&f_ui, px - 2, audio_option_hits[i].x + 12,
             audio_option_hits[i].y + px / 2, audio_sources[i], BLACK);
    }
}

static int audio_handle_tap(int x, int y) {
    if (!audio_visible || !audio_book) return 0;
    if (audio_popup) {
        int n = audio_choices(), chosen = -1;
        for (int i = 0; i < n; i++)
            if (audio_contains(audio_option_hits[i], x, y)) chosen = i;
        if (chosen >= 0 && chosen != audio_source) {
            audio_stop();
            audio_source = chosen;
            audio_error = "";
        }
        audio_popup = 0;
        return 1;
    }
    if (audio_contains(audio_source_hit, x, y)) {
        audio_popup = 1;
        return 1;
    }
    if (audio_contains(audio_play_hit, x, y)) {
        int ok;
        if (!audio_playing)
            ok = audio_run("play", audio_source, audio_book, audio_chapter);
        else
            ok = audio_run(audio_paused ? "resume" : "pause", audio_source, 0, 0);
        if (ok) {
            if (!audio_playing) { audio_playing = 1; audio_paused = 0; }
            else audio_paused = !audio_paused;
            audio_error = "";
        } else {
            audio_stop();
            audio_error = "Audio unavailable";
        }
        return 1;
    }
    return 0;
}
#endif
