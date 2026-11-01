# R39.1 — bounded synthetic input lifecycle for genuine ReaderUI activation

**2026-11-02 update: USER-SUPPLIED R39.1 ARM/QEMU PASS.** The independent unchanged R25 control returned `R25_REAL_EVENT_LOOP_ARM_PASS`. Genuine `FileManager:openFile` opened the original two-page PDF, scheduled ReaderUI through the real `nextTick` coroutine, and an actual `ReaderUI.instance` was verified. The two synthetic Input lifecycle hooks were reached on their success path; a synthetic Close led to clean genuine UIManager shutdown and distinct R39 strict reviewer `R39_READERUI_FIRST_ACTIVATION_ARM_PASS`. R39.1 has 51/51 host tests PASS. **No page change, FileManager return, physical render, global migration, boot or file removal was verified.**

## User-side R39.1 ARM evidence

The local output reports `R39_READERUI_FIRST_ACTIVATION_ARM_GATE_PASS` and `R39_READERUI_FIRST_ACTIVATION_ARM_PASS` with independent original R25 reviewer PASS. In the guest log, the genuine FileManager opens `/tmp/r25-ko-home/library/r39-original-two-pages.pdf`, the real ReaderUI initializes and prints:

```text
R39_ORIGINAL_TWO_PAGE_PDF_COPIED_TO_TEMP
R39_GENUINE_FILEMANAGER_OPENFILE_READERUI_SCHEDULED
R39_1_GENUINE_READERUI_INPUT_INHIBIT_REQUESTED_SYNTHETIC_ONLY
R39_1_GENUINE_READERUI_INPUT_RELEASE_REQUESTED_SYNTHETIC_ONLY
R39_REAL_READERUI_INSTANCE_AND_TWO_PAGE_PDF_OPENED
R39_REAL_UIMANAGER_LOOP_AFTER_READERUI_NEXTTICK
R39_SYNTHETIC_CLOSE_SENT_TO_READERUI
R39_REAL_READER_SHUTDOWN_COMPLETED
R39_REAL_READER_EXIT_BOUNDARY_PASS
R39_READERUI_FIRST_ACTIVATION_ARM_GATE_PASS
```

The strict R39 reviewer marks `genuine_filemanager_openfile_scheduled_readerui`, `genuine_readerui_instance_created`, `genuine_two_page_pdf_open_verified`, `genuine_readerui_input_lifecycle_calls_verified`, `readerui_closed_through_synthetic_event` and `independent_r25_baseline_control_pass` true. It explicitly leaves `page_navigation_verified`, `returned_to_filemanager_verified`, `physical_render_verified`, `real_pw3_init`, `global_startup_migrations_executed`, `complete_dependency_closure_proven` false, with `NOT_BOOTABLE`. The original R39.0 failure remains preserved separately. This successful ReaderUI initialization is stronger than R34 import, but still does not establish page navigation.

## Confirmed original R39.0 failure

The genuine ReaderUI async coroutine was reached after `R39_ORIGINAL_TWO_PAGE_PDF_COPIED_TO_TEMP` and `R39_GENUINE_FILEMANAGER_OPENFILE_READERUI_SCHEDULED`. In `frontend/apps/reader/readerui.lua` at line 120, it calls `Input:inhibitInput(true)`, missing from the **R17 synthetic input instance**. Its exception recovery calls `Input:inhibitInputUntil(0.2)` at line 730, also missing. The R39 reviewer correctly returned **FAIL**, without a real ReaderUI instance or page evidence. The separate original R25 baseline remained PASS.

Upstream `Generic:setIgnoreInput`, `Generic:notifyBookState`, and the pre-existing memory-screen `setWindowTitle` already exist; no substitute implementations of these were added.

## Scoped R39.1 correction

The forked R39 guard adds precisely two methods to `expected_input=Device.input` **after** the original Generic initialization contract: `inhibitInput(true)` and `inhibitInputUntil(0.2)`. Both require the exact synthetic instance and pinned `frontend/apps/reader/readerui.lua` source provenance.

- `inhibitInput(true)` is allowed only from genuine `ReaderUI:init` line 120, only once and after original FileManager startup.
- `inhibitInputUntil(0.2)` is allowed only once after the inhibit and only from ReaderUI line 533 (normal successful initialization) or 730/922 (real coroutine error recovery). **The new strict R39.1 reviewer only accepts the successful line 533 path**; recovery markers or any coroutine exception cause FAIL.
- Both calls update synthetic bookkeeping only; never open `/dev/input`, touch a physical e-ink screen, alter network/firmware/boot state or synthesize a ReaderUI instance.
- Original `R39_REAL_READERUI_INSTANCE_AND_TWO_PAGE_PDF_OPENED`, genuine ReaderPaging and UIManager event-loop/exit assertions remain required. The R39 reviewer now also requires ordered `R39_1_GENUINE_READERUI_INPUT_INHIBIT_REQUESTED_SYNTHETIC_ONLY` and `R39_1_GENUINE_READERUI_INPUT_RELEASE_REQUESTED_SYNTHETIC_ONLY` markers. It rejects a failed ReaderUI coroutine or missing original R25 control.

**Release:** conversation attachment `pw3-os-r39.1-readerui-input-lifecycle-fix.zip`, SHA-256 **`19c59fb14770b271295805ad0988aca7e7494f9bff553eef2705af6429a31398`**. ZIP integrity, 12 internal SHA-256 payloads, Lua syntax (three files), Python/shell syntax all PASS. **51/51 host tests PASS** (35 previous + 16 new source/reviewer regressions). User-side ARM/QEMU **not run**.

## Mac reproduction — fresh result directory only

```sh
cd ~/Downloads
unzip pw3-os-r39.1-readerui-input-lifecycle-fix.zip
cd pw3-os-r39.1-readerui-input-lifecycle-fix
python3 -m unittest discover -s tests -v

./run-r39-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json" \
  "$PWD" \
  "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run"

cat "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-R25-BASELINE-CONTROL.json"
tail -n 180 "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-REVIEW.json"
```

**Target only if actual new ARM/QEMU run passes all guards:** `R39_READERUI_FIRST_ACTIVATION_ARM_PASS` and `genuine_readerui_input_lifecycle_calls_verified=true`. Original R39.0 failure and separate R25 results must remain untouched. If a different interface fails next, keep its first exception and source details; no synthetic method or path exceptions should be added without inspection.

R39.1 still has **no page-turn or return-to-FileManager proof** and has not audited all production document sidecar persistence (R38.2 was a separate synthetic migration roundtrip). The 976 unobserved staged regular files stay `UNKNOWN_HOLD`; no new rootfs or firmware is created.

**Immutable holds:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.

References: [R39.0 actual failure](R39-0-READERUI-ACTIVATION-TRIAL.md), [R39 full two-page plan](R39-READERUI-TWO-PAGE-EVENT-CONTRACT.md), [R38.2 reconciliation](R38-2-1-GATE-MARKER-REPAIR.md).
