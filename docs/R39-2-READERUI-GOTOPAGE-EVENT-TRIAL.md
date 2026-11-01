# R39.2 — genuine ReaderUI page 1 → page 2 event trial

**2026-11-02 status:** The user confirmed **R39.1 `R39_READERUI_FIRST_ACTIVATION_ARM_PASS`** on offline ARM/QEMU, with a separate unchanged R25 control `R25_REAL_EVENT_LOOP_ARM_PASS`. The genuine FileManager opened a SHA-pinned synthetic two-page PDF via `openFile()`, asynchronous `ReaderUI:showReader()` reached a real ReaderUI instance, and the two synthetic Input lifecycle methods were successfully exercised, followed by a clean Close/Generic shutdown. The user-provided R39.1 reviewer retains `page_navigation_verified=false`, `returned_to_filemanager_verified=false`, `physical_render_verified=false` and `NOT_BOOTABLE`.

**R39.2 USER ARM/QEMU FAIL** (historical result preserved): after independent unchanged R25 PASS, the original page-turn experiment reached genuine ReaderUI initialization and success-path synthetic Input release, then failed at `/r39/loop_guard.lua:422: R39.2 first page not genuinely drawn before input`. The new ReaderPaging event was **not delivered**, so page navigation was not verified. Source analysis shows `ReaderView.state.drawn` is assigned only for the non-paging/CRE branch, not genuine PDF pages. This was a test-instrumentation defect, not evidence of a failed PDF rendering. [R39.2.1](R39-2-1-GENUINE-PDF-DRAW-COMPLETION.md) uses a real post-return PDF draw observer instead; **90/90 host tests PASS, ARM pending**. The original R39.2 result stays FAIL.

## User-supplied failure and verified source explanation (2026-11-02)

The original R39.2 ARM execution passed `R39_PINNED_SOURCES_AND_TWO_PAGE_FIXTURE_PASS`, reproduced the independent original R25 `R25_REAL_EVENT_LOOP_ARM_PASS`, and reached `R39_ORIGINAL_TWO_PAGE_PDF_COPIED_TO_TEMP`, `R39_GENUINE_FILEMANAGER_OPENFILE_READERUI_SCHEDULED`, and both `R39_1_GENUINE_READERUI_INPUT_...SYNTHETIC_ONLY` success markers. Immediately before delivering its proposed page-turn event, the forked guard asserted `reader.view.state.drawn==true`; genuine PDF ReaderView had not set this flag. Trace:

```text
/r39/loop_guard.lua:422: R39.2 first page not genuinely drawn before input
R39_2_PAGE_TURN_ARM_GATE_FAIL (exit=1)
R39-REVIEW.json: verdict FAIL, missing R39_REAL_READERUI_INSTANCE_AND_TWO_PAGE_PDF_OPENED
```

Upstream KOReader v2026.07.2 `frontend/apps/reader/modules/readerview.lua` `ReaderView:paintTo` dispatches PDF pages through `self:drawSinglePage(bb,x,y)`, but sets `self.state.drawn=true` **only** in the non-paging branch, after `if self.ui.paging then ... else ...`. This is why the R39.2 PDF assertion was invalid. The log does not demonstrate whether a real PDF paint occurred; do not infer either success or failure. The historical R39.2 output and FAIL reviewer remain unchanged; see [R39.2.1](R39-2-1-GENUINE-PDF-DRAW-COMPLETION.md) for a narrowly instrumented retry.

## R39.2 changed scope

This release forks only the **separate R39.1 synthetic Input guard**, its R39 reviewer, preflight/checksum pins, and replay runner. No staged native KOReader code, original R25.3 single-Close test, PDF fixture, Ink Away plugin, stage/rootfs or firmware source is modified. R39.1 remains an independent prior ARM PASS.

The new synthetic `Input:waitEvent` may produce **exactly two** input events:
1. Only after genuine `FileManager:openFile` and ReaderUI's actual `UIManager:nextTick` coroutine, require a live genuine `ReaderUI.instance`, the exact two-page PDF, a true original `ReaderPaging:onGotoPage` method, topmost ReaderUI widget, and **page 1 selected** in both `reader.paging.current_page` and `reader.view.state.page` with `state.drawn==true`. Then return `Event:new('GotoPage',2)` to the **real UIManager's default input event dispatcher**. The overlay does not directly invoke the page handler or assign the page state.
2. On the **next real UIManager input poll**, after KOReader handles the event and the repaint, require the *same* real ReaderUI with **`paging.current_page==2`**, **`view.state.page==2`**, and **`view.state.drawn==true`**. Only then deliver the ordinary `Event:new('Close')` and require the normal genuine ReaderUI/UIManager/Generic shutdown.

