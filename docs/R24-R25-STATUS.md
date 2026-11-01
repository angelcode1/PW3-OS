# PW3-OS R24–R25: genuine reader.lua FileManager and event-loop candidates

**Status (2026-11-01): R23.4 ARM/QEMU PASS (user-provided log); R24 ARM NOT RUN; R25 ARM NOT RUN.** These are **source-only, host-tested candidates**, not an ARM application-startup claim. Neither R24 nor R25 authorizes physical Kindle access, firmware writes, boot, or a bootable rootfs.

## R24: real FileManager startup gate

The R24 test runs the **unmodified staged** KOReader `v2026.07.2` `reader.lua` under ARM/QEMU using the existing R17 synthetic PW3 device, memory-backed 1072×1448 screen, and temporary `KO_HOME`. It skips but **does not execute** `frontend/ui/data/onetime_migration.lua`, prevents userpatch execution and version-log changes, and retains the existing R23.4 Bidi/real UIManager input handshake.

The new stage exercises the real `FileManager:showFiles(directory)` branch with the `directory` argument pointing to fresh `/tmp/r24-ko-home/library`; its original `PluginLoader:loadPlugins()` and `createPluginInstance()` must run. **Only Ink Away 4.4.0 is permitted for discovery**, with pinned main/_meta Lua files, and real FileManager-owned plugin instance, FileChooser path, and UIManager window-stack ownership must all be confirmed. The test intercepts `UIManager:run()` at the entrypoint and stops deliberately: **R24 does not run the event loop or perform shutdown**.

Expected user-side verdict *if and only if real ARM execution passes*: `R24_REAL_FILEMANAGER_ARM_PASS`. Fail-closed reviewer refuses missing, duplicated, unordered, denied or old/falsely promoted markers.

## R25: bounded genuine UIManager event loop and reader shutdown

R25 builds on R24. It leaves genuine KOReader `UIManager:run()` untouched and supplies one **synthetic** `Close` event from the isolated R17 input's `waitEvent` callback. It verifies the actual FileManager/PluginLoader lifecycle and attempts a genuine `Generic:exit()` with inert memory-only `screen:close()`, `setHWNightmode()`, and `input:teardown()`. The final `os.exit` is intercepted to report a clean shutdown boundary without exiting the host harness unexpectedly.

This is a **test proposal, not demonstrated runtime functionality**. Real FileManager init, refresh/event delivery, or close may expose additional compatibility gaps. Do not loosen checks or claim R25 PASS without the ARM log and reviewer JSON.

Even a future R25 PASS would not mean full stock `reader.lua` behavior has been validated: migrations are *skipped*, only one plugin is discoverable, UI input and screen are synthetic, and no actual Kindle hardware or independent boot exists.

## Verification and artifact provenance

Available local host regression suites: **94/94 PASS** (32 R21 + 10 R22.1 + 5 R23 + 7 R23.1 + 5 R23.2 + 9 R23.3 + 7 R23.4 + 10 R24 + 9 R25). New R24/R25 Lua files passed a Lua 5.3 syntax-only check; Python compilation, POSIX shell syntax, ZIP integrity, and complete SHA-256 manifest verification passed. This **does not substitute for ARM/QEMU execution**.

The full historical R23.4 plus R24/R25 source-only handoff is supplied separately in ChatGPT. No proprietary library, raw device diagnostic capture, stock firmware, or boot image is committed to the public repository.

- `pw3-os-r24-filemanager-startup.zip` — SHA-256 `59b8299de56e16a685e41eebd84fcbdc9a090cd95ddbdb2bb47a0dad83f8353c` (122 payload hashes).
- `pw3-os-r25-eventloop-shutdown.zip` — SHA-256 `5852ba0a07a50644f5bbafd6fda283d561be82c808986c70b5e9c6875092a350` (129 payload hashes). **Cumulative package contains R24 and R25 runners.**

## Reproduce on Mac in strict sequence

After extracting the R25 ZIP:

```sh
cd ~/Downloads/pw3-os-r25-eventloop-shutdown/src/r21-filemanager-core
./run-r24-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$PWD/results-r24-first-run"
cat results-r24-first-run/R24-EMULATION.log
cat results-r24-first-run/R24-RESULT-REVIEW.json
```

**Stop if R24 fails.** Only if the R24 reviewer verdict is exactly `R24_REAL_FILEMANAGER_ARM_PASS`, run:

```sh
./run-r25-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$PWD/results-r25-first-run"
cat results-r25-first-run/R25-EMULATION.log
cat results-r25-first-run/R25-RESULT-REVIEW.json
```

The Docker **runtime** uses `--network none --read-only --cap-drop ALL`, `no-new-privileges`, no device mounts, and writable temporary storage. Initial Docker image **builds** may require ordinary package download unless layers are already cached. Source audit fails on changed staged contracts, and prior results directories are never overwritten.

**Scope hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. The proposed minimal Alpine rootfs must eventually be built from a licensed dependency allowlist; not by deleting unclassified files from stock firmware. See [minimal userspace roadmap](PW3-MINIMAL-USERSPACE-ROADMAP.md).
