#!/bin/sh
# Codex NetSurf launcher. Only the RAM backend is enabled for offline testing.
# No physical framebuffer, Kindle EPDC or touch device is accessed here.
set -eu
BIN=/usr/bin/netsurf-fb
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
    *)
        echo "Codex Browser: physical e-ink display/input backend is not implemented" >&2
        echo "Available safe commands: --diagnose, --offscreen-test" >&2
        exit 78
        ;;
esac
