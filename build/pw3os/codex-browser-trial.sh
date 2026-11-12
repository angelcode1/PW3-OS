#!/bin/sh
# RAM-only NetSurf trial launcher for a pre-existing Codex Alpine ARMv7 session.
# Extract the generated codex-netsurf-test-bundle.tar.gz to a private directory
# and run this script from there. No framebuffer or EPDC calls are made.
set -eu
BASE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BIN="$BASE/usr/bin/netsurf-framebuffer"
RES="$BASE/usr/share/netsurf"
TEST="$BASE/usr/share/codex/browser-smoke.html"
[ -x "$BIN" ] && [ -d "$RES" ] && [ -s "$TEST" ] || {
    echo "NetSurf trial bundle incomplete" >&2; exit 69;
}
export LD_LIBRARY_PATH="$BASE/usr/lib:$BASE/lib"
export NETSURFRES="$RES"
export HOME="${TMPDIR:-/tmp}/codex-netsurf-trial-home"
mkdir -p "$HOME"
case "${1:-}" in
    --diagnose)
        echo "CODEX_NETSURF_ARMV7_TRIAL_STAGED_NOT_DEVICE_VERIFIED"
        exit 0
        ;;
    --offscreen-test)
        [ "$#" -eq 1 ] || exit 64
        LOG="${TMPDIR:-/tmp}/codex-netsurf-trial.log"
        "$BIN" -f ram -w 600 -h 800 -b 32 "file://$TEST" > "$LOG" 2>&1 &
        pid=$!
        # Short, bounded read-only RAM-surface exercise. Never writes EPDC.
        sleep 8
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || :
            wait "$pid" 2>/dev/null || :
            echo "CODEX_NETSURF_RAM_PROCESS_ALIVE_NEEDS_RENDER_VERIFICATION"
        else
            wait "$pid" || :
            echo "Codex NetSurf exited early" >&2
            cat "$LOG" >&2
            exit 1
        fi
        ;;
    *)
        echo "Trial has no physical e-ink backend; use --diagnose or --offscreen-test" >&2
        exit 78
        ;;
esac
