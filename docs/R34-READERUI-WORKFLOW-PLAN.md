# R34 — guarded genuine ReaderUI document workflow (design / preflight only)

**2026-11-02 status:** User-reported `R33_PDF_EPUB_OFFSCREEN_ARM_PASS` on corrected R33.1. PDF MuPDF and EPUB CREngine memory rendering, R32 Ink Away persistence and R25.3 event-loop/shutdown all passed on isolated offline ARM/QEMU. **R34 is a proposal only: no runner, host suite, ARM result, or boot artifact has been created.**

## Important difference from R33

R33 exercised genuine `DocumentRegistry:openDocument` and native offscreen document renderers directly while keeping FileManager as the UIManager widget. It did **not** prove `FileManager:openFile` → `ReaderUI:showReader` → ReaderUI initialization/page navigation/close. The R33 strict reviewer explicitly reports `full_reader_ui_document_open_verified=false`.

Pinned KOReader `v2026.07.2` sources:

- [`frontend/apps/filemanager/filemanager.lua`](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/filemanager/filemanager.lua): `FileManager:openFile()` calls `ReaderUI:showReader(file, provider, ...)` for document providers.
- [`frontend/apps/reader/readerui.lua`](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/reader/readerui.lua): `showReader()` queues a `showReaderCoroutine` through `UIManager:nextTick`, then `doShowReader()` constructs the real ReaderUI instance. Its `ReaderUI:init()` calls `SettingsMigration:migrateSettings(self.doc_settings)`, and uses input-inhibit, `Device:setIgnoreInput`, book-state and screen title APIs.
- [`frontend/document/documentregistry.lua`](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/document/documentregistry.lua): owns genuine PDF/EPUB document-engine lifecycle and refcounting.

## Required safety preflight before an executable R34 test

1. **Migration boundary:** Earlier R25/R32/R33 tests deliberately skipped migrations. ReaderUI invokes per-document settings migration in `ReaderUI:init()`. Audit the implementation and ensure it cannot access or mutate real existing user settings. An R34 run may invoke only explicitly audited, temporary per-document settings paths or else must fail/hold. Do not silently bypass migrations while still claiming unmodified full ReaderUI initialization.
2. **Synthetic device API contract:** enumerate every `Screen`, `Device`, `Input`, time/rotation/notification call reached in the real ReaderUI path. Only memory-backed instance methods may be added; never expose `/dev`, `/sys`, real e-ink refresh, battery, wireless, or persistent host paths.
3. **Event scheduler and teardown:** verify an authentic UIManager `nextTick` ReaderUI coroutine enters the reader stack, opens an original PDF/EPUB from `/tmp`, performs a deterministic synthetic page action, closes the ReaderUI and safely restores FileManager or exits through its actual application path. Do not call ReaderUI methods as stubs or directly assert their outputs.
4. **Testing and evidence:** preserve the verified R33.1/R32/R25 sources and strict reviewer logs. Create a **separate** R34 fail-closed reviewer and new results path, with ordered proof markers for genuine ReaderUI open, page draw, navigation, close, and recovered UIManager lifecycle. A test failure is evidence of a missing adapter or migration incompatibility, not authorization to disable checks.
5. **Trace coverage:** run a fresh QEMU guest-path trace on R33/R34 workflows and reconcile with R26–R31 baseline, retaining private paths locally and all unobserved objects as UNKNOWN_HOLD. Do not build a smaller rootfs solely from R25 startup trace.

## What R34 cannot claim until independently verified

No full ReaderUI document-open PASS is yet established. No screen pixel quality, physical PW3 framebuffer/EPDC, Kindle touch/keyboard event devices, charging/suspend/frontlight, genuine firmware boot, stock OS replacement, complete dependency closure, or safe file removal has been proven.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.