The new R39.2 reviewer mandates all ordered markers, including `R39_2_READER_PAGE1_DRAWN_AND_CURRENT_PAGE_VERIFIED`, `R39_2_GOTOPAGE2_SENT_THROUGH_REAL_UIMANAGER_INPUT`, `R39_2_READER_PAGE2_DRAWN_AND_CURRENT_PAGE_VERIFIED`, and `R39_2_PAGE_TURN_ARM_GATE_PASS`, plus a new unchanged R25 control reviewer PASS and original user-provided R39.1 reviewer PASS. An unexpected page, document, caller, UI stack, extra event, migration path, coroutine exception or shutdown causes FAIL.

**Meaning of a future R39.2 PASS:** genuine **synthetic KOReader event-driven page 1→2 navigation** and **in-memory ReaderView drawn-state**, not verified physical framebuffer/pixel equality, touch/key event integration, Home → FileManager return, complete dependency closure, per-device initialization or independent boot.

## Host validation and source archive

Conversation artifact: `pw3-os-r39.2-event-page-turn.zip`, SHA-256 **`6980a56b3068b03f48fc00792d164beebb5d258ba0df9705d5d055c6358589ec`**. **71/71 host tests PASS** (includes the adjusted 51 R39.1 regression checks and 20 additional R39.2 checks), `sh -n` both shell files PASS, all Python files compile, **three Lua entrypoint/guard files syntax PASS**, original two-page fixture verified by `pdfinfo` as 2 pages, ZIP integrity PASS, 12 SHA-256 payloads verified.

Original R25 baseline source remains pinned at SHA `7f5881a9c79da22c626bd0451a580fd13eae8af96330de811a13042cd98ed2b8`. The R39.2 source guard is separately SHA-pinned at `ffb48558d4e50c04d9cc284afd545482bf81608a272f73fb31d47b043cf4ab53` and the two-page synthetic PDF stays `17f2bf493433c9664457dd51f0e3e31e2f67b88b0480f97a3ed9dc2ade7170db`. Six genuine staged source hashes are rechecked against R37. The runner also requires the original R38.2 existing ARM evidence reconciliation plus the newly supplied R39.1 reviewer PASS. Do not infer the Docker image digest `sha256:e245...` is this archive checksum.

## Mac reproduction (fresh R39.2 results, no overwrites)

```sh
cd ~/Downloads
unzip pw3-os-r39.2-event-page-turn.zip
cd pw3-os-r39.2-event-page-turn
python3 -m unittest discover -s tests -v

./run-r39-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json" \
  "$PWD" \
  "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.2-page-turn-first-run"

cat "$HOME/Downloads/pw3-os-r39.2-page-turn-first-run/R39-R25-BASELINE-CONTROL.json"
tail -n 180 "$HOME/Downloads/pw3-os-r39.2-page-turn-first-run/R39-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r39.2-page-turn-first-run/R39-REVIEW.json"
```

**Target only after user-side ARM/QEMU:** `R39_2_READERUI_PAGE_TURN_ARM_PASS` with `page_navigation_verified=true`, `page2_reader_view_drawn_verified=true`, `navigation_through_real_uimanager_input_verified=true`, and **`returned_to_filemanager_verified=false`**. If the trial cannot paint page 2, it must remain FAIL, rather than relaxing this new assertion. An eventual Home/return test must have its own separate event budget and reviewer.

## Safety boundary

The Docker *application* runs `--network none --read-only --cap-drop ALL --security-opt no-new-privileges`, with bounded memory/pids/CPU, ephemeral `/tmp`, read-only source and stage mounts, no device mounts and a fresh results-only write mount. The original R25 control runs independently; never apply its single-Close reviewer to R39.2's two-event experiment. Global startup migrations are skipped, and no physical touch, e-ink display, Kindle boot or firmware access occurs. The R36 catalog's 976 unobserved regular files remain `UNKNOWN_HOLD`; **no pruning**.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.

Related: [R39.1 user-side activation PASS](R39-1-READERUI-INPUT-LIFECYCLE-FIX.md), [R39 full workflow design](R39-READERUI-TWO-PAGE-EVENT-CONTRACT.md), [R38.2.1 reconciled per-book migration](R38-2-1-GATE-MARKER-REPAIR.md).
