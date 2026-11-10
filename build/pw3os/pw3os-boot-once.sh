#!/bin/sh
# Batch 4.2: association-gated Alpine SSH trial for Alpine SSH session on Amazon kernel 3.0.35-lab126.
# Separate writable debug image; no stock root/kernel/Upstart edits, no reboot.
# The installed one-shot Upstart job consumes the marker and owns boot.log.
# On a verified complete cleanup, return stock even if SSH/network startup fails.
# On UNVERIFIED cleanup, exit nonzero: existing Upstart hook blocks stock startup.
set -u
BB=/bin/busybox
D=/mnt/base-us/pw3os
IMG=$D/alpine-debug.img
R=$D/.pw3os-alpine-live-root
SRC=$D/pw3-debugmount
BIN=/tmp/pw3-debugmount-live
LOOPDEV=''
CREATED=0
COPIED=0
ATTACH_UNCERTAIN=0
ASSOCIATED=0
MOUNTED=0
B_DEV=0
B_PROC=0
B_SYS=0
B_US=0
FIREWALL_RULE=0
FW_BIN=''

preflight_fail() { echo "HOLD: $*" >&2; echo 'RESULT: DEBUG_PREFLIGHT_FAILED_STOCK_CONTINUES'; exit 0; }
trial_fail() { echo "HOLD: $*" >&2; exit 3; }
is_mounted() {
    while read -r dev mp typ opts rest; do
        [ "$mp" = "$1" ] && return 0
    done < /proc/mounts
    return 1
}
loop_is_free() {
    loop_query=$($BB losetup "$1" 2>&1)
    loop_query_rc=$?
    [ "$loop_query_rc" -ne 0 ] || return 1
    case "$loop_query" in *'No such device or address'*) return 0 ;; *) return 1 ;; esac
}
cleanup() {
    trial_exit_status=$?
    trap - 0
    # Drop the temporary inbound SSH exception before any potentially
    # unsafe mount cleanup. Never silently resume stock with an open rule.
    if [ "$FIREWALL_RULE" -eq 1 ]; then
        "$FW_BIN" -D INPUT -i wlan0 -p tcp --dport 2223 -j ACCEPT || {
            echo 'HOLD: TEMP_SSH_PORT_2223_RULE_REMOVE_FAILED' >&2
            exit 7
        }
        FIREWALL_RULE=0
        echo 'RESULT: TEMP_SSH_PORT_2223_REMOVED'
    fi
    # Stop any remaining Alpine-rooted process (including interactive SSH shells)
    # before unmounting. Inkwell uses the same /proc/<pid>/root technique.
    for process in /proc/[0-9]*; do
        [ -d "$process" ] || continue
        process_root=$($BB readlink "$process/root" 2>/dev/null) || continue
        if [ "$process_root" = "$R" ]; then
            $BB kill -TERM "${process#/proc/}" 2>/dev/null || :
        fi
    done
    "$BB" sleep 1
    for process in /proc/[0-9]*; do
        [ -d "$process" ] || continue
        process_root=$($BB readlink "$process/root" 2>/dev/null) || continue
        if [ "$process_root" = "$R" ]; then
            $BB kill -KILL "${process#/proc/}" 2>/dev/null || :
        fi
    done
    "$BB" sleep 1
    if [ "$B_US" -eq 1 ]; then
        "$BIN" umount "$R/mnt/us" || { echo 'HOLD: USERSTORE_BIND_UNMOUNT_UNSAFE' >&2; exit 7; }
    fi
    if [ "$B_SYS" -eq 1 ]; then
        "$BIN" umount "$R/sys" || { echo 'HOLD: SYS_BIND_UNMOUNT_UNSAFE' >&2; exit 7; }
    fi
    if [ "$B_PROC" -eq 1 ]; then
        "$BIN" umount "$R/proc" || { echo 'HOLD: PROC_BIND_UNMOUNT_UNSAFE' >&2; exit 7; }
    fi
    if [ "$B_DEV" -eq 1 ]; then
        "$BIN" umount "$R/dev" || { echo 'HOLD: DEV_BIND_UNMOUNT_UNSAFE' >&2; exit 7; }
    fi
    # Kernel mount table, not script flags, decides whether stock may resume.
    while read -r dev mp typ opts rest; do
        case "$mp" in "$R/"*) echo "HOLD: CHILD_MOUNT_REMAINS=$mp" >&2; exit 7 ;; esac
    done < /proc/mounts
    if [ "$MOUNTED" -eq 1 ]; then
        "$BIN" umount "$R" || { echo 'HOLD: DEBUG_EXT3_UNMOUNT_FAILED' >&2; exit 7; }
    fi
    if is_mounted "$R"; then echo 'HOLD: ALPINE_ROOT_STILL_MOUNTED' >&2; exit 7; fi
    if [ "$ATTACH_UNCERTAIN" -eq 1 ]; then
        echo 'HOLD: LOOP_ASSOCIATION_UNCERTAIN' >&2
        exit 8
    fi
    if [ "$ASSOCIATED" -eq 1 ]; then
        "$BB" losetup -d "$LOOPDEV" || { echo 'HOLD: LOOP_DETACH_FAILED' >&2; exit 8; }
    fi
    if [ -n "$LOOPDEV" ]; then
        loop_is_free "$LOOPDEV" || { echo 'HOLD: LOOP_NOT_FREE_AFTER_DETACH' >&2; exit 8; }
    fi
    if [ "$CREATED" -eq 1 ]; then "$BB" rmdir "$R" || { echo 'HOLD: MOUNTPOINT_RMDIR_FAILED' >&2; exit 9; }; fi
    if [ "$COPIED" -eq 1 ]; then "$BB" rm -f "$BIN" || { echo 'HOLD: TEMP_HELPER_REMOVE_FAILED' >&2; exit 9; }; fi
    "$BB" sync
    echo 'RESULT: DEBUG_EXT3_BIND_AND_LOOP_CLEANLY_RELEASED'
    if [ "$trial_exit_status" -eq 0 ]; then
        echo 'RESULT: ALPINE_SSH_DEBUG_SESSION_PASS_STOCK_CONTINUES'
    else
        echo "RESULT: ALPINE_SSH_DEBUG_SESSION_ERROR_RC=${trial_exit_status}_SAFE_STOCK_FALLBACK"
    fi
    # An SSH failure after successful cleanup is NOT a reason to block Amazon.
    exit 0
}

