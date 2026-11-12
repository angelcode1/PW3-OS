#!/bin/sh
# Experimental browser is intentionally unavailable pending PW3 EPDC/input verification.
set -eu
if [ "${CODEX_BROWSER_ENABLE:-0}" != 1 ] || [ ! -f /etc/codex/browser-backend-verified ]; then
    echo "Codex Browser: framebuffer/input integration unverified" >&2
    exit 78
fi
if [ -x /usr/bin/netsurf-fb ]; then exec /usr/bin/netsurf-fb "$@"; fi
echo "Codex Browser: NetSurf framebuffer binary unavailable" >&2
exit 69
