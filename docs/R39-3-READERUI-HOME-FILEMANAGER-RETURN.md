# R39.3 — genuine ReaderUI Home → FileManager return

**2026-11-02 USER ARM/QEMU FAIL**. Fresh unchanged independent R25 control `R25_REAL_EVENT_LOOP_ARM_PASS`, genuine original two-page PDF scrolling and `GotoPage(2)` with successful page-1/page-2 MuPDF scroll draws PASS. The new `Home` event was dispatched, but the R39.3 experimental `FileManager:showFiles` wrapper failed **before invoking the genuine returned FileManager constructor** at its combined condition `R39.3 ReaderUI document not genuinely closed before FM return`. Exact failed predicate not logged; strict reviewer remains FAIL and return-to-FileManager is not verified. **[R39.3.1](R39-3-1-HOME-CLOSE-STATE-DIAGNOSTIC.md)** is a single read-only pre-assertion snapshot/release diagnostic (235 host tests PASS; user ARM pending), not an asserted fix.

## Actual R39.3 user-side failure

The user ran R39.3 with the original unchanged R25 control and received:

```text
R25_REAL_EVENT_LOOP_ARM_PASS
R39_2_4_GENUINE_SCROLL_PAGE1_DRAW_RETURNED
R39_2_GOTOPAGE2_SENT_THROUGH_REAL_UIMANAGER_INPUT
R39_2_4_GENUINE_SCROLL_PAGE2_DRAW_RETURNED
R39_2_READER_PAGE2_DRAWN_AND_CURRENT_PAGE_VERIFIED
R39_3_HOME_SENT_THROUGH_REAL_UIMANAGER_INPUT
/r39/loop_guard.lua:322: R39.3 ReaderUI document not genuinely closed before FM return
R39_3_HOME_RETURN_ARM_GATE_FAIL (exit=1)
```

The actual strict R39.3 `R39-REVIEW.json` returned `FAIL` for missing `R39_3_GENUINE_FILEMANAGER_RETURNED_AFTER_HOME`. The error occurs *inside the experimental wrapper*, immediately before calling the real `FileManager:showFiles` constructor. The original assertion combined four checks: `ReaderUI.instance==nil`, saved ReaderUI's `document==nil`, saved PDF `is_open==false`, and saved PDF `_document==nil`. It did not print which check failed. Real KOReader `Document:close` is reference counted; an outstanding registry reference can keep an engine live even after the ReaderUI reference is released. That possibility is **not yet proven or exonerated** by the log. The original failed results must remain unchanged; [R39.3.1](R39-3-1-HOME-CLOSE-STATE-DIAGNOSTIC.md) captures the exact states and registry reference count before the same strict assertion.

## Confirmed foundation: R39.2.4 user-side PASS

The user supplied a guest trace with genuine `FileManager:openFile` → scheduled ReaderUI, original two-page PDF, completed original ReaderView PDF **scroll** draws on pages 1 and 2, `GotoPage(2)` sent through actual UIManager, actual ReaderPaging and ReaderView page-2 state, ordinary Close and clean Generic teardown. R39.2.4 reviewer confirms `page_navigation_verified=true`, `genuine_pdf_scroll_draw_completion_verified=true`, and independently rerun original R25 control PASS. `returned_to_filemanager_verified=false`, physical render, boot, global migrations, and complete dependency closure remained explicitly unverified.

## New R39.3 workload

R39.3 forks only the separately labeled offline synthetic R39.2.4 test, **not** original R25 or staged KOReader. It retains the original two-page PDF and genuine render observer, but sends **three actual UIManager-dispatched events** instead of the earlier two:

1. `GotoPage(2)` after first genuine PDF scroll draw; require second selected page and a completed genuine PDF scroll draw.
2. `Home` after verified page 2; require genuine `ReaderUI:onHome` to call `ReaderUI:onClose`, `Document:close` and `ReaderUI:showFileManager` (exact staged source/caller pin at line 594). The test retains the previously active original ReaderUI and PDF document as *observation-only* references. Before accepting the new FileManager, require `ReaderUI.instance=nil`, the saved reader's `document=nil`, and PDF document `is_open=false` and `_document=nil`. Require a **new actual FileManager instance** controlling the UIManager stack and pointing to the same disposable `/tmp/r25-ko-home/library`.
3. Only after successful Home return and document-release checks, `Close` the **returned FileManager** through the ordinary UIManager event path. Verify genuine FileManager/plugin cleanup, an empty widget stack, generic input/screen/device teardown and normal intercepted `reader.lua` exit.

