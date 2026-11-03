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


## Packaged R40.4.3.3 staged UI event source gate (2026-11-03)

A **read-only staged-source gate** is now implemented in the SHA-256 pinned standalone release `pw3-os-r40.4.3.3-ui-source-gate.zip` (ZIP SHA-256 `5eaf473613d5eb85bc1798eec7d32e71bdbe5c4e4ab3e24d2c0a5ef75001c867`; 13,382 bytes; six ZIP members, five member SHA-256 checks PASS). The Python host regression suite is **62/62 PASS**, including malformed Lua comments/strings, missing methods, wrong prior-review counters, symlinks, special sources, pre-existing outputs and private-data export guards. The complete runnable code, tests and exact Mac commands are in the versioned ZIP's `README-R40.4.3.3.md`; this GitHub directory records provenance and status, not the private stage contents.

The tool reuses the already pinned `R40.4.3.2` preflight, checks original release manifest and source, independently verifies the uploaded historical public review SHA, and rehashes all original 2,070 R26 stage entries on the user's Mac. It then **only reads six more historically staged KOReader UI source modules**: UIManager, Event, InputContainer, WidgetContainer, FileManager and PluginLoader. Exact staged paths/hashes/line positions stay in a private local JSON; only boolean method-name candidates and counts go into a public summary.

**Important:** Host tests PASS, **Mac stage gate still PENDING**, and a genuine new ARM/QEMU InkAwayView/input/save/return test **has not run**. If a local API differs, report `STAGED_UI_SOURCE_CONTRACT_INCOMPLETE_HOLD`; do not infer a replacement or use a mocked widget. Presence of method declarations is not proof of runtime event ownership, UI safety or dependency closure. Original 347 observed-open file union and 1,101 unobserved stage regular files unchanged. Continue preserving all 976 earlier UNKNOWN_HOLD records, optional puzzle hold, `NOT_BOOTABLE`, no pruning/hardware/firmware.


## User-side Mac staged-source audit (2026-11-03)

The user ran 62 host tests **PASS** and the original stage-bound source gate. Its reported verdict was `R40_4_3_3_UI_EVENT_SOURCE_CANDIDATES_OBSERVED_NOT_EXECUTED` and exact contract status `EXPECTED_UI_METHOD_NAMES_SEEN_STATICALLY_NOT_EXECUTED`. The six original staged KOReader sources were present with expected method declarations: UIManager show/close/sendEvent/isWidgetShown, Event:new, InputContainer onInput/onGesture, WidgetContainer handleEvent/propagateEvent, FileManager init/onClose, PluginLoader create/stop/get-instance. The gate rechecked 2,070 R26 entries including 1,448 SHA-256 regular-file hashes, 335 symlinks and 287 directory types. Private paths/hashes remain local. **No new ARM guest, input event, menu callback, widget or save was executed**, and no dependency closure or pruning is authorized.

R40.4.3.4 is separately packaged as a **new view-show-and-close experimental ARM/QEMU run**; it reuses the original FileManager guard with one independently pinned targeted insertion and a new strict reviewer. It is *not* a full InputContainer/pen/stroke/save scenario, and its new guest execution is pending.
