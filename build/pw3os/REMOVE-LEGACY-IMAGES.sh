#!/bin/sh
# Run ONLY over stock SSH after a verified PW3-OS shutdown + stock boot.
# Removes obsolete Alpine image files but never Amazon firmware/kernel/recovery.
set -eu
BB=/bin/busybox
D=/mnt/base-us/pw3os

hold() { echo "HOLD: $*" >&2; exit 3; }
[ "${1:-}" = --remove-legacy-after-stock ] || {
    echo 'Usage: sh REMOVE-LEGACY-IMAGES.sh --remove-legacy-after-stock' >&2
    exit 2
}
[ -x "$BB" ] && [ -d "$D" ] || hold STOCK_USERSTORE_NOT_READY
[ -r /etc/upstart/pw3os-alpine-once.conf ] || hold STOCK_UPSTART_HOOK_NOT_FOUND
[ -s "$D/alpine-os.img" ] || hold NEW_IMAGE_MISSING
[ -s "$D/ATTENDED-LIVE-ALPINE.sh" ] || hold ACTIVE_RUNNER_MISSING
"$BB" grep -Fq 'IMG=$D/alpine-os.img' "$D/ATTENDED-LIVE-ALPINE.sh" ||
    hold ACTIVE_RUNNER_NOT_POINTING_TO_ALPINE_OS
[ ! -e "$D/BOOT_ALPINE_ONCE" ] || hold BOOT_TRIGGER_STILL_ARMED
[ -r "$D/boot-once.log" ] || hold NO_POSTBOOT_LOG
"$BB" grep -Fq 'RESULT: TEMP_SSH_PORT_2223_REMOVED' "$D/boot-once.log" ||
    hold SSH_FIREWALL_CLEANUP_NOT_VERIFIED
"$BB" grep -Fq 'RESULT: DEBUG_EXT3_BIND_AND_LOOP_CLEANLY_RELEASED' "$D/boot-once.log" ||
    hold ROOTFS_CLEANUP_NOT_VERIFIED
# Rootfs mount must NOT be active. Do not touch any mounted or attached image.
while read -r dev mp typ opts rest; do
    case "$mp" in
      "$D/.pw3os-alpine-live-root"|"$D/.pw3os-alpine-live-root/"*)
        hold ALPINE_IMAGE_STILL_MOUNTED ;;
    esac
done < /proc/mounts
for path in /sys/block/loop*/loop/backing_file; do
    [ -r "$path" ] || continue
    while IFS= read -r backing; do
        case "$backing" in
          *alpine.img*|*alpine-debug.img*|*alpine-os.img*)
            hold LOOP_BACKING_STILL_OPEN ;;
        esac
    done < "$path"
done

# Explicitly named legacy files only. Current alpine-os.img is NEVER removed.
for name in alpine.img alpine-debug.img; do
    if [ -f "$D/$name" ]; then
        echo "REMOVING_LEGACY_IMAGE=$name"
        "$BB" rm "$D/$name" || hold "CANNOT_REMOVE_$name"
    fi
done
# Remove stale image hashes only after successful image removal.
for name in alpine.img.sha256 alpine-debug.img.sha256; do
    if [ -f "$D/$name" ]; then
        "$BB" rm "$D/$name" || hold "CANNOT_REMOVE_$name"
    fi
done
"$BB" sync
echo 'RESULT: LEGACY_ALPINE_IMAGES_REMOVED_CURRENT_ALPINE_OS_PRESERVED'
