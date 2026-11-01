# R22 integration candidate — 2026-11-01

## Verification state

**R22 ARM/QEMU: NOT RUN; R22 PASS: NOT CLAIMED.** The source-only R22 candidate was prepared as a downloadable conversation ZIP, not installed on Kindle hardware.

- Unmodified R21.5 host regression suite: **32/32 passed**.
- New R22 host verification: **9/9 passed**.
- Four new Lua probe files passed a local Lua syntax check.
- Source-only archive: `pw3-os-r22-plugin-integration-candidate.zip`; no stock firmware, captured Kindle data, or proprietary runtime binaries.
- Offline ARM execution is **pending** because the local R13 stage is held on the user's Mac.

## What R22 candidate actually tests

The new fixture calls KOReader's genuine `PluginLoader:loadPlugins()`, `_load()`, and `createPluginInstance()`, with `_discover()` constrained to the single Ink Away plugin. This prevents enumeration/execution of other plugin main and metadata files while retaining the stock loading and instance lifecycle. Plugin identity after KOReader's directory-name normalization is `ink-away`, while the FileManager menu key is `inkaway`.

Probes verify real FileManager ownership, real dispatcher and Tools menu registration, opening the canvas via the Ink Away **menu callback**, synthetic UIManager gesture events, temporary project save and return to FileManager. They retain the R17/R19 forbidden-module, shell, device-I/O, and out-of-temp-write checks. Automatic Ink Away updates are turned off in in-memory settings; Docker networking remains disabled.

These probe sources must be run using the retained full offline R21.5 handoff plus the stage described below. This GitHub status document is not itself an executable R22 suite.

## Pinned upstream code inspected

- KOReader `v2026.07.2`: [frontend/pluginloader.lua](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/pluginloader.lua) and [FileManager](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/filemanager/filemanager.lua)
- Ink Away `v4.4.0`: [main.lua](https://github.com/EmirErtorer/ink-away.koplugin/blob/v4.4.0/main.lua) and [_meta.lua](https://github.com/EmirErtorer/ink-away.koplugin/blob/v4.4.0/_meta.lua)

## Mac commands after extracting R22 source-only ZIP

```sh
cd ~/Downloads/pw3-os-r22-plugin-integration/src/r21-filemanager-core
./HOST-VERIFY-R22.sh
./run-r22-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$PWD/results-r22-first-run"
cat results-r22-first-run/R22-EMULATION.log
cat results-r22-first-run/R22-RESULT-REVIEW.json
```

The script refuses existing results folders, audits genuine staged sources before the run and uses Docker `--network none --read-only --cap-drop ALL` with no device mounts. If any required native source or ARM proof fails, **stop and preserve the failure logs**; do not claim R22 verified.

## Holds

`NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.

This milestone does not authorize a flash, image deployment, physical framebuffer update, or hardware control. The v6 read-only device inventory and R22 host integration are separate evidence streams.
