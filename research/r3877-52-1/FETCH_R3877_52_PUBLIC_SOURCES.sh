#!/bin/sh
# Downloads public, pinned musl upstream and public Lab126 mirror files only.
# No Kindle IP, SSH, Docker, root, local raw firmware or binary execution.
set -eu
out=${1:-sources}
mkdir -p "$out"
fetch() {
  rel=$1 repo=$2 commit=$3 path=$4
  dest="$out/$rel"
  if [ -L "$dest" ]; then echo "refusing symlinked output: $rel" >&2; exit 2; fi
  mkdir -p "$(dirname "$dest")"
  temp="$dest.tmp.$$"
  trap 'rm -f "$temp"' EXIT HUP INT TERM
  curl --fail --location --silent --show-error --retry 0 --connect-timeout 10 \
    --max-time 60 "https://raw.githubusercontent.com/$repo/$commit/$path" -o "$temp"
  mv "$temp" "$dest"
  trap - EXIT HUP INT TERM
}
musl='ifduyue/musl'
mref='v1.2.6'
kern='katadelos/linux-3.0.35-lab126'
kref='7ac2585f384573da8cbdcc987a3503e2e6ff1fb4'
fetch musl/src/thread/arm/__set_thread_area.c "$musl" "$mref" src/thread/arm/__set_thread_area.c
fetch musl/src/thread/arm/clone.s "$musl" "$mref" src/thread/arm/clone.s
fetch musl/src/thread/pthread_create.c "$musl" "$mref" src/thread/pthread_create.c
fetch musl/arch/arm/pthread_arch.h "$musl" "$mref" arch/arm/pthread_arch.h
fetch musl/src/time/clock_gettime.c "$musl" "$mref" src/time/clock_gettime.c
fetch musl/src/time/clock_nanosleep.c "$musl" "$mref" src/time/clock_nanosleep.c
fetch musl/src/thread/__timedwait.c "$musl" "$mref" src/thread/__timedwait.c
fetch musl/src/stat/fstatat.c "$musl" "$mref" src/stat/fstatat.c
fetch musl/src/linux/getrandom.c "$musl" "$mref" src/linux/getrandom.c
fetch musl/src/misc/getentropy.c "$musl" "$mref" src/misc/getentropy.c
fetch lab126/arch/arm/include/asm/unistd.h "$kern" "$kref" arch/arm/include/asm/unistd.h
fetch lab126/arch/arm/kernel/traps.c "$kern" "$kref" arch/arm/kernel/traps.c
fetch lab126/arch/arm/kernel/entry-common.S "$kern" "$kref" arch/arm/kernel/entry-common.S
printf '%s\n' 'FETCH_FINISHED: 13 public text files downloaded on Mac; run SHA1 Git blob audit before trusting their content.'
