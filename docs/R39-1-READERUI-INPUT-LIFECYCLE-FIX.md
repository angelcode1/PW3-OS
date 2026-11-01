# R39.1 — bounded synthetic input lifecycle for genuine ReaderUI activation

**2026-11-02 status: 51/51 host tests PASS; user-side R39.1 ARM/QEMU PENDING.** The original R39.0 user's independent R25.3 control returned **PASS**, but first ReaderUI activation trial returned **FAIL**. This source-only R39.1 retry changes only the **forked R39 synthetic Input lifecycle adapter**, the distinct R39 reviewer and SHA-pinned source manifest. No original staged KOReader source, native engine, two-page PDF fixture or pinned R25.3 control has been changed.

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