[ "${1:-}" = --run ] || { echo 'Usage: --run' >&2; exit 2; }
[ -x "$BB" ] && [ -d "$D" ] && [ -r /proc/mounts ] || preflight_fail 'BASE_ENV_MISSING'
[ ! -e "$R" ] && [ ! -L "$R" ] && [ ! -e "$BIN" ] && [ ! -L "$BIN" ] || preflight_fail 'STALE_MOUNT_OR_HELPER'
[ -s "$IMG" ] && [ -s "$D/alpine-debug.img.sha256" ] || preflight_fail 'DEBUG_IMAGE_NOT_STAGED'
[ -s "$SRC" ] && [ -s "$D/DEBUG_MOUNT_BRIDGE.sha256" ] || preflight_fail 'DEBUG_MOUNT_HELPER_NOT_STAGED'
[ -s "$D/wifi.conf" ] || preflight_fail 'WIFI_CONF_MISSING'
base_ok=0
while read -r dev mp fs opts rest; do
    if [ "$mp" = /mnt/base-us ]; then
        [ "$dev" = /dev/loop/0 ] && [ "$fs" = vfat ] || preflight_fail 'USERSTORE_NOT_EXPECTED_VFAT_LOOP0'
        base_ok=1
    fi
done < /proc/mounts
[ "$base_ok" -eq 1 ] || preflight_fail 'USERSTORE_MOUNT_ABSENT'
read -r expected_image image_filename image_extra < "$D/alpine-debug.img.sha256" || preflight_fail 'IMAGE_HASH_MANIFEST_READ'
[ "$image_filename" = alpine-debug.img ] && [ -z "$image_extra" ] || preflight_fail 'IMAGE_HASH_MANIFEST_FORMAT'
actual=$($BB sha256sum "$IMG") || preflight_fail 'IMAGE_SHA256_FAILED'
[ "${actual%% *}" = "$expected_image" ] || preflight_fail 'IMAGE_SHA256_MISMATCH'
read -r expected_helper helper_filename helper_extra < "$D/DEBUG_MOUNT_BRIDGE.sha256" || preflight_fail 'HELPER_HASH_MANIFEST_READ'
[ "$helper_filename" = pw3-debugmount ] && [ -z "$helper_extra" ] || preflight_fail 'HELPER_HASH_MANIFEST_FORMAT'
actual=$($BB sha256sum "$SRC") || preflight_fail 'HELPER_SHA256_FAILED'
[ "${actual%% *}" = "$expected_helper" ] || preflight_fail 'HELPER_SHA256_MISMATCH'
echo 'RESULT: PINNED_DEBUG_IMAGE_AND_MOUNT_HELPER_HASH_PASS'

