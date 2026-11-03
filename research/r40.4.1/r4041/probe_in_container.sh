#!/bin/sh
# R40.4.1 independent FileManager-only QEMU replay, no device access or networking.
set -eu
ROOT=/stage/rootfs
APP="$ROOT/opt/koreader-compat/app"
GNU="$ROOT/opt/koreader-compat/gnu/lib"
RAW=/results/R4041-QEMU-RAW-PRIVATE.log
STDOUT=/results/R4041-GUEST-STDOUT-PRIVATE.log
STATUS=/results/R4041-EXIT.txt
[ -d "$APP" ] && [ -d "$GNU" ] && [ -r /r4041/01_fm_only.lua ] && [ -r /r4041/loop_guard.lua ] || exit 86
[ ! -e "$RAW" ] && [ ! -e "$STDOUT" ] && [ ! -e "$STATUS" ] || exit 87
cd "$APP"
export HOME=/tmp/r25-ko-home KO_HOME=/tmp/r25-ko-home LC_ALL=C
export LUA_PATH='/r4041/?.lua;/r394/?.lua;/usr/local/share/r25_3/?.lua;/usr/local/share/r24_2/?.lua;/usr/local/share/r23_4/?.lua;/usr/local/share/r23/?.lua;/usr/local/share/r22/?.lua;/usr/local/share/r21/?.lua;/usr/local/share/r20/?.lua;/usr/local/share/r19/?.lua;/usr/local/share/r18/?.lua;/usr/local/share/r17/?.lua;;'
mkdir -p /tmp/r25-ko-home/library
set +e
timeout 180s qemu-arm -strace "$GNU/ld-linux.so.3" --library-path "$APP/libs:$APP/common:$GNU" \
 "$APP/luajit" /r4041/01_fm_only.lua /tmp/r25-ko-home/library > "$STDOUT" 2> "$RAW"
RC=$?
set -e
printf 'R4041_QEMU_EXIT=%s\n' "$RC" > "$STATUS"
if [ "$RC" -eq 0 ]; then
  # A shell-level exit gate, never guest-source, collector, or reviewer fabricated.
  printf 'R4041_QEMU_POST_EXIT_ZERO_BOUNDARY\n' >> "$STDOUT"
else
  printf 'R4041_QEMU_POST_EXIT_FAIL\n' >> "$STDOUT"
  exit "$RC"
fi
