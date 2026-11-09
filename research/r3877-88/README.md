# R3877.88 — host-only WidgetContainer source and dependency gate

**R3877.87 user reported PASS on real Kindle:** pinned KOReader `ui/event`, `ui/widget/eventlistener`, `ui/widget/widget`; synthetic event dispatch; SSH exit 0; tmpfs cleanup complete. Sanitized R3877.87 evidence is committed under `research/r3877-87/R3877_87_USER_REPORTED_LIVE_PASS.json`. No GUI or hardware actuation, no boot/mount/firmware changes. `NOT_BOOTABLE` remains mandatory.

The next candidate is the real KOReader v2026.07.2 `frontend/ui/widget/container/widgetcontainer.lua` module. Its genuine direct imports include `ui/geometry` and `ui/widget/widget`. The geometry branch leads through `optmath`, `dbg`, `logger` and the external `ffi/serpent` dependency. This must be checked without guessing unpinned dependency contents or starting the GUI.

**Source package prepared but device not run:** `pw3-r3877-88-widgetcontainer-preflight.zip` (provided as a conversation attachment). The package contains `pw3_r3877_88_container_preflight.py`, `test_r3877_88.py`, `SHA256SUMS_R3877_88.txt` and a runnable README. Local host synthetic tests: 18/18 PASS; source checksum and ZIP integrity checks PASS. The runnable package is not yet committed here as individual source files, and no GitHub R3877.88 CI result is claimed.

This Mac-only tool compares eight named, stage-local KOReader Lua files against their exact upstream Git blob hashes, reports the static, explicitly reviewed import chain and checks candidate paths for `ffi/serpent` without following symlinks or reading/launching that unpinned module. It does **not** execute LuaJIT, connect to Kindle, modify the stage or prove full runtime dependency closure.

### Local run

```zsh
cd ~/Downloads
unzip -oq pw3-r3877-88-widgetcontainer-preflight.zip -d ~/Downloads
cd ~/Downloads/pw3-r3877-88
shasum -a 256 -c SHA256SUMS_R3877_88.txt
python3 -B -m unittest -q test_r3877_88.py
STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
setopt pipefail
python3 -B pw3_r3877_88_container_preflight.py \
  --stage "$STAGE" \
  --acknowledge-mac-only-source-inspection \
  | tee r3877_88_offline.json
printf 'R3877_88_OFFLINE_EXIT_CODE=%s\n' "$?"
```

Expected result is `HOLD`, exit 2, `NOT_BOOTABLE` even when `all_upstream_source_pins_match=true`. Future live WidgetContainer testing requires a separately checksum-pinned provenance review for its external dependencies, strict loader mapping, explicit user opt-in, existing executable tmpfs only and no GUI/input/display/boot modifications.

R26-stage identity mismatch (historical 1,448 vs current 1,446 regular files), independent recovery and full dynamic ELF/Lua dependency closure remain unresolved.
