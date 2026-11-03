# R40.4.3.3 — proposed genuine InkAwayView input/save/return scenario contract

**Research-only plan, 2026-11-03 • NOT_EXECUTED_HOLD • NOT_BOOTABLE.**

R40.4.3.2 is now independently reproduced from uploaded private QEMU trace (388 syscalls, 198 path operations, 1 confined decoded write-open, 1 confined decoded rename, zero decoded unlink). It proves only the original staged **model and storage** chain. Its 18 distinct regular stage opens were all observed in earlier PDF/FileManager traces; the observed-open union remains 347.

## New coverage required before a guest executable is approved

1. **Source-pin the real staged KOReader/Ink Away UI boundary.** Reconcile the staged Ink Away `main.lua` `openCanvas` callback, `ink/view.lua` initialization/teardown, `ink/view/input.lua` input handling, `ink/view/stroke.lua` stroke finalization, `ink/view/document.lua` save hook, and the genuine KOReader `ui/uimanager.lua`, event and InputContainer interfaces. Historical staged source, not current upstream, controls API shape. Missing callbacks or ambiguous event ownership are a HOLD rather than silently substituting method calls.
2. **Trace the real widget lifecycle:** FileManager is live; Ink Away plugin owns the menu callback; `openCanvas` genuinely adds one `inkaway_view` widget to UIManager's window stack; a synthetic input event traverses the expected view input path; stroke finalizes through its real view methods; committed project is written to disposable HOME, reopened and validated; UIManager closes the view and returns to the existing FileManager; plugin unload and clean process exit are confirmed. Merely calling `Canvas:startStroke` directly must FAIL this newer reviewer.
3. **Enforce scratch writes before running.** The staged `Storage.writeAtomic` has a fallback destination removal. Docker must keep rootfs and release readonly, network disabled, caps dropped, no device access, no host-home mounts, and all writes (including failed rename/unlink) in a new isolated tmpfs synthetic HOME. Include hostile-path tests for `io.open`, `os.rename`, `os.remove`, `io.popen`, `os.execute`, and reject unknown or pathless mutation syscalls. Incomplete QEMU Linux-user trace decoding and unverified FFI paths preclude blanket safety claims.
4. **Independent strict reviewer:** require exact ordered genuine view/pen/commit/save/load/close markers, source-bound traces, guest zero exit and no blocked device or stage mutations. A visible marker alone is insufficient. Compute new scenario regular stage opens and compare against prior 347 **only after** a genuine new traced run; absence of new opens does not mean unused files can be deleted.
5. Keep EPUB/text, fallback font/locale, canvas exporting, physical Kindle, full Alpine boot, all 976 old UNKNOWN_HOLD, all 1,101 unobserved regular stages and future optional puzzle package on existing HOLDs.

The **next artifact to build** is a staged-source-bound UI event/ownership verifier using read-only stage inspection. Its source preflight must PASS before generating or running another QEMU guest. This document does NOT authorize an ARM run or claim new InkAwayView coverage.

**Immutable:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`.
