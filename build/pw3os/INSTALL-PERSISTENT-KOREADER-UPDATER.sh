#!/bin/bash
set -euo pipefail
IP=192.168.8.102
KEY="$HOME/.ssh/pw3os_alpine_ed25519"
BASE=https://raw.githubusercontent.com/angelcode1/PW3-OS/build/pw3-alpine-integrated/build/pw3os
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
SSH=(ssh -T -p 2223 -i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes root@"$IP")
"${SSH[@]}" 'test "$(cat /etc/own/name)" = PW3-OS && test -f /opt/koreader/reader.lua && test -f /opt/koreader-compat/gnu/lib/ld-linux.so.3 && test -d /mnt/us/pw3os && command -v python3 && command -v curl'
for file in koreader_update.py 2-pw3os-autoupdate.lua pw3-koreader-managed.sh; do
  curl -fLsS --retry 3 "$BASE/$file" -o "$TMP/$file"
  test -s "$TMP/$file"
done
(cd "$TMP" && tar -cf - koreader_update.py 2-pw3os-autoupdate.lua pw3-koreader-managed.sh) | "${SSH[@]}" 'mkdir -p /tmp/pw3-koreader-managed && tar -xf - -C /tmp/pw3-koreader-managed'
"${SSH[@]}" 'sh -s' <<'SH'
set -eu
S=/tmp/pw3-koreader-managed
D=/usr/local/lib/pw3os
L=/usr/local/bin/pw3-koreader
python3 -m py_compile "$S/koreader_update.py"
sh -n "$S/pw3-koreader-managed.sh"
mkdir -p "$D" /mnt/us/pw3os/koreader-data/patches
if ! grep -q 'python3 "$MANAGER" activate' "$L" 2>/dev/null; then
    [ ! -e "$L.before-managed" ] || { echo "HOLD: LAUNCHER_BACKUP_ALREADY_EXISTS"; exit 3; }
    cp -p "$L" "$L.before-managed"
fi
cp "$S/koreader_update.py" "$D/koreader_update.py.new"
cp "$S/2-pw3os-autoupdate.lua" "$D/2-pw3os-autoupdate.lua.new"
cp "$S/pw3-koreader-managed.sh" "$L.new"
chmod 755 "$D/koreader_update.py.new" "$L.new"
chmod 644 "$D/2-pw3os-autoupdate.lua.new"
mv "$D/koreader_update.py.new" "$D/koreader_update.py"
mv "$D/2-pw3os-autoupdate.lua.new" "$D/2-pw3os-autoupdate.lua"
mv "$L.new" "$L"
rm -rf "$S"
# The R13 GNU runtime is private and cannot be included in public CI images.
# Preserve a checksum-verified local bundle for future OS image replacements.
B=/mnt/us/pw3os/koreader-compat-r13-private.tar.gz
if [ ! -e "$B" ]; then
    tar -czf "$B.new" -C /opt koreader-compat
    gzip -t "$B.new"
    mv "$B.new" "$B"
    (cd /mnt/us/pw3os && sha256sum koreader-compat-r13-private.tar.gz > koreader-compat-r13-private.tar.gz.sha256)
fi
(cd /mnt/us/pw3os && sha256sum -c koreader-compat-r13-private.tar.gz.sha256)
echo "RESULT: PRIVATE_R13_BACKUP_VERIFIED_ON_USERSTORE"
echo "RESULT: PW3OS_PERSISTENT_KOREADER_UPDATER_INSTALLED"
echo "NEXT: Quit KOReader fully and reopen."
SH