The test allows the prior **one genuine `UIManager:setDirty` retry per PDF page**, never direct drawing, and imposes a maximum **five input polls, three dispatched events**. No ReaderUI, ReaderPaging, ReaderView, Document, FileManager or UIManager production method is replaced. It cannot be marked PASS if Home is not dispatched, document refs are retained, FM does not reappear or cleanup is incomplete.

**Path provenance refinement:** Genuine `util.splitFilePathName(file)` returns the parent directory with a trailing `/` when `ReaderUI:showFileManager` calls `FileManager:showFiles`; that stock method then normalizes the directory via `ffiUtil.realpath`. R39.3 requires exactly this trailing-slash handoff at the genuine source-pinned call and the expected normalized temporary library path after FileManager construction. Both are verified in a new host regression; no unbounded path normalization is accepted.\n\n**Temporary metadata containment:** KOReader's new DocSettings object does *not* have a guaranteed `.file` member; the source-correct path is `doc_sidecar_dir .. '/' .. sidecar_filename`. R39.3 checks this derived path is under disposable `/tmp/r25-ko-home` and retains existing hard denials of writes outside that home. This does **not** independently validate the final sidecar bytes, and no broad file-access trace is claimed.

## Separate source pins, reviewers and tests

- `r39/review_r39_2_4.py` is the preserved original strict R39.2.4 reviewer, SHA-256 `2b514a92d02e48610d931a85496237744647ebdfe42586909bf1629ddd08dae9`; inherited regression tests still exercise it without conflating historical contracts.
- The **new** `r39/review_r39.py` checks the strict order: both genuine page draws, `GotoPage(2)`, new Home event, genuine document release, new FileManager, final Close and original Generic exit. It requires positive previous user-side R39.1 activation and R39.2.4 page-turn review JSON, R38.2.1 reconciliation and a **fresh independent original R25 baseline PASS**.
- `r39/check_inputs.py` SHA-pins new overlay and archived old reviewer, original stage source SHA256s and original R25 guard, six genuine KOReader sources, original two-page PDF SHA, ReaderView Git blob, and explicit `NOT_BOOTABLE` holds.
- **203/203 host tests PASS**, Python compileall, POSIX shell syntax and three Lua 5.4 syntax-only parses PASS. ZIP integrity and **26 internal payload SHA256 hashes verified**. These are **host tests only; no R39.3 ARM run has yet occurred**.

Conversation ZIP: `pw3-os-r39.3-home-filemanager-return.zip` SHA-256 **`9928454f2f3b0ae30d7ba97194e7125475b7ccaa785f42f6a24d433ee30acedc`**.

## Mac run (new output directory; old results untouched)

```sh
cd ~/Downloads
unzip pw3-os-r39.3-home-filemanager-return.zip
cd pw3-os-r39.3-home-filemanager-return
python3 -m unittest discover -s tests -v

./run-r39-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json" \
  "$PWD" \
  "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.2.4-scroll-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.3-home-first-run"

cat "$HOME/Downloads/pw3-os-r39.3-home-first-run/R39-R25-BASELINE-CONTROL.json"
tail -n 200 "$HOME/Downloads/pw3-os-r39.3-home-first-run/R39-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r39.3-home-first-run/R39-REVIEW.json"
```

**Target only if a real new offline user-side ARM/QEMU run passes:** `R39_3_HOME_RETURN_ARM_GATE_PASS` and `R39_3_READERUI_HOME_FILEMANAGER_RETURN_ARM_PASS`. A new failure is a useful fail-closed interface or cleanup observation; preserve it and do not relax the original R25 or R39.2.4 controls.

**Immutable holds:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. Application container remains networkless and read-only, with disposable `/tmp`, read-only stage/source mounts and no hardware mounts. All R36 `UNKNOWN_HOLD` staged files (976) remain retained; no pruning or boot authorization. Global startup migrations are skipped.

References: [R39.2.4 genuine page-turn PASS](R39-2-4-SCROLL-RENDER-OBSERVER.md), [full R39 contract](R39-READERUI-TWO-PAGE-EVENT-CONTRACT.md), [upstream ReaderUI:onHome](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/reader/readerui.lua#L927-L933) and [Document:close](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/document/document.lua#L104-L125).
