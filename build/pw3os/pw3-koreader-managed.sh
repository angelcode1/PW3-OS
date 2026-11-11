#!/bin/sh
# PW3-OS durable KOReader launcher: independent of KOReader release files.
set -u
MANAGER=/usr/local/lib/pw3os/koreader_update.py
PATCH=/usr/local/lib/pw3os/2-pw3os-autoupdate.lua
export HOME=/root LC_ALL=C
export KO_HOME=/mnt/us/pw3os/koreader-data
export KOREADER_DIR=/opt/koreader
LOADER=/opt/koreader-compat/gnu/lib/ld-linux.so.3
LIB=/opt/koreader-compat/gnu/lib:/opt/koreader-compat/app/ffi:/opt/koreader/libs:/opt/koreader/ffi

if [ ! -r "$MANAGER" ] || [ ! -r "$PATCH" ] || [ ! -f "$LOADER" ]; then
    echo "HOLD: PW3OS_KOREADER_RUNTIME_COMPONENTS_MISSING" >&2
    exit 2
fi
mkdir -p "$KO_HOME/patches" "$KO_HOME/ota" /var/tmp

# Move user-specific data out of the app release on first managed launch.
# The shared Kindle userstore persists across future Alpine image updates.
if [ ! -e "$KO_HOME/.pw3os-migrated" ]; then
    for item in settings.reader.lua settings history docsettings hashdocsettings \
                data plugins screenshots styletweaks cache; do
        if [ -e "/opt/koreader/$item" ] && [ ! -e "$KO_HOME/$item" ]; then
            cp -r "/opt/koreader/$item" "$KO_HOME/$item" || exit 3
        fi
    done
    touch "$KO_HOME/.pw3os-migrated"
fi
# Project-owned patch is refreshed by our launcher, not by a KOReader OTA.
if ! cmp -s "$PATCH" "$KO_HOME/patches/2-pw3os-autoupdate.lua"; then
    cp "$PATCH" "$KO_HOME/patches/2-pw3os-autoupdate.lua" || exit 3
fi

if [ ! -e /opt/koreader ]; then
    python3 "$MANAGER" recover || exit 4
fi
if [ ! -x /opt/koreader/luajit ] || [ ! -r /opt/koreader/reader.lua ]; then
    echo "HOLD: KOREADER_RUNTIME_MISSING" >&2
    exit 4
fi

cd /opt/koreader || exit 4
# KOReader Kindle checks the MD5 of the expected startup-script copy.
cp -p ./koreader.sh /var/tmp/koreader.sh || exit 4
cmp -s ./koreader.sh /var/tmp/koreader.sh || exit 4

"$LOADER" --library-path "$LIB" ./luajit ./reader.lua "$@"
status=$?
case "$status" in
    85)
        if python3 "$MANAGER" activate; then
            exec /usr/local/bin/pw3-koreader "$@"
        fi
        echo "HOLD: KOReader update not activated; previous version retained" >&2
        exit 0
        ;;
    0)
        python3 "$MANAGER" first-launch-ok || :
        exit 0
        ;;
    *)
        if python3 "$MANAGER" first-launch-failed; then
            echo "PW3OS: rolled back failed KOReader first launch" >&2
            exec /usr/local/bin/pw3-koreader "$@"
        fi
        exit "$status"
        ;;
esac
