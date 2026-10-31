# PW3-OS handover — R21.5 verified checkpoint

**Date:** 2026-11-01 (Australia/Brisbane). **Research and educational purposes only.**

## Confirmed result

The user's latest ARM/QEMU Docker run reported:

```text
BOOTSTRAP_HOLD PASS
FIXTURE_STORAGE_BOUNDARY PASS
WINDOW_TITLE_BOUNDARY PASS
SETTINGS_FLUSH_BOUNDARY PASS
REAL_FM_MODULE_IMPORT PASS
REAL_FM_SHOWFILES PASS
REAL_FM_MEMORY_PAINT PASS
REAL_FM_CLOSE PASS
NEGATIVE_SAFETY PASS
R21_ARM_FILEMANAGER_CORE_PASS
R21_RESULT_REVIEW=PASS
```

These are **user-reported** execution results. The full offline handoff independently reran the R21.5 host suite (**32 tests PASS**); the subsequent collector has **seven** separate host tests. The Docker image identifier printed by the user is not a ZIP digest.

## Purpose and architecture

Build an independent lightweight userspace for Kindle Paperwhite 3 with the stock Linux 3.0.35-lab126 kernel/drivers retained, official KOReader `kindlepw2` v2026.07.2 + Ink Away 4.4.0, Alpine ARMv7 musl minirootfs and an isolated GNU glibc 2.20 ARM soft-float compatibility runtime under `/opt/koreader-compat`. Inkwell is a source reference for selective hardware integration, not the chosen reader application.

## Proven by previous host-only QEMU stages

- R10–R12: ARM LuaJIT and real native libraries, Ink Away PDF export, MuPDF roundtrip and annotation.
- R13: Alpine musl BusyBox and KOReader GNU runtime in the same staged rootfs.
- R14–R16.2: synthetic power/network adapter and fail-closed Amazon LIPC import; PW3 class selection without full PW3 init.
- R17: actual KOReader `Generic:init()` with synthetic 1072×1448 300 DPI screen, in-memory BlitBuffer and input queue.
- R18: real UIManager events and memory painting, synthetic Ink Away view.
- R19.4: actual Ink Away view constructor, memory paint, gesture stroke, temporary save/reopen.
- R20: actual Ink Away `UIManager:show()` / stroke / `close()` lifecycle with temporary storage.
- R21.5: actual FileManager/FileChooser import, start, memory painting, and close with plugin activation held off.

**Not proven:** `reader.lua` complete startup, real plugin-loader activation, FileManager→Ink Away navigation, actual e-ink display/ioctls, touch, real battery/frontlight/suspend, networking, complete Amazon LIPC replacement, Kindle-side runtime, independent boot, recovery, or bootable image.

## Immutable safety hold

`NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.

No Kindle firmware/partition/init/kernel/bootloader changes, and no stock-system service changes. Host Docker QEMU tests remain offline, read-only, without mapped device nodes. **Do not use Inkwell's boot/install scripts on the Kindle.** Previous file-access traces are observations, not authority to prune files.

The separately supplied **opt-in, read-only SSH collector** is intended solely for additional evidence if the Kindle already has SSH access, not device execution, hardware control or any change to the stock OS. Never commit raw Kindle captures to this public repo.

## Required local stage

The stage is NOT in GitHub. On the user's Mac:

```text
~/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed
```

This assembled stage depends on verified prior local KOReader captures and official Alpine minirootfs. Do not substitute random ELF libraries.

## Reproduce on Mac

Extract `pw3-os-r21-handoff-complete.zip` (supplied as a separate downloadable artifact in ChatGPT), then:

```sh
cd ~/Downloads/pw3-os-r21-handoff
./scripts/verify-handoff.sh
./scripts/run-r21-on-mac.sh
```

Run the separate read-only collector from the *updated handoff*:

```sh
python3 tools/collect_pw3_readonly.py
python3 tools/collect_pw3_readonly.py --host 192.168.8.102 --port 2222 --collect --out ~/Downloads/pw3-readonly-evidence.zip
```

It writes **only** a local archive. Review the archive for identifying data before sharing. The repo is public.

## R22 continuation

Study actual `frontend/pluginloader.lua`, `frontend/apps/filemanager/filemanager.lua` and `plugins/ink-away.koplugin/main.lua` in the local stage. Enable only Ink Away through KOReader's public plugin-loader path and temporary settings, holding all other plugin activations off. Verify plugin instance ownership by FileManager, menu/action registration, real canvas open/stroke/save/close and return to FileManager. Preserve all previous R21 guards and tests. Neither real device actions nor boot become authorized if R22 passes.

More detailed offline handover, full R21.5 source and old test ZIPs are in the downloadable archive, **not in this first GitHub text commit**.
