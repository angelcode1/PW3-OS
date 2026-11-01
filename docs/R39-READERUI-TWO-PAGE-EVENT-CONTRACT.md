# R39 — genuine ReaderUI transition and two-page navigation contract

**Status (2026-11-02): DESIGN AND SOURCE CONTRACT ONLY.** No R39 runner, synthetic input adapter, host test suite, QEMU trace or device execution has been created or authorized yet. This document follows the verified user-side `R38_2_EXISTING_ARM_EVIDENCE_GATE_RECONCILED` result: 79/79 host tests PASS and an unchanged strict R38.2 review that passes after a single old-to-new marker correction **in memory only**. Original R38.2 strict reviewer stays FAIL, and no new ARM execution is claimed. All application tests remain synthetic and `NOT_BOOTABLE`.

## Why a separate R39 execution harness is required

The pinned R25.3 `loop_guard.lua` deliberately asserts **exactly one** synthetic input wait, returns one ordinary `Close` event, and requires FileManager to be on the UI stack. Its exit assertions require one wait, one event, finalized Ink Away and empty UI stack. The R38.2 sidecar scenario can complete before that wait, but **cannot honestly validate real ReaderUI opening and turning a page within R25's single-event invariant**. Do not modify R25's pinned guard or reuse its existing gate marker to certify a different event sequence.

Genuine upstream KOReader v2026.07.2 control path: `FileManager:openFile(file)` calls `ReaderUI:showReader(file, provider)`. The latter emits `ShowingReader` (the original FileManager closes), shows a status widget and schedules `doShowReader` using **`UIManager:nextTick`** and a coroutine. `doShowReader` creates `ReaderUI:new`, which invokes `DocSettings:open` and genuine per-book `SettingsMigration:migrateSettings`; it also touches synthetic input, screen/window title and book-state methods. Existing R34 only imported ReaderUI, and R38.2 only called per-book migration **outside a ReaderUI instance**. Both are useful preconditions, not ReaderUI execution proof.

## Proposed R39 stage-1 positive workload

1. Build a **new, original, deterministic, two-page PDF** from source with separate visibly different text on pages 1 and 2; independently validate two-page structure and record fixture hashes. Keep original R33 one-page PDF and EPUB unchanged, and copy the new fixture only into disposable `/tmp/r25-ko-home/library`. No user book is collected.
2. Begin in actual KOReader `reader.lua` with the same offline staged rootfs, memory-only screen, synthetic input and FileManager ownership. Replay the independently verified Ink Away persistence and PDF/EPUB engine checks only if compatible without weakening earlier gates.
3. From the genuine FileManager instance invoke its **real** `openFile(temp_two_page_pdf)`; require actual `ReaderUI:showReader` and `UIManager:nextTick` coroutine activation, with no direct invocation of `ReaderUI:doShowReader`, no replacement of ReaderUI methods and no fake ReaderUI object.
4. Require `ReaderUI.instance` actually exists, controls the synthetic widget stack, and holds the verified two-page PDF. Observe a genuine first-page render. Reject message/error dialogs masquerading as a ReaderUI instance.
5. Send a bounded **synthetic KOReader page-change event through the real event dispatcher**, not a direct assignment to `ReaderPaging.current_page`. Verify `ReaderPaging.current_page` changes from 1 to 2, plus a genuine page-render/dirty-state update. A one-page document cannot pass the turn gate.
6. Send a bounded real Home/return event through the UIManager/ReaderUI path. Require ReaderUI to close its original registry document reference, FileManager to reappear as the active instance, and remaining temporary sidecars/settings to stay under `/tmp`. Then deliver a final normal Close event, run genuine UIManager teardown and exit via the same immutable synthetic device adapter. The new event budget is **different** from R25's and must have a new reviewer.
7. Record a **fresh QEMU guest-path trace** of the new workflow. Keep raw paths and traces private; share aggregate deltas and hashes only. Recompare against R36's 472 positively opened staged regular files and 976 `UNKNOWN_HOLD` entries, without pruning.

## Required failure gates before any runnable release

- **ReaderUI call provenance:** assert real source functions with pinned R37 staged SHA256s; no stubbing of `FileManager:openFile`, `ReaderUI:showReader`, `ReaderUI:init`, `ReaderPaging:onGotoPage` or `UIManager:run`. A new input **adapter** is allowed only on the synthetic `Device.input` object, and must not impersonate the reader.
- **Document sidecars and migration:** keep real `DocSettings`, per-book `SettingsMigration:migrateSettings`, archive/history and metadata path writes inside disposable temp. Audit possible `os.remove` and legacy-candidate behavior. The narrow R38.2 one-file `dofile` exception is not a general permission to execute arbitrary sidecars; expand only after enumerating and pinning any newly necessary ephemeral metadata candidates. Prohibit symlinks and path traversal at relevant load/write locations.
- **Device method contract:** audit *every newly reached* `Input:inhibitInput`, `Device:setIgnoreInput`, `Device:notifyBookState`, `Screen:setWindowTitle`, refresh and page-paint method against the synthetic adapter; fail closed if an unrecognized kernel/hardware interface is reached. No physical `/dev`, `/sys`, network or Kindle access.
- **Event budget and state sequence:** new bounded positive order must be independently proven: real FileManager → scheduled showReader coroutine → real ReaderUI page 1 → **observed page 2** → real onHome/return to FileManager → normal final Close → genuine exit. Any duplicate event, unexpected coroutine error, timeout or early shutdown FAIL.
- **Independent controls:** run the pinned **unchanged R25/R32/R33/R34** baseline in a separate isolated execution and retain its original strict reviewers. Do not misleadingly require the original R25 single-Close reviewer to PASS *against the new R39 multi-event log*. Give R39 a separate strict reviewer, immutable source pins, failure regression tests, and a fresh output directory.
- **No pruning or boot:** stage rootfs remains read-only; no independent Alpine boot image, firmware changes or file deletion follows from this result.

## Concrete source anchors

- [FileManager `openFile` (v2026.07.2)](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/filemanager/filemanager.lua#L1614-L1637)
- [ReaderUI `showReader` (v2026.07.2)](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/reader/readerui.lua#L613-L674)
- [ReaderUI asynchronous coroutine, `doShowReader` (v2026.07.2)](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/reader/readerui.lua#L711-L792)
- [ReaderUI genuine `onHome` and teardown](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/reader/readerui.lua#L864-L933)
- [ReaderPaging `onGotoPage` and page state](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/reader/modules/readerpaging.lua#L1147-L1165)
- [Temporary DocSettings migration evidence](R38-2-1-GATE-MARKER-REPAIR.md)
- [R37 source SHA audit](R37-READERUI-BOUNDARY-PREFLIGHT.md)

**Nothing in R39 is yet ARM verified.** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.
