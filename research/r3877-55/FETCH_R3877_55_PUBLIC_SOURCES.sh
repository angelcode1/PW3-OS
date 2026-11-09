#!/bin/sh
# Fetch exactly 5 public source files on Mac. Does not contact Kindle or Docker.
set -eu
out=${1:-sources}
mkdir -p "$out/alpine" "$out/busybox/miscutils" "$out/busybox/shell"
base='https://raw.githubusercontent.com'
a='35f5eb2864e50dd4448758d31f3e2a32f733ab84'
b='1_37_0'
fetch() {
  dest=$1 url=$2
  if [ -L "$out/$dest" ]; then echo 'REFUSED_SYMLINK_DESTINATION' >&2; exit 2; fi
  temp="$out/$dest.tmp.$$"
  trap 'rm -f "$temp"' EXIT HUP INT TERM
  curl --fail --location --silent --show-error --retry 0 --connect-timeout 10 --max-time 45 "$url" -o "$temp"
  mv "$temp" "$out/$dest"
  trap - EXIT HUP INT TERM
}
fetch alpine/APKBUILD "$base/alpinelinux/aports/$a/main/busybox/APKBUILD"
fetch alpine/busyboxconfig "$base/alpinelinux/aports/$a/main/busybox/busyboxconfig"
fetch alpine/busyboxconfig-extras "$base/alpinelinux/aports/$a/main/busybox/busyboxconfig-extras"
fetch busybox/miscutils/seedrng.c "$base/vda-linux/busybox_mirror/$b/miscutils/seedrng.c"
fetch busybox/shell/random.c "$base/vda-linux/busybox_mirror/$b/shell/random.c"
echo 'FETCH_FINISHED: 5 pinned public sources copied to Mac; validate all Git blobs with the Python auditor before trusting.'
