#!/bin/sh
# Alpine ARMv7/QEMU ONLY. Visual NetSurf smoke test; NEVER opens PW3 framebuffer.
# The caller must explicitly install netsurf-framebuffer, xvfb and scrot.
# Produces baseline.png, netsurf-sdl.png and logs under /reports.
set -eu
umask 077
REPORT_DIR=${CODEX_REPORT_DIR:-/reports}
FIXTURE=/usr/share/codex/browser-smoke.html
BIN=/usr/bin/netsurf-framebuffer
if [ ! -x "$BIN" ] || [ ! -s "$FIXTURE" ]; then
    echo "NetSurf or local fixture missing" >&2
    exit 69
fi
for cmd in Xvfb scrot cmp; do
    command -v "$cmd" >/dev/null 2>&1 || {
        echo "Missing visual test prerequisite: $cmd" >&2
        exit 69
    }
done
# Avoid accidental launch against any physical or host X display.
[ "${CODEX_BROWSER_VISUAL_CI:-0}" = 1 ] || {
    echo "Refusing visual mode without explicit CI gate" >&2
    exit 78
}
[ "${DISPLAY:-}" = "" ] || {
    echo "DISPLAY is already set; refusing to attach to a real display" >&2
    exit 78
}
# The runner owns the bind-mounted report directory but container commands
# execute as root. Return ownership on EVERY exit, including failed tests.
: "${CODEX_CI_HOST_UID:?Missing GitHub runner UID}"
: "${CODEX_CI_HOST_GID:?Missing GitHub runner GID}"
case "$CODEX_CI_HOST_UID:$CODEX_CI_HOST_GID" in
    *[!0-9:]*|:*|*:) echo "Invalid report owner" >&2; exit 64 ;;
esac
mkdir -p "$REPORT_DIR"
chmod 700 "$REPORT_DIR"
export HOME=/tmp/codex-netsurf-test-home
mkdir -p "$HOME"
export NETSURFRES=/usr/share/netsurf
export SDL_VIDEODRIVER=x11
export DISPLAY=:117
server_pid=
browser_pid=
cleanup() {
    [ -z "$browser_pid" ] || kill "$browser_pid" 2>/dev/null || :
    [ -z "$server_pid" ] || kill "$server_pid" 2>/dev/null || :
    [ -z "$browser_pid" ] || wait "$browser_pid" 2>/dev/null || :
    [ -z "$server_pid" ] || wait "$server_pid" 2>/dev/null || :
    # scrot/browser logs are created under umask 077 by container root.
    # Make the reports readable by the runner for PNG validation and upload.
    chown -R "$CODEX_CI_HOST_UID:$CODEX_CI_HOST_GID" "$REPORT_DIR" || :
}
trap cleanup EXIT INT TERM
Xvfb :117 -screen 0 800x1000x24 -nolisten tcp > "$REPORT_DIR/xvfb.log" 2>&1 &
server_pid=$!
ready=0
for i in 1 2 3 4 5 6 7 8 9 10; do
    if scrot -z "$REPORT_DIR/baseline.png" > "$REPORT_DIR/scrot.log" 2>&1; then
        ready=1
        break
    fi
    sleep 1
done
[ "$ready" -eq 1 ] || {
    echo "Virtual display failed" >&2
    cat "$REPORT_DIR/xvfb.log" >&2 || :
    exit 1
}
# NetSurf's SDL surface provides a real visual renderer under virtual X11.
# Both the page and supporting CSS are loaded strictly from local files.
"$BIN" -f sdl -w 600 -h 800 -b 32 "file://$FIXTURE" > "$REPORT_DIR/browser.log" 2>&1 &
browser_pid=$!
# Give NetSurf enough time under QEMU to parse the page and apply CSS.
# An earlier screenshot could show only a blank SDL window.
sleep 28
if ! kill -0 "$browser_pid" 2>/dev/null; then
    echo "NetSurf terminated during visual test" >&2
    cat "$REPORT_DIR/browser.log" >&2 || :
    exit 1
fi
if ! scrot -z "$REPORT_DIR/netsurf-sdl.png" > "$REPORT_DIR/scrot.log" 2>&1; then
    echo "Failed to capture browser Xvfb pixels" >&2
    cat "$REPORT_DIR/scrot.log" >&2 || :
    exit 1
fi
if cmp -s "$REPORT_DIR/baseline.png" "$REPORT_DIR/netsurf-sdl.png"; then
    echo "No changed pixels from browser SDL window" >&2
    cat "$REPORT_DIR/browser.log" >&2 || :
    exit 1
fi
# PNG correctness is also verified by the host-side pixel validator in CI.
echo "CODEX_NETSURF_SDL_VISUAL_CAPTURED_NEEDS_PIXEL_VALIDATION" | tee "$REPORT_DIR/result.txt"