for n in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16; do
    candidate=/dev/loop/$n
    [ -b "$candidate" ] || continue
    used=0
    while read -r dev mp typ opts rest; do [ "$dev" = "$candidate" ] && used=1; done < /proc/mounts
    [ "$used" -eq 0 ] || continue
    if loop_is_free "$candidate"; then LOOPDEV=$candidate; break; fi
done
[ -n "$LOOPDEV" ] || preflight_fail 'NO_FREE_LOOP_1_TO_16'
echo "SELECTED_FREE_LOOP=$LOOPDEV"

trap cleanup 0
"$BB" cp "$SRC" "$BIN" || trial_fail 'HELPER_COPY_FAILED'
COPIED=1
"$BB" chmod 700 "$BIN" || trial_fail 'HELPER_CHMOD_FAILED'
"$BIN" >/dev/null 2>&1
[ "$?" -eq 2 ] || trial_fail 'ARM_HELPER_NOT_EXECUTABLE'
"$BB" mkdir "$R" || trial_fail 'MOUNTPOINT_CREATE_FAILED'
CREATED=1
loop_is_free "$LOOPDEV" || trial_fail 'LOOP_CHANGED_BEFORE_ATTACH'
ATTACH_UNCERTAIN=1
"$BB" losetup "$LOOPDEV" "$IMG" || trial_fail 'LOOP_ATTACH_FAILED_UNCERTAIN'
ASSOCIATED=1
ATTACH_UNCERTAIN=0
"$BIN" mount-rw "$LOOPDEV" "$R" || trial_fail 'EXT3_RW_MOUNT_FAILED'
MOUNTED=1
for child in dev proc sys mnt/us; do
    [ -d "$R/$child" ] && [ ! -L "$R/$child" ] || trial_fail "BIND_TARGET_UNSAFE_$child"
done
"$BIN" bind /dev "$R/dev" || trial_fail 'DEV_BIND_FAILED'
B_DEV=1
"$BIN" bind /proc "$R/proc" || trial_fail 'PROC_BIND_FAILED'
B_PROC=1
"$BIN" bind /sys "$R/sys" || trial_fail 'SYS_BIND_FAILED'
B_SYS=1
"$BIN" bind /mnt/base-us "$R/mnt/us" || trial_fail 'USERSTORE_BIND_FAILED'
B_US=1
# The stock Kindle normally brings up wlan0 later in boot. Our Upstart job
# intercepts starting dbus before those services, so explicitly load the
# Amazon ath6kl_sdio driver first (the same step used by Inkwell).
# No rmmod, firmware overwrite, USB gadget change or stock-network shutdown.
if [ -d /sys/class/net/wlan0 ]; then
    echo 'PW3_WIFI_PRESTATE=wlan0_present'
