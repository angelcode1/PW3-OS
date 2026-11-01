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

Source-only `pw3-os-r23-reader-startup-preflight.zip` is supplied separately in the conversation; its staged KOReader binaries are **not** embedded. ZIP SHA-256: `e7d48e55f34ca71d47156a2206d082bf977bba5de441e85aab668708d1786626` (81 internal file digests verified). The source contracts were also checked against the eight pinned upstream KOReader v2026.07.2 files. It contains the unchanged R22.1 sources, `audit_r23.py`, and five host tests.

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

## R23 source preflight: user-reported PASS, 2026-11-01

The user executed the R23 source audit against their retained R13 stage and provided the JSON verdict:

```text
R23_SOURCE_PREFLIGHT_PASS
R23_ARM_STARTUP_PENDING; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NOT_BOOTABLE
```

The JSON maps 35 staged source files to SHA-256 digests and required startup contracts. Its `r22_arm_verified=false`, `plugin_execution_verified=false`, and `real_reader_lua_executed=false` fields are deliberately **source-audit-scoped**, not a contradiction of the separately supplied successful R22.1 ARM run.

### R23.1 early-bootstrap candidate

Source-only archive: `pw3-os-r23.1-reader-bootstrap.zip`, delivered separately in the conversation.

- Archive SHA-256: `e4685fd5a64d62a4ac48431f69253666987fdbbbce1fa7bb84018a4c73756f0d`; 90 internal payload-file hashes verified.
- Local regressions: 32 R21 + 10 R22.1 + 5 R23 + 7 R23.1 = **54 PASS**. Two new Lua files also passed local syntax checks.
- First ARM/QEMU runtime probe now packaged, **not executed or ARM-verified here**.
- Runs the unmodified staged `reader.lua` using synthetic PW3 (not stock Kindle device selector) and a temporary KO_HOME. It uses genuine `LuaSettings:open()` and `Generic:init()` with memory-backed screen, and attempts the genuine `CanvasContext:init()` before an intentional migration boundary stop.
- Explicit holds prevent userpatch script execution, application directory version-log writes, and migration execution; the probe must fail closed if a source, permission, dependency, IO guard or startup assertion is incompatible. The full reader event loop and normal app shutdown are **not tested** by R23.1.
- The fail-closed reviewer can report only `R23_EARLY_BOOTSTRAP_ARM_PASS` for this limited boundary, with `r23_full_arm_startup_verified=false`, and must never emit `R23_ARM_READER_STARTUP_PASS`.

Commands after extracting the new archive:

```sh
cd ~/Downloads/pw3-os-r23.1-reader-bootstrap/src/r21-filemanager-core
./HOST-VERIFY-R22.sh
python3 -m unittest discover -s tests_r23 -v
python3 -m unittest discover -s tests_r23_1 -v
./run-r23-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$PWD/results-r23.1-first-run"
cat results-r23.1-first-run/R23-EARLY-EMULATION.log
cat results-r23.1-first-run/R23-EARLY-RESULT-REVIEW.json
```

The raw staged runtime, proprietary firmware materials and device captures must remain local. The repository documents this experiment but does **not** contain the full R23.1 source archive.

## R23.1 ARM failure and R23.2 correction — 2026-11-01

The user ran R23.1 in their offline Docker/QEMU environment and reported:

```text
R23_REAL_READER_LUA_ENTER
R23_REAL_SETUPKOENV_IMPORTED
frontend/luadefaults.lua:50: Failed reading defaults.lua
R23_EARLY_BOOTSTRAP_ARM_GATE_FAIL (exit=1)
```

The fail-closed JSON reviewer verdict was `FAIL`; there was **no** `R23_REAL_GENERIC_INIT_SYNTHETIC_ONLY` or completed premigration marker. Docker's legacy-builder deprecation warning and the printed `sha256:98e3...` image identifier are unrelated to this failure.

**Cause:** KOReader's genuine `frontend/luadefaults.lua` loads the stock `defaults.lua` with `pcall(dofile, "defaults.lua")`. R23.1's Lua guard refused all `dofile` calls except its intentional migration stop, so it also blocked the required read-only defaults load. `LuaSettings:open()` and `LuaDefaults:open()` additionally probe optional temporary settings via `pcall(dofile, path)`, including missing-file fallbacks. These must not count as security-policy violations.

**R23.2 host-tested correction** (ARM rerun pending):

- Allow exactly `defaults.lua` from the pinned read-only staged KOReader working directory, checking its table return and `DHINTCOUNT==1`, with one-time marker `R23_REAL_DEFAULTS_LOADED_READ_ONLY`.
- Also allow only four optional paths inside the temporary `KO_HOME`: `defaults.custom.lua`, `defaults.custom.lua.old`, `settings.reader.lua`, `settings.reader.lua.old`. A missing file returns the ordinary native error, which genuine KOReader code handles via `pcall`.
- Continue rejecting every other `dofile`, including user scripts and `frontend/ui/data/onetime_migration.lua` execution. The intended migration hold and genuine `reader.lua` entrypoint are unchanged; update the ordered reviewer so it rejects a missing defaults marker.
- Preserve the R21/R22 fixtures and all earlier source-audit contracts. All **59 host regression tests passed** (32 R21, 10 R22, 5 R23, 7 R23.1, 5 R23.2), plus new Lua syntax checks.
- Candidate source-only ZIP `pw3-os-r23.2-reader-bootstrap.zip`, SHA-256 `bf92cd20cb6a15e5138e7c536393c41789933b9ab30cb603401159044263a304`; 94 archive entries verified. This ZIP is provided in the conversation rather than publicly committed.
- Exact correction: [R23.2 defaults allowlist patch](../patches/r23.2-defaults-read-allowlist.patch).

Run from the newly extracted R23.2 package with the existing local R13 stage:

```sh
cd ~/Downloads/pw3-os-r23.2-reader-bootstrap/src/r21-filemanager-core
./HOST-VERIFY-R22.sh
python3 -m unittest discover -s tests_r23 -v
python3 -m unittest discover -s tests_r23_1 -v
python3 -m unittest discover -s tests_r23_2 -v
./run-r23-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$PWD/results-r23.2-first-run"
cat results-r23.2-first-run/R23-EARLY-EMULATION.log
cat results-r23.2-first-run/R23-EARLY-RESULT-REVIEW.json
```

An R23.2 ARM result remains **unknown**. If it passes, its only authorized milestone is `R23_EARLY_BOOTSTRAP_ARM_PASS`, with `r23_full_arm_startup_verified=false`, and **not** proof of FileManager startup, migrations, real-device access, independent boot or firmware operation.

## Remaining unproven boundaries

Native Kindle `Device:init()`, full driver ioctl/display updates, actual evdev touch events, battery/frontlight/suspend, stock Upstart service replacement, independent boot/recovery, image deployment, and cold boot.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. No hardware control or firmware changes are authorized.
