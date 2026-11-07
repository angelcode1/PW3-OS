#!/bin/sh
# Mac-only: official Alpine Linux aports git snapshot; verifies no secrets or Kindle access.
set -eu
out=${1:-aports-keys}
mkdir -p "$out"
base='https://raw.githubusercontent.com/alpinelinux/aports/35f5eb2864e50dd4448758d31f3e2a32f733ab84/main/alpine-keys'
for name in alpine-devel@lists.alpinelinux.org-616adfeb.rsa.pub alpine-devel@lists.alpinelinux.org-6165ee59.rsa.pub; do
  curl --fail --location --silent --show-error --retry 0 --connect-timeout 10 --max-time 45 \
    "$base/$name" -o "$out/$name"
done
echo 'Public keys downloaded. The Python audit must verify their pinned Git blobs before trusting.'