else
    echo 'PW3_WIFI_PRESTATE=wlan0_absent'
    driver_loader=''
    for mod in /sbin/modprobe /usr/sbin/modprobe /bin/modprobe /usr/bin/modprobe; do
        if [ -x "$mod" ]; then
            driver_loader=$mod
            break
        fi
    done
    if [ -n "$driver_loader" ]; then
        echo "PW3_WIFI_DRIVER_LOADER=$driver_loader"
        "$driver_loader" ath6kl_sdio 2>&1
        mod_rc=$?
        echo "PW3_WIFI_MODPROBE_RC=$mod_rc"
    else
        echo 'PW3_WIFI_DRIVER_LOADER=busybox_fallback'
        "$BB" modprobe ath6kl_sdio 2>&1
        mod_rc=$?
        echo "PW3_WIFI_MODPROBE_RC=$mod_rc"
    fi
fi
wifi_ticks=0
while [ "$wifi_ticks" -lt 30 ]; do
    [ -d /sys/class/net/wlan0 ] && break
    "$BB" sleep 1
    wifi_ticks=$((wifi_ticks + 1))
done
echo "PW3_WIFI_WAIT_SECONDS=$wifi_ticks"
if [ ! -d /sys/class/net/wlan0 ]; then
    echo 'HOLD: WLAN0_NOT_PRESENT_AFTER_DRIVER_LOAD' >&2
    for netpath in /sys/class/net/*; do
        [ -e "$netpath" ] && echo "PW3_NET_INTERFACE=${netpath##*/}"
    done
    echo 'PW3_WIFI_MODULES:'
    "$BB" grep -i ath6kl /proc/modules 2>/dev/null || :
    for word in ath6kl firmware cfg80211; do
        echo "PW3_WIFI_DMESG_FILTER=$word"
        "$BB" dmesg 2>/dev/null | "$BB" grep -i "$word" | "$BB" tail -n 12 || :
    done
    trial_fail 'WIFI_DRIVER_NOT_READY_BEFORE_ALPINE'
fi
echo 'RESULT: AMAZON_WIFI_INTERFACE_PRESENT_BEFORE_ALPINE'
# Stock Kindle has iptables under /usr/sbin, not /sbin. Its INPUT policy
# is DROP, so the Dropbear socket was unreachable despite successful Wi-Fi.
# Restrict the temporary exception to wlan0 and port 2223 only.
for ipt in /usr/sbin/iptables /sbin/iptables /usr/bin/iptables /bin/iptables; do
    if [ -x "$ipt" ]; then FW_BIN=$ipt; break; fi
done
[ -n "$FW_BIN" ] || trial_fail 'STOCK_IPTABLES_NOT_FOUND'
echo "PW3_FIREWALL_TOOL=$FW_BIN"
"$FW_BIN" -I INPUT 1 -i wlan0 -p tcp --dport 2223 -j ACCEPT || trial_fail 'TEMP_SSH_PORT_2223_RULE_ADD_FAILED'
FIREWALL_RULE=1
echo 'RESULT: TEMP_SSH_PORT_2223_ALLOWED'
# Auto return to stock after ~4 minutes. The outside 330s watchdog kills a
# stuck inner shell; cleanup kills any remaining Alpine-rooted processes.
"$BB" timeout -t 330 "$BB" chroot "$R" /bin/sh /mnt/us/pw3os/PW3-DEBUG-INIT-WIFI42.sh --run
session_status=$?
echo "PW3_DEBUG_ALPINE_SESSION_EXIT=$session_status"
[ "$session_status" -eq 0 ] || trial_fail 'ALPINE_DEBUG_INIT_NONZERO_OR_TIMEOUT'
exit 0
