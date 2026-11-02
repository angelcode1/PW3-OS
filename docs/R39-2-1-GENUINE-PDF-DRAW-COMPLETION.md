# R39.2.1 — genuine PDF draw-completion proof (not `state.drawn`)

**2026-11-02 update:** R39.2.1 **USER ARM/QEMU FAIL** at `/r39/loop_guard.lua:471: R39.2.1 first page must complete genuine MuPDF draw before input`, before any `GotoPage(2)` event; independently replayed original R25 control PASS and real ReaderUI initialization/input-release reached. The original R39.2.1 reviewer remains FAIL. No completed PDF paint call was observed before the first synthetic input poll; this alone does **not** establish a renderer fault or correct repaint scheduling. Source inspection also identified that the old reviewer ordered the `R39_REAL_READERUI_INSTANCE...` first-input marker before the first PDF draw marker, contrary to the possible real `UIManager:_repaint`→`Input:waitEvent` order. [R39.2.2](R39-2-2-BOUNDED-REPAINT-PROOF.md) uses one bounded real-UIManager `setDirty` retry per page and corrects reviewer ordering; **116/116 host tests PASS; ARM/QEMU pending**.

## Actual R39.2.1 user-side failure

The local log and fresh reviewer reported original R25 `R25_REAL_EVENT_LOOP_ARM_PASS`, then R39.2.1 `R39_2_PAGE_TURN_ARM_GATE_FAIL (exit=1)` and strict `FAIL` (missing `R39_REAL_READERUI_INSTANCE_AND_TWO_PAGE_PDF_OPENED`). Genuine FileManager two-page PDF open, ReaderUI asynchronous construction, `R39_1_GENUINE_READERUI_INPUT_INHIBIT_REQUESTED_SYNTHETIC_ONLY` and `R39_1_GENUINE_READERUI_INPUT_RELEASE_REQUESTED_SYNTHETIC_ONLY` had all occurred. The first-page draw counter remained zero when the guard's `Input:waitEvent` callback ran; no GotoPage event was dispatched.

Unlike the earlier R39.2 state flag problem, R39.2.1 waits for a genuine completed PDF draw. The available log does not show UIManager's dirty state, repaint queue or why no draw preceded that first input poll. An explicit bounded *genuine UIManager* repaint retry followed by the same draw counter is a legitimate test of the next boundary, not proof that repaint had occurred. The original strict review's draw/instance marker order would also reject a successful paint-before-first-input sequence and is addressed separately in [R39.2.2](R39-2-2-BOUNDED-REPAINT-PROOF.md). Preserve R39.2.1's FAIL.

## Proven R39.2 cause

The user-provided original R39.2 log reached genuine FileManager open, asynchronous ReaderUI initialization, first Input inhibit/release, then failed at `/r39/loop_guard.lua:422: R39.2 first page not genuinely drawn before input` before the GotoPage(2) event was delivered.

The original guard asserted `reader.view.state.drawn == true`. Upstream KOReader v2026.07.2 `frontend/apps/reader/modules/readerview.lua` uses `self:drawSinglePage(bb,x,y)` for PDFs inside the `if self.ui.paging then` branch, but assigns `self.state.drawn = true` **only under the alternative non-paging/CRE branch**. Thus this property is **not** a PDF rendering-completion flag. The R39.2 log does not prove whether PDF drawing took place.

## Targeted R39.2.1 correction

The R39.2.1 fork intercepts the genuine ReaderView module when imported and wraps **only** `drawSinglePage`. It confirms the original method comes from staged ReaderView, the call comes from the real `ReaderView:paintTo` at line 198, the original live `ReaderUI.instance` owns the verified two-page temporary PDF, the memory-backed buffer is nonnil, and ReaderPaging and ReaderView agree on the selected page. The wrapper invokes the original method *unchanged* and records a bounded page-specific paint count **only after it returns successfully**. There is no direct page-state assignment, no direct ReaderPaging invocation, no fake ReaderUI, and no substituted PDF renderer. Staged ReaderView's upstream v2026.07.2 Git blob is pinned as `3217d9d20ca3e593f44b465ef6322fb5e6058db5`, on top of the six original R37 SHA-256 source pins.

At the first real UIManager synthetic input poll, R39.2.1 requires page 1 selected by both genuine objects and at least one successful original PDF draw, with zero page 2 draws, then sends `Event:new('GotoPage',2)`. On the second poll, it requires page 2 selected by both and at least one **completed original PDF draw of page 2**, then sends ordinary Close. Normal genuine UIManager/Generic exit is required. The separate strict reviewer requires new ordered markers `R39_2_1_GENUINE_MUPDF_PAGE1_DRAW_COMPLETED` and `R39_2_1_GENUINE_MUPDF_PAGE2_DRAW_COMPLETED` around the real `GotoPage(2)` event. Invalid/missing/duplicate/out-of-order draw evidence, coroutine errors and all unapproved device/file operations remain FAIL.

The package retains the exact original two-page fixture, genuine KOReader, independent unchanged R25 control and previous R39.1 reviewer PASS, read-only stage/source mounts, networkless Docker runtime, and `NOT_BOOTABLE`. It does **not** test Home→FileManager return or physical e-ink pixel output.

## Host release and reproduction

Conversation ZIP: `pw3-os-r39.2.1-genuine-pdf-draw-proof.zip`, SHA-256 **`0025ab5bdaa1f9afb31685a75d2023bc805c4678308e63c4ccb480d8f93651e5`**, ZIP integrity PASS and **16 internal SHA-256 payload hashes verified**. **90/90 Python host tests PASS** including explicit missing, duplicate and misordered paint markers; Python and shell syntax PASS, three Lua parses PASS. No user-side R39.2.1 ARM result yet. The stage or source-pin check may fail if the staged ReaderView differs from exact upstream bytes; inspect, never waive the pin.

```sh
cd ~/Downloads
unzip pw3-os-r39.2.1-genuine-pdf-draw-proof.zip
cd pw3-os-r39.2.1-genuine-pdf-draw-proof
python3 -m unittest discover -s tests -v

./run-r39-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json" \
  "$PWD" \
  "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.2.1-page-turn-first-run"

cat "$HOME/Downloads/pw3-os-r39.2.1-page-turn-first-run/R39-R25-BASELINE-CONTROL.json"
tail -n 180 "$HOME/Downloads/pw3-os-r39.2.1-page-turn-first-run/R39-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r39.2.1-page-turn-first-run/R39-REVIEW.json"
```

**Target only if real guest run passes:** runner `R39_2_PAGE_TURN_ARM_GATE_PASS` and strict reviewer `R39_2_READERUI_PAGE_TURN_ARM_PASS`; positive `page_navigation_verified=true` and `genuine_pdf_draw_single_page_completion_verified=true`. This proves only synthetic page navigation and actual memory draw-call completion, **not framebuffer pixel fidelity, hardware input, ReaderUI Home, global migrations, dependency closure or independent boot**.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. R36's 976 unobserved regular files remain `UNKNOWN_HOLD`, no pruning.

See [original R39.2 FAIL](R39-2-READERUI-GOTOPAGE-EVENT-TRIAL.md), [R39.1 ARM PASS](R39-1-READERUI-INPUT-LIFECYCLE-FIX.md), [full R39 contract](R39-READERUI-TWO-PAGE-EVENT-CONTRACT.md).
