# R32 — genuine Ink Away stroke/save/reload during synthetic R25 lifecycle

**2026-11-01:** **R32 genuine Ink Away stroke/save/project-reload within real reader.lua lifecycle ARM/QEMU PASS (user-supplied log and both reviewers)**. R25.3 verified synthetic application lifecycle and R31 conditional CWD audit also PASS. The R32 host suite passed 23 tests. No physical Kindle access, independent boot or EPUB/PDF rendering has been proven.

## User-supplied R32 ARM/QEMU PASS — 2026-11-01

The user ran `run-r32-docker.sh` and provided the complete emulation log plus independent strict R25 and R32 reviewer JSON. The log established:

```text
R24_REAL_FILEMANAGER_SHOWFILES
R24_INKAWAY_INSTANCE_OWNED_BY_FILEMANAGER
R32_GENUINE_INKAWAY_MENU_CANVAS_OPENED
R32_GENUINE_INKAWAY_STROKE_SAVED_TO_TEMP
R32_GENUINE_INKAWAY_PROJECT_RELOADED
R25_REAL_UIMANAGER_EVENT_LOOP_REACHED
R25_SYNTHETIC_CLOSE_EVENT_DELIVERED
R25_REAL_GENERIC_EXIT_SYNTHETIC_ONLY
R25_REAL_READER_SHUTDOWN_COMPLETED
R25_REAL_READER_EXIT_BOUNDARY_PASS
R32_INKAWAY_PERSISTENCE_R25_LIFECYCLE_BOUNDARY_PASS
R25_REAL_EVENT_LOOP_ARM_GATE_PASS
R32_INKAWAY_PERSISTENCE_ARM_GATE_PASS
R25_REAL_EVENT_LOOP_ARM_PASS
R32_INKAWAY_PERSISTENCE_ARM_PASS
```

R25 fresh reviewer verdict `R25_REAL_EVENT_LOOP_ARM_PASS`: real reader entry, FileManager, Ink Away-only plugin, UIManager loop and normal exit all `true`. R32 reviewer verdict `R32_INKAWAY_PERSISTENCE_ARM_PASS`: `genuine_inkaway_menu_canvas_verified=true`, `genuine_inkaway_synthetic_stroke_saved_to_temp=true`, `genuine_inkaway_project_reload_verified=true`, `genuine_uimanager_event_loop_executed=true`, `r25_replay_verified=true`.

R32 marked `epub_pdf_rendering_verified=false`, `complete_dependency_closure_proven=false`, `migrations_executed=false`, `real_pw3_init=false`, and every device/firmware/boot/removal authorization `false`; hold `NOT_BOOTABLE`. The successfully reloaded *project data parser* is not proof that the user visibly reopened the canvas window. The image-builder `sha256:e245...` printed in the console is not a release archive SHA.

**Next step:** separate offline-document workload probes, tested on **synthetically authored, non-copyright documents**, to exercise PDF/EPUB engines and in-memory rendering; no physical display writes. Do not treat the R32 PASS as if either document format were verified.

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
