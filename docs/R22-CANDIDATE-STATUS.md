# R22 integration candidate — 2026-11-01

## Verification state

**Historical sequence:** R22.0 ARM/QEMU failed teardown (2026-11-01); R22.1 corrected the genuine FileManager close path and subsequently passed all ARM gates on the user's Mac. See the verified-result section below.

- First ARM run successfully reached: `R22_REAL_PLUGINLOADER_ONLY_INKAWAY`, `R22_REAL_PLUGIN_INSTANCE_OWNED_BY_FILEMANAGER`, and `R22_REAL_DISPATCHER_AND_MENU_REGISTRATION`.
- It then failed: `plugin_fixture_r22.lua:99: plugin instance retained after FM close`, `REAL_PLUGIN_LOAD FAIL (exit=1)`, and `R22_RESULT_REVIEW=FAIL`. The menu-canvas and negative-safety probes **were not executed** on that run.
- Root cause: the R22 fixture called `UIManager:close(fm)` rather than genuine `FileManager:onClose()`, which is responsible for `PluginLoader:finalize()`. The direct UI call bypassed normal plugin-registry cleanup.
- R22.1 calls `fm:onClose()`, asserts the genuine method source, and preserves plugin-registry, singleton, window-stack, flush, and safety postconditions. No direct manual finalization or weakened checks.
- R21.5 host regression unchanged: **32/32 PASS**; R22.1 host regression: **10/10 PASS** (new teardown test added).
- New source-only archive: `pw3-os-r22.1-plugin-integration.zip`, provided in the conversation. No firmware, captures, secrets, or proprietary runtimes committed.
- The exact fixture/source-audit/host-test diff is published at [`patches/r22.1-filemanager-close.patch`](../patches/r22.1-filemanager-close.patch). Apply against the original R22 candidate root only, or use the full corrected ZIP directly; do not mix source trees.
- **Independent ARM rerun not available here:** The user's retained R13 stage was used for their successful ARM/QEMU run; source-only artifacts do not include that stage.

## R22.1 ARM/QEMU result — user-supplied PASS, 2026-11-01

**R22.1 ARM/QEMU: PASS (user-supplied execution output and reviewer JSON).** This supersedes the earlier R22.0 failure and R22.1 rerun-pending status above. The earlier FAILED run remains documented as historical evidence.

The user reported from `results-r22.1-first-run`:

```text
REAL_PLUGIN_LOAD PASS
MENU_CANVAS_LIFECYCLE PASS
NEGATIVE_SAFETY PASS
R22_ARM_PLUGIN_INTEGRATION_PASS
NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NOT_BOOTABLE; ONLY_INKAWAY_PLUGIN; SYNTHETIC_UI_ONLY
R22_RESULT_REVIEW=PASS
```

Reviewer claims: `verdict=PASS`, `r22_arm_verified=true`, `genuine_inkaway_plugin_verified=true`; `boot_authorized=false`, `firmware_write_authorized=false`, `hardware_write_authorized=false`, `real_pw3_init=false`. This records the reported execution, not an independent rerun by a GitHub runner.

The ARM log confirms:
- Genuine Ink Away-only PluginLoader discovery, FileManager-owned instance, dispatcher/menu registration, and `R22_FILEMANAGER_CLEAN_CLOSE`.
- Canvas opened from the menu, memory-painted, handled synthetic UI gesture input, saved under temporary storage and returned to FileManager.
- Fail-closed Amazon-device, shell, and outside-temporary-storage denials; clean FileManager close.
- KOReader's `libkoreader-monolibtic.so` absence message and deprecated Ink Away metadata-name warning were nonfatal in this run.

The reported `sha256:102343eeb9f1621418e302ad9712f58c0d85a087e6348c5d11ff430f1985a3d0` has no explicit artifact type in this message; do not treat it as a verified source ZIP checksum or a released Git tree.

**Still not proven:** full `reader.lua` startup, real PW3 device init, real framebuffer/evdev operation, battery/frontlight control, suspend/resume, recovery, independent boot, and a bootable OS image. The full stage and raw output remain local.

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
