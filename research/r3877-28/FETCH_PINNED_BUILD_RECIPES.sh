#!/bin/sh
# Downloads public recipe files to the Mac. The Python audit pins their Git blobs before use.
set -eu
out=${1:-build-recipes}
base='https://raw.githubusercontent.com/alpinelinux/aports/35f5eb2864e50dd4448758d31f3e2a32f733ab84'
mkdir -p "$out"
for name in build-base gcc binutils make abuild; do
  curl -fLsS --retry 0 --connect-timeout 12 --max-time 45 \
    "$base/main/$name/APKBUILD" -o "$out/$name.APKBUILD"
done
printf '%s\n' 'Downloaded public recipes. Verify their pinned Git blobs with Python before using.'
