#!/bin/sh
# PW3-OS Alpine entrypoint, derived from Inkwell own-init (MIT, Pragyaan Gaur).
# Userstore /mnt/us is bind-mounted by the early-boot runner.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin HOME=/root
D=/mnt/us/pw3os
mkdir -p /run /tmp /var/log "$D/logs" /root/.ssh
chmod 1777 /tmp
chmod 700 /root/.ssh
exec >>"$D/logs/alpine-own-init.log" 2>&1
echo "=== PW3-OS Alpine boot $(date) ==="
uname -a
cat /etc/alpine-release
# Avoid boot-time APK upgrades and nested tmpfs mounts: the image was assembled offline.
if [ -s "$D/authorized_keys" ]; then
    tr -d '\r' < "$D/authorized_keys" > /root/.ssh/authorized_keys
    chmod 600 /root/.ssh/authorized_keys
else
    echo 'WARNING: no authorized_keys on userstore; SSH public-key login unavailable'
fi
# Inkwell's working Wi-Fi/userspace approach; kernel ath6kl_sdio module is loaded by early-boot runner.
ifconfig lo 127.0.0.1 up || :
if [ -r "$D/wifi.conf" ]; then
    mkdir -p /run/wpa_supplicant
    ifconfig wlan0 up || :
    wpa_supplicant -B -i wlan0 -D nl80211 -c "$D/wifi.conf" -P /run/wpa_supplicant.pid || :
    udhcpc -i wlan0 -b -S -p /run/udhcpc.wlan0.pid || :
else
    echo 'WARNING: wifi.conf missing; configure it locally on the userstore'
fi
# Key-only Dropbear, on the same port verified in PW3-OS Batch 4.4.
dropbear -R -s -p 2223 -P /run/dropbear.pid || :
echo 'PW3OS: Dropbear launched on port 2223 (check actual listening socket over SSH)'
# Keep useful logs on userstore, not only in the writable image.
(
  while :; do
    echo "PW3OS_HEARTBEAT $(date) $(cat /proc/uptime)" >> "$D/logs/heartbeat.log"
    sleep 60
  done
) &
HEARTBEAT=$!
crashes=0
while :; do
    echo 'PW3OS: starting graphical home'
    /usr/local/bin/home
    status=$?
    echo "PW3OS: home exited with $status"
    case "$status" in
        10|11|12) break ;;
    esac
    crashes=$((crashes + 1))
    if [ "$crashes" -ge 5 ]; then
        echo 'PW3OS: home repeatedly failed; hand back to stock next boot'
        status=13
        break
    fi
    sleep 1
done
kill "$HEARTBEAT" 2>/dev/null || :
for pid in /run/dropbear.pid /run/wpa_supplicant.pid /run/udhcpc.wlan0.pid; do
    if [ -f "$pid" ]; then kill "$(cat "$pid")" 2>/dev/null || :; fi
done
sync
exit "$status"
