#!/bin/sh
# Codex NetSurf launcher. Only the RAM backend is enabled for offline testing.
# No physical framebuffer, Kindle EPDC or touch device is accessed here.
set -eu
BIN=/usr/bin/netsurf-framebuffer
RES=/usr/share/netsurf
[ -x "$BIN" ] || { echo "Codex Browser: NetSurf ARM binary missing" >&2; exit 69; }
[ -d "$RES" ] || { echo "Codex Browser: NetSurf resources missing" >&2; exit 69; }
case "${1:-}" in
    --diagnose)
        echo "Codex Browser: binary and resources staged; runtime/EPDC/input unverified"
        exit 0
        ;;
    --offscreen-test)
        # Local trusted fixture only; RAM surface means NO user-visible screen.
        [ "$#" -eq 1 ] || { echo "No URL arguments accepted" >&2; exit 64; }
        export NETSURFRES="$RES"
        export HOME="${HOME:-/root}"
        exec "$BIN" -f ram -w 320 -h 480 -b 32 file:///usr/share/codex/browser-smoke.html
        ;;
    --capture-offscreen)
        # Attended local-page test only: no EPDC, /dev/fb0, input or URL.
        [ "$#" -eq 1 ] || exit 64
        [ "${CODEX_BROWSER_ATTENDED:-}" = "EXPLICIT" ] && [ -t 0 ] || {
            echo "An interactive terminal and CODEX_BROWSER_ATTENDED=EXPLICIT are required" >&2
            exit 78
        }
        LIB=/usr/local/lib/codex/libcodex-sdl-capture.so
        VALIDATOR=/usr/local/lib/codex/verify_direct_sdl.py
        [ -s "$LIB" ] && [ -f "$VALIDATOR" ] || {
            echo "Headless browser capture dependencies missing" >&2
            exit 69
        }
        R=/run/codex-browser
        mkdir -p "$R"
        chmod 700 "$R"
        rm -f "$R/codex-live-sdl.bmp" "$R/codex-browser-live-pw3.pgm"
        export NETSURFRES="$RES"
        export HOME=/tmp/codex-browser-attended-home
        mkdir -p "$HOME"
        pid=
        cleanup() {
            [ -z "$pid" ] || kill "$pid" 2>/dev/null || :
            [ -z "$pid" ] || wait "$pid" 2>/dev/null || :
        }
        trap cleanup EXIT INT TERM
        CODEX_SDL_CAPTURE_ENABLE=PW3_ATTENDED SDL_VIDEODRIVER=dummy DISPLAY= \
            LD_PRELOAD="$LIB" "$BIN" -f sdl -w 600 -h 800 -b 32 \
            file:///usr/share/codex/browser-smoke.html \
            > "$R/netSurf-trial.log" 2>&1 &
        pid=$!
        sleep 15
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "NetSurf headless trial exited early" >&2
            cat "$R/netSurf-trial.log" >&2 || :
            exit 1
        fi
        cleanup
        pid=
        python3 "$VALIDATOR" "$R/codex-live-sdl.bmp" "$R/codex-browser-live-pw3.pgm"
        echo "CODEX_BROWSER_HEADLESS_PW3_IMAGE_READY=$R/codex-browser-live-pw3.pgm"
        echo "No screen display or touch integration has run"
        ;;
    *)
        echo "Codex Browser: physical e-ink display/input backend is not implemented" >&2
        echo "Safe commands: --diagnose, --offscreen-test, --capture-offscreen (attended)" >&2
        exit 78
        ;;
esac
