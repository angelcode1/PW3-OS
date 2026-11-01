# R32 — genuine Ink Away stroke/save/reload during synthetic R25 lifecycle

**2026-11-01:** User-side R25.3 real KOReader `reader.lua` → FileManager → Ink Away plugin ownership → UIManager run → synthetic Close → clean shutdown **ARM/QEMU PASS**. R31 conditional CWD provenance audit **user-side PASS** (7 conditional staged-directory candidates). **R32 is a source-only ARM/QEMU candidate; 23/23 local host tests PASS; no R32 ARM result has been reported.**

## Why R32, and what it actually tests

R26–R31 identified many files not directly opened in a *single* synthetic startup/shutdown scenario; this is not evidence they are removable. R32 therefore **adds an application workload** instead of drawing increasingly strong conclusions from the same trace.

The existing R22.1 plugin integration had already verified a genuine Ink Away v4.4.0 FileManager menu callback, real UIManager canvas window, synthetic stroke, project save and project data readback in an **independent** ARM/QEMU fixture. R32 exercises that integration in the **same actual staged `reader.lua`** lifecycle verified by R25.3:

1. Load the **unchanged pinned R25.3 `loop_guard.lua`** and its tight read-only stage, temporary settings, migration skip, Ink Away-only discovery and synthetic screen/input constraints. Do not edit the app/firmware/stage or override `UIManager:run()`.
2. After the genuine FileManager show-files method and plugin instance ownership checks, the R32 source-only overlay intercepts this synthetic FileManager method *on this one run* to call the genuine Ink Away menu callback.
3. Deliver memory-only `IaTouch`, `IaPan`, `IaPanRelease` UI events; require a nonempty canvas operation count; close the view with genuine UIManager; require nonempty saved project data **only** in `/tmp/r25-ko-home/`; invoke genuine `ink/project` data parser reload and check it contains saved operations. This is **not** a second canvas UI reopen, but a real project data reload.
4. Allow the original `reader.lua` → genuine `UIManager:run()` → synthetic Close → genuine `Generic:exit()` lifecycle to continue. Require a **fresh strict R25.3 reviewer PASS** and the **new R32 reviewer PASS** for the ordered additional markers.

The new candidate is **not** an EPUB or PDF renderer, and does not claim any NetSurf support. That is a separate R33+ scenario. The R32 runtime may expose additional unsupported synthetic interfaces and fail; this is an expected fail-closed outcome and must not be hidden.

## Source-only deliverable, host evidence

Download supplied in the conversation: `pw3-os-r32-inkaway-persistence.zip`, release SHA-256 **`75030b521eb00d399c4fd4531eb58068cb5dd93345b59c2e2888615aa3137a97`**. ZIP integrity PASS; eight payload SHA-256 checks PASS; 23/23 host tests PASS; Python/shell and both Lua files syntax checked. **No R32 ARM/QEMU execution here**, and no R13 stage, Kindle firmware, private path inventory or proprietary KOReader files in the archive.

The portable overlay requires the user's existing `pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core` source. It checks fixed SHA-256 pins for the six critical previously validated R25.3 source/reviewer/audit files, checks the successful previous R25.3 reviewer, re-runs five distinct source audits to a **brand-new output directory**, then builds the same existing R25.3 Dockerfile for an offline replay. Docker runtime uses `--network none`, `--read-only`, `--cap-drop ALL`, `--security-opt no-new-privileges`, one CPU, 768 MiB cap and `--tmpfs /tmp:rw,nosuid,nodev,size=160m` with read-only `/stage` and `/r32`. **No physical host or Kindle device mount.** Note the Docker *image build* may need external package repositories if uncached; runtime has no network.

## Mac reproduction

```sh
cd ~/Downloads
unzip pw3-os-r32-inkaway-persistence.zip
cd pw3-os-r32-inkaway-persistence
python3 -m unittest discover -s tests -v

./run-r32-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core/results-r25.3-first-run/R25.3-RESULT-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r32-inkaway-first-run"

tail -n 150 "$HOME/Downloads/pw3-os-r32-inkaway-first-run/R32-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r32-inkaway-first-run/R32-R25-RESULT-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r32-inkaway-first-run/R32-RESULT-REVIEW.json"
```

Expected R32-specific order only if genuine runtime succeeds:

```text
R32_GENUINE_INKAWAY_MENU_CANVAS_OPENED
R32_GENUINE_INKAWAY_STROKE_SAVED_TO_TEMP
R32_GENUINE_INKAWAY_PROJECT_RELOADED
R25_REAL_UIMANAGER_EVENT_LOOP_REACHED
R25_SYNTHETIC_CLOSE_EVENT_DELIVERED
R25_REAL_GENERIC_EXIT_SYNTHETIC_ONLY
R25_REAL_READER_SHUTDOWN_COMPLETED
R25_REAL_READER_EXIT_BOUNDARY_PASS
R32_INKAWAY_PERSISTENCE_R25_LIFECYCLE_BOUNDARY_PASS
R32_SYNTHETIC_INPUT_TEMP_STORAGE_ONLY; MIGRATIONS_SKIPPED; NOT_BOOTABLE
R25_REAL_EVENT_LOOP_ARM_GATE_PASS
R32_INKAWAY_PERSISTENCE_ARM_GATE_PASS
```

The final reviewer verdict would be `R32_INKAWAY_PERSISTENCE_ARM_PASS` **only after user-side ARM/QEMU evidence**; no success inferred from host unit tests. If either fresh R25 or R32 reviewer fails, report the error and preserve the unique output directory. The original R25.3 PASS stays established.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. Neither unobserved paths nor successful synthetic Ink Away saves authorize file removal, real e-ink IO or independent boot.
