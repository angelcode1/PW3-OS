#!/bin/sh
# Experimental Browser Test tile for Codex Home. Unlike the SSH trial,
# Home itself owns and waits for the child app; NEVER signal Home here.
# Built-in time limit is 30 seconds; no boot or stock UI changes.
set -eu
[ "$#" -eq 0 ] || { echo "Home browser preview takes no arguments" >&2; exit 64; }
R=/run/codex-browser
PANEL=/usr/local/bin/codex-browser-panel-preview
PROBE=/usr/local/bin/codex-display-probe
BIN=/usr/bin/netsurf-framebuffer
CAP=/usr/local/lib/codex/libcodex-sdl-capture.so
INPUT=/usr/local/lib/codex/libcodex-sdl-touch-input.so
FAST=/usr/local/bin/codex-browser-fast-frames
PY=/usr/local/lib/codex/codex-browser-live-frames.py
VERIFY=/usr/local/lib/codex/verify_direct_sdl.py
HTML=/usr/share/codex/browser-interactive.html
RES=/usr/share/netsurf

# A real /usr/local/bin/home process must be our ancestor. This prevents
# accidentally launching a physical panel session from a detached service.
"$PANEL" --home-origin-check || exit 78
for p in "$PANEL" "$PROBE" "$BIN" "$CAP" "$INPUT" "$FAST"; do
  [ -x "$p" ] || { echo "CODEX_BROWSER_HOME_MISSING_BINARY=$p" >&2; exit 69; }
done
for p in "$PY" "$VERIFY" "$HTML"; do
  [ -r "$p" ] || { echo "CODEX_BROWSER_HOME_MISSING_RESOURCE=$p" >&2; exit 69; }
done
[ -d "$RES" ] || exit 69
"$PANEL" --selftest || exit 69
"$PROBE" --read-only /dev/fb0 || exit 69
mkdir -p "$R"
chmod 700 "$R"
LOCK="$R/.live-trial-lock"
mkdir "$LOCK" 2>/dev/null || {
  echo "CODEX_BROWSER_HOME_ALREADY_RUNNING" >&2; exit 75;
}
browser_pid=
converter_pid=
cleaning=0
cleanup() {
  [ "$cleaning" -eq 0 ] || return
  cleaning=1
  trap - EXIT INT HUP TERM
  [ -z "$browser_pid" ] || kill "$browser_pid" 2>/dev/null || :
  [ -z "$converter_pid" ] || kill "$converter_pid" 2>/dev/null || :
  [ -z "$browser_pid" ] || wait "$browser_pid" 2>/dev/null || :
  [ -z "$converter_pid" ] || wait "$converter_pid" 2>/dev/null || :
  rmdir "$LOCK" 2>/dev/null || :
  # Returning from this launcher makes upstream Home's run_app() call
  # draw_home() itself. Do NOT kill, STOP, or restart its parent process.
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

rm -f "$R/codex-live-sdl.bmp" "$R/codex-browser-live-stream.pgm"
export NETSURFRES="$RES"
export HOME=/tmp/codex-browser-home-preview
mkdir -p "$HOME"
echo CODEX_BROWSER_HOME_PREVIEW_STARTED
CODEX_SDL_CAPTURE_ENABLE=PW3_ATTENDED \
CODEX_SDL_INPUT_ENABLE=PW3_HOME_PREVIEW \
SDL_VIDEODRIVER=dummy DISPLAY= LD_PRELOAD="$CAP:$INPUT" \
"$BIN" -f sdl -w 600 -h 800 -b 32 "file://$HTML" \
  < /dev/null > "$R/home-netsurf.log" 2>&1 &
browser_pid=$!
CODEX_BROWSER_LIVE_TRIAL=EXPLICIT "$FAST" --follow-seconds 33 \
  < /dev/null > "$R/home-converter.log" 2>&1 &
converter_pid=$!
CODEX_BROWSER_PANEL_TRIAL=HOME_PREVIEW \
"$PANEL" --follow-pgm "$R/codex-browser-live-stream.pgm" --confirm-home
echo CODEX_BROWSER_HOME_PREVIEW_COMPLETED
