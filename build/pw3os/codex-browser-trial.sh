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
        if command -v ldd >/dev/null 2>&1; then
            ldd "$BIN" > "$HOME/dependencies.txt" 2>&1 || {
                echo "NetSurf dynamic loader check failed" >&2
                cat "$HOME/dependencies.txt" >&2
                exit 1
            }
            if grep -q "not found" "$HOME/dependencies.txt"; then
                echo "NetSurf shared library not found" >&2
                cat "$HOME/dependencies.txt" >&2
                exit 1
            fi
        fi
        # -f ? enumerates supported libnsfb surfaces without opening one.
        "$BIN" -f '?' > "$HOME/surfaces.txt" 2>&1 || :
        if ! grep -q 'ram' "$HOME/surfaces.txt"; then
            echo "NetSurf did not enumerate a RAM surface" >&2
            cat "$HOME/surfaces.txt" >&2
            exit 1
        fi
        echo "CODEX_NETSURF_ARMV7_TRIAL_LOADER_AND_RAM_SURFACE_PASS"
        echo "Renderer, kernel compatibility under load, EPDC and input remain unverified"
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
