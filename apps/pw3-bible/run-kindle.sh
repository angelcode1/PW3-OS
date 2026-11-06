#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
exec ./pw3-bible-arm ./bible.pw3 "$@"
