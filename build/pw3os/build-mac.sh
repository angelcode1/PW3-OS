#!/bin/sh
# One build path on macOS and GitHub Actions. Docker Desktop/Colima/OrbStack supported.
set -eu
HERE=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
REPO=$(CDPATH='' cd -- "$HERE/../.." && pwd)
OUTPUT=${PW3_OUTPUT:-"$REPO/out/pw3os"}
mkdir -p "$OUTPUT"
IMAGE_TAG=pw3os-alpine-builder:0.14.1
if ! command -v docker >/dev/null 2>&1; then
    echo 'Install/start Docker Desktop, Colima, or OrbStack first.' >&2; exit 2
fi
docker build --platform linux/amd64 -t "$IMAGE_TAG" -f "$HERE/Dockerfile" "$HERE"
# Optional local KOReader dual-libc stage and Life Bible APK. Neither is sent to CI.
set -- -v "$REPO:/repo:ro" -v "$OUTPUT:/output"
if [ -n "${PW3_STAGE:-}" ]; then
    [ -d "$PW3_STAGE" ] || { echo 'PW3_STAGE must be a rootfs directory' >&2; exit 2; }
    set -- "$@" -v "$PW3_STAGE:/private-stage:ro"
fi
if [ -n "${PW3_LIFE_APK:-}" ]; then
    [ -f "$PW3_LIFE_APK" ] || { echo 'PW3_LIFE_APK must be a file' >&2; exit 2; }
    set -- "$@" -v "$PW3_LIFE_APK:/private/LifeBible.apk:ro"
fi
if [ -n "${PW3_IMAGE_MIB:-}" ]; then
    set -- "$@" -e "PW3_IMAGE_MIB=$PW3_IMAGE_MIB"
fi
docker run --rm --platform linux/amd64 "$@" "$IMAGE_TAG" --output /output
printf 'Build artifacts: %s\n' "$OUTPUT"
