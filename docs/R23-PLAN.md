# R23 — genuine reader.lua startup boundary

**State, 2026-11-01:** R22.1 ARM/QEMU **PASS** in the user's supplied log and fail-closed JSON reviewer. R23 is **SOURCE PREFLIGHT ONLY; ARM STARTUP NOT RUN**. The user-reported R22.1 success is not a GitHub Actions ARM execution.

## Evidence inherited unchanged

- R21.5: actual KOReader FileManager/FileChooser start, in-memory painting and clean close (9 ARM probes, user-reported).
- R22.1: genuine KOReader `PluginLoader:loadPlugins()` and `createPluginInstance()`; Ink Away-only discovery, FileManager-owned instance; actual menu callback opens Ink Away; synthetic stroke, temporary save, return, genuine `FileManager:onClose()`; negative safety tests. Three ARM probes and result reviewer PASS, user-reported.
- Host regression: 32 original R21 tests + 10 R22.1 tests. New R23 preflight: five local unit tests PASSED.
- Read-only physical Kindle interface names: EPDC framebuffer, Cypress evdev, MAX77696 power/backlight, Lab126 Upstart. These are **not** tested by the R22 or R23 application probes.

## Pinned upstream entrypoint

Official KOReader `v2026.07.2` [`reader.lua`](https://github.com/koreader/koreader/blob/v2026.07.2/reader.lua) (Git blob `0316af75b82855cb5b74a0b0a08762c422cba08a`) is the missing genuine top-level application path.

Its order matters:

1. `require("setupkoenv")` configures module lookup, then `userpatch.applyPatches(...early*)` may execute scripts.
2. `DataStorage` / `luasettings` opens settings, may create device ID, and version state can be written.
3. `require("device")` selects and initializes a device; `CanvasContext:init(Device)` and one-time migrations follow.
4. `UIManager` loads; without a document, `FileManager:showFiles(directory)` enters the real application and `UIManager:run()` starts an event loop.
5. `Device:exit()`, before-exit userpatches, and `os.exit(reader_retval, true)` finish shutdown.

The first R23 runtime probe should use an explicit **synthetic temporary directory argument**, never a real user-storage path. It must invoke the unmodified staged `reader.lua` with the synthetic PW3 device and finite, deterministic synthetic UI event input, rather than faking the FileManager or replacing the upstream entrypoint.

## First deliverable: static source preflight

Source-only `pw3-os-r23-reader-startup-preflight.zip` is supplied separately in the conversation; its staged KOReader binaries are **not** embedded. It contains the unchanged R22.1 sources, `audit_r23.py`, and five host tests.

```sh
cd ~/Downloads/pw3-os-r23-reader-startup-preflight/src/r21-filemanager-core
python3 -m unittest discover -s tests_r23 -p 'test_*.py' -v
python3 audit_r23.py \
  --stage "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  --out "$PWD/results-r23-source-preflight"
cat results-r23-source-preflight/R23-SOURCE-PREFLIGHT.json
```

The source audit chains existing R17–R22 source gates. It reads only fixed staged application sources, checks markers and reader.lua startup order, produces hashes/contract counts in a new **local** results directory, and refuses missing/symlinked sources. A `R23_SOURCE_PREFLIGHT_PASS` result is **not** proof that `reader.lua` ran.

## Later ARM/QEMU experiment (not yet implemented or passed)

- Keep the real `reader.lua`, real settings structures, real FileManager, genuine PluginLoader and Ink Away 4.4.0. Reuse R17 synthetic device, in-memory screen/input and all existing R22 negative guards; use strictly temporary project storage.
- Disable user-supplied patch execution and reject unapproved extra plugin directories; block updater/network, Amazon LIPC, shell/exec, and anything outside temporary storage. One-time migrations and `Version:updateVersionLog()` must never write to mounted application or stock paths.
- Verify real `CanvasContext:init(Device)`, initialized FileManager, finite `UIManager:run()` exit after controlled synthetic event, settings flush, genuine `Device:exit()`, and proof of clean shutdown.
- Require explicit negative tests for startup side effects, symlink escapes, network/API calls, unallowed plugin loads, device and sysfs access, and file writes outside `/tmp`.
- Run only offline Docker/QEMU (`--network none --read-only --cap-drop ALL`, no device mounts), with a new output directory and fail-closed ordered reviewer. Preserve R21.5 and R22.1 results independently.
- Name future runtime marker `R23_ARM_READER_STARTUP_PASS` **only** if full startup plus teardown and safety checks actually pass. Do not infer this from static auditing.

## Remaining unproven boundaries

Native Kindle `Device:init()`, full driver ioctl/display updates, actual evdev touch events, battery/frontlight/suspend, stock Upstart service replacement, independent boot/recovery, image deployment, and cold boot.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. No hardware control or firmware changes are authorized.
