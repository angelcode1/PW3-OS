#!/bin/sh
# Mac only; public Alpine v3.24 armv7 repository. No device access, no package install.
set -eu
OUT="${1:-public-musl}"
mkdir -p "$OUT"
BASE='https://dl-cdn.alpinelinux.org/alpine/v3.24/main/armv7'
curl --fail --location --silent --show-error --retry 0 --connect-timeout 15 --max-time 120 \
  "$BASE/musl-1.2.6-r3.apk" -o "$OUT/musl-1.2.6-r3.apk"
curl --fail --location --silent --show-error --retry 0 --connect-timeout 15 --max-time 120 \
  "$BASE/APKINDEX.tar.gz" -o "$OUT/APKINDEX.tar.gz"
echo 'Public package and index downloaded to Mac. Verify with Python before trusting.'
