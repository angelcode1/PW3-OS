/* PW3-OS Games folder. Inkwell's e-ink drawing and input API, PW3-OS own games.
 * No upstream Inkwell games are linked or launched.
 */
#include "ui.h"
#include <signal.h>
#include <sys/wait.h>
#include <unistd.h>

static int top, cellh, cellw;
static void draw_choice(int y, const char *name, const char *detail) {
    fill(56, y, W - 112, cellh - 24, WHITE);
    frame(56, y, W - 112, cellh - 24, 4, 0x44);
    text_center(&f_ui_bold, 56, W / 2, y + 34, name, BLACK);
    text_center(&f_ui, 31, W / 2, y + 113, detail, 0x40);
}
static void draw_menu(void) {
    top = H / 4;
    cellh = (H - top - 190) / 2;
    cellw = W - 112;
    fill(0, 0, W, H, WHITE);
    text_center(&f_ui_bold, 72, W / 2, 65, "Games", BLACK);
    text_center(&f_ui, 32, W / 2, 165, "Choose a puzzle", 0x55);
    draw_choice(top, "Memory Match", "Find eight matching pairs");
    draw_choice(top + cellh, "Sudoku", "Fill the 9 x 9 number grid");
    frame(56, H - 120, cellw, 85, 3, 0x55);
    text_center(&f_ui_bold, 37, W / 2, H - 101, "Back to Home", BLACK);
    flip();
}
static void launch(const char *game) {
    pid_t pid = fork();
    if (pid == 0) {
        setsid();
        execl("/usr/local/bin/pw3-puzzles", "pw3-puzzles", game, (char *)0);
        _exit(127);
    }
    if (pid > 0) {
        int st;
        while (waitpid(pid, &st, 0) < 0 && errno == EINTR) {}
    }
    input_drain();
    draw_menu();
}
int main(void) {
    signal(SIGCHLD, SIG_DFL);
    if (fb_open() || fonts_load()) return 1;
    input_open();
    draw_menu();
    for (;;) {
        event e = input_wait(60000);
        if (e.type == EV_POWER) return 0;
        if (e.type != EV_TAP) continue;
        if (e.ux < 56 || e.ux > W - 56) continue;
        if (e.uy >= H - 120) return 0;
        if (e.uy >= top && e.uy < top + cellh - 24) launch("match");
        else if (e.uy >= top + cellh && e.uy < top + 2 * cellh - 24) launch("sudoku");
    }
}
