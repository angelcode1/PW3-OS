#!/bin/sh
# Fetch only public build inputs to a local Mac directory. Audit hashes separately.
set -eu
out=${1:-sources}
mkdir -p "$out"
base='https://raw.githubusercontent.com/alpinelinux/aports/35f5eb2864e50dd4448758d31f3e2a32f733ab84/main/musl'
fetch() {
  src=$1
  dst=$2
  curl -fLsS --retry 0 --connect-timeout 12 --max-time 180 "$src" -o "$out/$dst"
}
fetch "$base/APKBUILD" APKBUILD
fetch 'https://musl.libc.org/releases/musl-1.2.6.tar.gz' 'musl-1.2.6.tar.gz'
for name in \
  handle-aux-at_base.patch \
  0001-add-stub-for-pthread_mutexattr_setprioceiling.patch \
  fix-loongarch64-zero-len-extcontext.patch \
  CVE-2026-6042.patch \
  CVE-2026-40200.patch \
  CVE-2026-107891.patch \
  ldconfig __stack_chk_fail_local.c getconf.c getent.c iconv.c
do
  fetch "$base/$name" "$name"
done
printf 'Public Alpine musl source inputs downloaded. Verify with the pinned Python analyzer before trusting.\n'
