# R3877.89 — genuine KOReader WidgetContainer child-event dispatch

**Research only. `NOT_BOOTABLE` remains immutable. No firmware / boot changes.**

## Evidence carried forward

- R3877.83 — physical Kindle glibc loader and LuaJIT one-process PASS.
- R3877.85 — physical Kindle FFI libc/libm one-process PASS.
- R3877.86 — physical Kindle genuine `ui/event` module PASS.
- R3877.87 — physical Kindle genuine Widget + EventListener synthetic dispatch PASS.
- R3877.88.3 — Mac-only, all **nine** original staged Lua modules match exact KOReader v2026.07.2 and pinned KOReader-base Git blob IDs. Staged geometry is 10,735 UTF-8 bytes (10,734 Unicode code points); prior apparent mismatch was an upstream character-count error. No stage edits.

## New guarded test prepared (not yet executed on device)

Source-only archive supplied to user: `pw3-r3877-89-koreader-widgetcontainer-dispatch.zip`.

SHA256: `61f186049f424dc794ab001922198a4823a840baa7373bb1f7db95bb4994ea44`.

Locally tested: 24/24 synthetic host tests PASS; fixed remote script `sh -n` PASS; package manifest SHA256 PASS; archive integrity PASS. **No actual R3877.89 Kindle execution, dynamic loader resolution or native module load is claimed.** Original source package is delivered in conversation, **not published as separate repository code in this commit**; no R89 GitHub CI success is claimed.

The new one-shot smoke would import actual staged `ui/widget/container/widgetcontainer` and its eight real Lua dependency files, along with `ui/event`, using the previously verified six ELF objects. 9 Lua files total, **35,685 bytes**. It checks that child 1 declines an event, child 2 consumes it, child 3 never sees it, and a fallback event is handled by the container. It confirms LuaJIT's built-in `bit.band` for this code path.

Remote guard: original kernel/arch check, pre-existing RW executable tmpfs, fixed-name tar, all 15 payload files SHA256 verified, relocated glibc `--inhibit-rpath` and `--inhibit-cache`, loader `--list` with every named library mapped to the RAM directory, a single non-GUI LuaJIT process, checked stdout marker, explicit cleanup on success. No boot hooks, mounts, chroot, firmware writes, EPDC/input access or GUI.

### Mac host validation

```zsh
cd ~/Downloads
unzip -oq pw3-r3877-89-koreader-widgetcontainer-dispatch.zip -d ~/Downloads
cd ~/Downloads/pw3-r3877-89
shasum -a 256 -c SHA256SUMS_R3877_89.txt
python3 -B -m unittest -q test_r3877_89.py
STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
setopt pipefail
python3 -B pw3_r3877_89_container_dispatch.py --stage "$STAGE" --review-only | tee r3877_89_offline.json
printf 'R3877_89_OFFLINE_EXIT_CODE=%s\n' "$?"
```

Expected host result is `HOLD` and exit 2 with `offline_validation_passed=true`, `all_nine_source_pins_match=true`, `module_files=9`, `module_bytes=35685` and `hold_category=HOST_WIDGETCONTAINER_BUNDLE_READY_DEVICE_UNVERIFIED`. On any other result, **stop**.

### Optional attended device smoke ONLY after host success

```zsh
python3 -B pw3_r3877_89_container_dispatch.py \
  --stage "$STAGE" --acknowledge-one-shot-kindle-widgetcontainer-test \
  --target root@192.168.8.102 --port 2222 \
  | tee r3877_89_live.json
printf 'R3877_89_LIVE_EXIT_CODE=%s\n' "$?"
```

A successful live result would be `PASS_KOREADER_WIDGETCONTAINER_CHILD_DISPATCH_SINGLE_PROCESS`, exit 0, **still `NOT_BOOTABLE`**. A failure/disconnect must be treated as a hold with cleanup unconfirmed; do not automatically rerun.

## Still unresolved

Actual KOReader FileManager/ReaderUI GUI on physical Kindle, full Lua/ELF/resource dependencies, e-ink/evdev/power system adaptations, R26 original-stage identity reconciliation, full independent restore, deterministic boot assembly and standalone OS boot. Do not upload proprietary stage files or device backups.
