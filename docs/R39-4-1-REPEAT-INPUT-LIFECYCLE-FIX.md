# R39.4.1 — second ReaderUI synthetic Input lifecycle correction

**2026-11-02 status: host-tested source release, 311/311 Python tests PASS, ARM/QEMU pending; NOT_BOOTABLE.** This milestone follows the real R39.4 ARM FAIL, which remains historical and unchanged in the original user's report.

## Observed regression

The first document lifecycle and Home→FileManager return succeeded in the original R39.4 user-side ARM trace. The returned genuine FileManager then opened the same disposable two-page PDF again and scheduled genuine ReaderUI initialization. The experimental `r394/loop_guard.lua` mistakenly required `stats.filemanager==1` on every `Input:inhibitInput(true)` invocation. On the second open, `stats.filemanager==2`, correctly tracking the second genuine FileManager, and the synthetic guard aborted before a second ReaderUI was established. A follow-up synthetic exception-recovery release also failed. Original strict reviewer: `FAIL`; independent original R25 control: `R25_REAL_EVENT_LOOP_ARM_PASS`.

## Narrow corrected contract

Only the forked `r394/loop_guard.lua` and related source pin/reviewer files change; the original `r39/`, independent R25, production KOReader and physical device remain untouched.

`Input:inhibitInput(true)` is permitted **only** from the original source-pinned genuine `ReaderUI:init` line 120 and in exactly one of these bounded phases:

- Initial reader: cycle 1, FileManager count 1, event count 0, no Home, zero prior initialization lifecycles.
- Reopened reader: cycle 2, FileManager count 2, event count 2, first Home successfully returned, exactly one prior Input lifecycle, first ReaderUI/document retained only as read-only observers, first document closed with raw PDF engine slot nil and inherited false sentinel, and genuine FileManager singleton absent after its own `openFile` schedules ReaderUI.

Both phases require the original expected synthetic input object, clean per-cycle counters and no existing input-inhibition flag. `inhibitInputUntil(0.2)` must match the active phase; genuine line 533 remains the only acceptable success path, while error recovery at lines 730/922 retains strict failure markers. The independent strict R39.4 reviewer now also requires the positive `r3941_repeat_input_lifecycle_fix_pinned` source-preflight field. Reuse of old first-only source or mismatched reviewer is rejected by SHA-256 pins.

No relaxation to Home-close verification, registry zero, distinct ReaderUI/doc objects, actual MuPDF scroll draw, two genuine FileManager returns, four UIManager-dispatched events, maximum eight input polls, final Close, networkless container, or original independent R25 baseline.

## Host verification and artifact

- **311/311 host Python tests PASS** (291 original R39.4 host checks and 20 new R39.4.1).
- Python compileall, shell syntax and four Lua 5.4 syntax-only loads PASS.
- All 50 internal payload SHA-256 manifest entries and ZIP CRC PASS.
- Release: `pw3-os-r39.4.1-repeat-input-lifecycle-arm-trial.zip`, SHA-256 `2633fc3692cd86be4fc2207a81bdb86b7f4922d549cc8ac37151fc2376f8d562`.
- New experimental guard SHA-256: `ad5256d494cc64931dd903d82288aba92dffd1ff67b7b905fc4415978616c402`.
- New dedicated strict reviewer SHA-256: `b2d7a44f1acedeb6ec9899074e91bb0f4d3a4fed63b15d0816ff9d7b99d51e57`.
- Original failed R39.4 guard SHA-256: `9cd738d0e2130936460f62a21991b596709b2ac736d96fff8dc3e5aaec690c5d`.

The full source release is a separate conversation ZIP; this repository documents the host-tested revision but does **not** contain a bootable or device-flashable artifact. The archive's `README-R39.4.1.md` includes the exact nine-argument `run-r394-docker.sh` command using a new results directory. The first R39.4 failure is preserved separately and must not be overwritten.

Only a fresh guest run that emits `R25_REAL_EVENT_LOOP_ARM_PASS`, `R39_4_REOPEN_ARM_GATE_PASS` and `R39_4_SAME_SESSION_REOPEN_ARM_PASS` after both reviewers pass can establish this lifecycle. Until then, ARM/QEMU **PENDING**.

**Holds:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Physical PW3 display, hardware initialization, global startup migrations, independent boot, full dependency closure and 976 `UNKNOWN_HOLD` files remain unverified.

## Subsequent R39.4.1 real ARM/QEMU result (2026-11-02)

The user's `R39.4.1-ARM-EVIDENCE.zip` (SHA-256 `2d75d2acfb4f0666539ef84b1a5fa060e7a84229d74e3fd55740ef0d908c538c`) passed ZIP CRC and independently verified the unmodified R25 control (`R25_REAL_EVENT_LOOP_ARM_PASS`) and source preflight (`R39_4_PINNED_SOURCES_PASS` with `r3941_repeat_input_lifecycle_fix_pinned=true`). The original R39.4.1 strict reviewer returned `FAIL` and the experimental gate emitted `R39_4_REOPEN_ARM_GATE_FAIL (exit=1)`.

The genuine first PDF cycle and first Home→FileManager completed. The returned FileManager opened the same PDF, and a **distinct second ReaderUI successfully ran the previously failing two Input lifecycle calls**. The second original MuPDF scroll draw returned on **page 1**. A second real UIManager Home was dispatched. The new second-Home snapshot reported `raw_engine_nil=true`, inherited engine sentinel `false`, `registry_refs=none`, released ReaderUI and distinct second PDF. The failure moved to the experimental post-`stock_show` assertion `R39.4 second FileManager not active` (line 370); no `R39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY` or final FileManager Close marker was emitted.

The failed predicate is one or more of the second returned FileManager chooser/path, UIManager top widget, or denied-operation count. **None is individually identified by this log.** Do not assume a production bug or waive the gate. R39.4.2 adds a diagnostic-only read-only snapshot at that precise point, preserving the same strict reviewer and test holds. See [R39.4.2](R39-4-2-SECOND-FILEMANAGER-STATE-DIAGNOSTIC.md).
