"""Adapt Inkwell Settings to add Terminal without replacing its recovery controls."""
def patch_settings(source: str) -> str:
    edits = [
        ('#include "ui.h"\n', '#include "ui.h"\n#include <errno.h>\n#include <signal.h>\n#include <sys/wait.h>\n#include <unistd.h>\n'),
        ('static rect restart_btn, off_btn, kindle_btn;', 'static rect restart_btn, off_btn, kindle_btn, terminal_btn;'),
        ('int bw = (W - 2 * MARGIN - 40) / 2;', 'int bw = (W - 2 * MARGIN - 80) / 3;'),
        ('off_btn = (rect){MARGIN + bw + 40, 210, bw, 110};',
         'off_btn = (rect){MARGIN + bw + 40, 210, bw, 110};\n'
         '    terminal_btn = (rect){MARGIN + 2 * (bw + 40), 210, bw, 110};'),
        ('pill(off_btn, "Power off", 0);',
         'pill(off_btn, "Power off", 0);\n    pill(terminal_btn, "Terminal", 0);'),
        ('else if (hit(off_btn, e.x, e.y)) press_on(off_btn);',
         'else if (hit(off_btn, e.x, e.y)) press_on(off_btn);\n'
         '            else if (hit(terminal_btn, e.x, e.y)) press_on(terminal_btn);'),
        ('if (hit(off_btn, e.x, e.y)) return 12;',
         'if (hit(off_btn, e.x, e.y)) return 12;\n'
         '        if (hit(terminal_btn, e.x, e.y)) { launch_terminal(); continue; }'),
    ]
    for before, after in edits:
        if source.count(before) != 1:
            raise ValueError("Inkwell Settings upstream layout changed: " + before[:90])
        source = source.replace(before, after, 1)
    marker = 'int main(void) {'
    if source.count(marker) != 1:
        raise ValueError("Inkwell Settings main() changed")
    source = source.replace(marker, """/* Terminal lives inside Settings, preserving Home's recovery return codes. */
static void launch_terminal(void) {
    pid_t pid = fork();
    if (pid == 0) {
        setsid();
        execl("/usr/local/bin/term", "term", (char *)0);
        _exit(127);
    }
    if (pid > 0) {
        int status;
        while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {}
    }
    input_drain();
    draw();
}

""" + marker, 1)
    return source.replace('Inkwell on Alpine %s', 'PW3-OS on Alpine %s')
