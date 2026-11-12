#!/bin/sh
# ATTENDED 30-second live NetSurf display trial. Never invoked at boot.
# Gate the real framebuffer presenter and restore Home even if the child
# browser exits unexpectedly. Bounded to one local, trusted HTML fixture.
set -eu
[ "$#" -eq 1 ] && [ "$1" = "--run" ] || {
  echo "Usage: CODEX_BROWSER_LIVE_TRIAL=EXPLICIT codex-browser-live-trial --run" >&2; exit 64;
}
env | grep -qx 'CODEX_BROWSER_LIVE_TRIAL=EXPLICIT' && [ -t 0 ] || {
  echo "Live display requires explicit gate and interactive SSH terminal" >&2; exit 78;
}
R=/run/codex-browser
BIN=/usr/bin/netsurf-framebuffer
SHARE=/usr/share/netsurf
HTML=/usr/share/codex/browser-smoke.html
CAP=/usr/local/lib/codex/libcodex-sdl-capture.so
INPUT=/usr/local/lib/codex/libcodex-sdl-touch-input.so
PY=/usr/local/lib/codex/codex-browser-live-frames.py
VP=/usr/local/lib/codex/verify_direct_sdl.py
PANEL=/usr/local/bin/codex-browser-panel-preview
for f in "$BIN" "$CAP" "$INPUT" "$PANEL"; do [ -x "$f" ] || {
  echo "MISSING_BROWSER_BINARY=$f" >&2; exit 69;
}; done
for f in "$PY" "$VP" "$HTML"; do [ -f "$f" ] || {
  echo "MISSING_BROWSER_RESOURCE=$f" >&2; exit 69;
}; done
[ -d "$SHARE" ] || { echo MISSING_NETSURF_RESOURCES >&2; exit 69; }
# Avoid a hidden second display owner or stale lock takeover.
mkdir -p "$R"
chmod 700 "$R"
LOCK=$R/.live-trial-lock
mkdir "$LOCK" 2>/dev/null || {
  echo "Another/stale live trial lock exists; refusing to run" >&2; exit 75;
}
home_pid=
browser_pid=
converter_pid=
cleaning=0
cleanup() {
  [ "$cleaning" -eq 0 ] || return
  cleaning=1
  trap - EXIT INT HUP TERM
  if [ -n "$browser_pid" ]; then kill "$browser_pid" 2>/dev/null || :; fi
  if [ -n "$converter_pid" ]; then kill "$converter_pid" 2>/dev/null || :; fi
  if [ -n "$browser_pid" ]; then wait "$browser_pid" 2>/dev/null || :; fi
  if [ -n "$converter_pid" ]; then wait "$converter_pid" 2>/dev/null || :; fi
  if [ -n "$home_pid" ]; then
    kill -CONT "$home_pid" 2>/dev/null || :
    # Existing init loop redraws Home on termination; no menu changes.
    kill -TERM "$home_pid" 2>/dev/null || :
  fi
  rmdir "$LOCK" 2>/dev/null || :
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP
# Verify geometry and exact test fixture before any panel write.
"$PANEL" --selftest
/usr/local/bin/codex-display-probe --read-only /dev/fb0
# Home is the usual e-ink panel owner; pause it just for this session.
home_pid=$(ps | awk '$0 ~ /\/usr\/local\/bin\/home$/ && $0 !~ /awk/ {print $1; exit}')
[ -n "$home_pid" ] && kill -STOP "$home_pid"
rm -f "$R/codex-live-sdl.bmp" "$R/codex-browser-live-stream.pgm"
export NETSURFRES="$SHARE"
export HOME=/tmp/codex-browser-live-home
mkdir -p "$HOME"
echo CODEX_BROWSER_LIVE_TRIAL_STARTED
CODEX_SDL_CAPTURE_ENABLE=PW3_ATTENDED CODEX_SDL_INPUT_ENABLE=PW3_ATTENDED \
SDL_VIDEODRIVER=dummy DISPLAY= LD_PRELOAD="$CAP:$INPUT" \
"$BIN" -f sdl -w 600 -h 800 -b 32 \
  "file://$HTML" < /dev/tty > "$R/live-netsurf.log" 2>&1 &
browser_pid=$!
CODEX_BROWSER_LIVE_TRIAL=EXPLICIT python3 "$PY" --follow-seconds 33 \
  > "$R/live-converter.log" 2>&1 &
converter_pid=$!
# Only this process opens the framebuffer for changes. It snapshots
# visible pixels, submits at most one GC16 frame per 1.8 seconds and
# restores after a fixed 30 seconds or normal signal interruption.
CODEX_BROWSER_PANEL_TRIAL=EXPLICIT "$PANEL" --follow-pgm \
  "$R/codex-browser-live-stream.pgm" --confirm-pw3
echo CODEX_BROWSER_LIVE_TRIAL_PASS
