#!/bin/sh
# Public text source only; HTTPS, pinned Git revisions, independent blob audit required.
# No Kindle, Docker, QEMU or firmware operations.
set -eu
OUT=${1:-sources}
mkdir -p "$OUT"
fetch() {
  dst=$1 url=$2
  parent=$(dirname "$OUT/$dst")
  mkdir -p "$parent"
  tmp="$OUT/$dst.tmp.$$"
  trap 'rm -f "$tmp"' EXIT HUP INT TERM
  curl --fail --location --silent --show-error --retry 0 --connect-timeout 10 --max-time 60 \
    "$url" -o "$tmp"
  mv "$tmp" "$OUT/$dst"
  trap - EXIT HUP INT TERM
}
K='https://raw.githubusercontent.com/katadelos/linux-3.0.35-lab126/7ac2585f384573da8cbdcc987a3503e2e6ff1fb4'
M='https://raw.githubusercontent.com/ifduyue/musl/v1.2.6'
fetch lab126/arch/arm/include/asm/unistd.h "$K/arch/arm/include/asm/unistd.h"
fetch lab126/arch/arm/kernel/calls.S "$K/arch/arm/kernel/calls.S"
fetch musl/src/linux/getrandom.c "$M/src/linux/getrandom.c"
fetch musl/src/misc/getentropy.c "$M/src/misc/getentropy.c"
fetch musl/src/env/__libc_start_main.c "$M/src/env/__libc_start_main.c"
fetch musl/src/env/__stack_chk_fail.c "$M/src/env/__stack_chk_fail.c"
echo 'FETCH_FINISHED: six pinned public source files copied to Mac. Run the Git blob audit before trusting.'
