# R22 integration candidate — 2026-11-01

## Verification state

**R22.0 ARM/QEMU: FAIL (2026-11-01); R22.1 corrected candidate: HOST VERIFIED, ARM RERUN PENDING; R22 PASS NOT CLAIMED.**

- First ARM run successfully reached: `R22_REAL_PLUGINLOADER_ONLY_INKAWAY`, `R22_REAL_PLUGIN_INSTANCE_OWNED_BY_FILEMANAGER`, and `R22_REAL_DISPATCHER_AND_MENU_REGISTRATION`.
- It then failed: `plugin_fixture_r22.lua:99: plugin instance retained after FM close`, `REAL_PLUGIN_LOAD FAIL (exit=1)`, and `R22_RESULT_REVIEW=FAIL`. The menu-canvas and negative-safety probes **were not executed** on that run.
- Root cause: the R22 fixture called `UIManager:close(fm)` rather than genuine `FileManager:onClose()`, which is responsible for `PluginLoader:finalize()`. The direct UI call bypassed normal plugin-registry cleanup.
- R22.1 calls `fm:onClose()`, asserts the genuine method source, and preserves plugin-registry, singleton, window-stack, flush, and safety postconditions. No direct manual finalization or weakened checks.
- R21.5 host regression unchanged: **32/32 PASS**; R22.1 host regression: **10/10 PASS** (new teardown test added).
- New source-only archive: `pw3-os-r22.1-plugin-integration.zip`, provided in the conversation. No firmware, captures, secrets, or proprietary runtimes committed.
- **R22.1 ARM/QEMU has not run** in this environment; the user's retained R13 stage is required.

## What R22 candidate actually tests

The new fixture calls KOReader's genuine `PluginLoader:loadPlugins()`, `_load()`, and `createPluginInstance()`, with `_discover()` constrained to the single Ink Away plugin. This prevents enumeration/execution of other plugin main and metadata files while retaining the stock loading and instance lifecycle. Plugin identity after KOReader's directory-name normalization is `ink-away`, while the FileManager menu key is `inkaway`.

Probes verify real FileManager ownership, real dispatcher and Tools menu registration, opening the canvas via the Ink Away **menu callback**, synthetic UIManager gesture events, temporary project save and return to FileManager. They retain the R17/R19 forbidden-module, shell, device-I/O, and out-of-temp-write checks. Automatic Ink Away updates are turned off in in-memory settings; Docker networking remains disabled.

These probe sources must be run using the retained full offline R21.5 handoff plus the stage described below. This GitHub status document is not itself an executable R22 suite.

## Pinned upstream code inspected

- KOReader `v2026.07.2`: [frontend/pluginloader.lua](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/pluginloader.lua) and [FileManager](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/filemanager/filemanager.lua)
- Ink Away `v4.4.0`: [main.lua](https://github.com/EmirErtorer/ink-away.koplugin/blob/v4.4.0/main.lua) and [_meta.lua](https://github.com/EmirErtorer/ink-away.koplugin/blob/v4.4.0/_meta.lua)

## Mac commands after extracting R22 source-only ZIP

```sh
cd ~/Downloads/pw3-os-r22.1-plugin-integration/src/r21-filemanager-core
./HOST-VERIFY-R22.sh
./run-r22-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$PWD/results-r22.1-first-run"
cat results-r22.1-first-run/R22-EMULATION.log
cat results-r22.1-first-run/R22-RESULT-REVIEW.json
```

The script refuses existing results folders, audits genuine staged sources before the run and uses Docker `--network none --read-only --cap-drop ALL` with no device mounts. If any required native source or ARM proof fails, **stop and preserve the failure logs**; do not claim R22 verified.

## Holds

`NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.

This milestone does not authorize a flash, image deployment, physical framebuffer update, or hardware control. The v6 read-only device inventory and R22 host integration are separate evidence streams.
