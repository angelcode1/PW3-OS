#!/bin/sh
# No Kindle. No guest execution. Copies from a STOPPED Docker container to Mac.
set -eu
IMAGE='pw3-r3877-signed-alpine:3.24.3-armv7-dc1ddfaf03ed'
EXPECTED='sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a'
OUT="${1:-candidate}"
command -v docker >/dev/null 2>&1 || { echo 'HOLD: docker not installed' >&2; exit 2; }
actual=$(docker image inspect --format '{{.Id}}' "$IMAGE") || { echo 'HOLD: candidate image unavailable' >&2; exit 2; }
[ "$actual" = "$EXPECTED" ] || { echo 'HOLD: candidate image ID differs from audited baseline' >&2; exit 2; }
mkdir -p "$OUT"
container=''
cleanup(){ [ -z "$container" ] || docker rm -f "$container" >/dev/null 2>&1 || :; }
trap cleanup EXIT HUP INT TERM
container=$(docker create --entrypoint /bin/true "$IMAGE") || { echo 'HOLD: unable to create stopped inspection container' >&2; exit 2; }
# docker create does not start the container; docker cp does not execute guest code.
docker cp "$container:/lib/apk/db/installed" "$OUT/installed.db" || exit 2
docker cp -L "$container:/lib/ld-musl-armhf.so.1" "$OUT/loader" || exit 2
printf '%s\n' "$actual" > "$OUT/image-id.txt"
echo 'Candidate package metadata and loader copied to Mac; no container execution.'
