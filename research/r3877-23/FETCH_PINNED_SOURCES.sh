#!/bin/sh
# Downloads public upstream source files only to your Mac. No Kindle access.
set -eu
OUT="${1:-sources}"
mkdir -p "$OUT"
fetch() {
  file=$1 url=$2
  tmp="$OUT/$file.tmp.$$"
  trap 'rm -f "$tmp"' EXIT HUP INT TERM
  curl --fail --location --silent --show-error --retry 0 --connect-timeout 10 --max-time 50 "$url" -o "$tmp"
  mv "$tmp" "$OUT/$file"
  trap - EXIT HUP INT TERM
}
fetch alpine_APKBUILD https://raw.githubusercontent.com/alpinelinux/aports/35f5eb2864e50dd4448758d31f3e2a32f733ab84/main/musl/APKBUILD
fetch clock_gettime.c https://raw.githubusercontent.com/ifduyue/musl/v1.2.6/src/time/clock_gettime.c
fetch __timedwait.c https://raw.githubusercontent.com/ifduyue/musl/v1.2.6/src/thread/__timedwait.c
fetch getrandom.c https://raw.githubusercontent.com/ifduyue/musl/v1.2.6/src/linux/getrandom.c
fetch fstatat.c https://raw.githubusercontent.com/ifduyue/musl/v1.2.6/src/stat/fstatat.c
fetch arm_syscall.h.in https://raw.githubusercontent.com/ifduyue/musl/v1.2.6/arch/arm/bits/syscall.h.in
fetch arm_syscall_arch.h https://raw.githubusercontent.com/ifduyue/musl/v1.2.6/arch/arm/syscall_arch.h
echo 'Public source files downloaded to Mac. Run Python audit to verify pinned Git blobs before trusting.'
