# R39.3.1 — bounded Home-close and DocumentRegistry reference-state diagnosis

**2026-11-02 USER ARM/QEMU DIAGNOSTIC CAPTURED:** `R39_3_1_HOME_CLOSE_STATE_DIAGNOSTIC_CAPTURED`, while the original unchanged R25 control PASS and R39.3.1 strict Home-return reviewer FAIL remain separately preserved. Exactly one original predicate failed: the old **inherited** `saved_pdf._document==nil` check; the reader singleton and reader document were gone, `is_open=false`, and registry refcount was `none`. Source examination confirms `PdfDocument:extend{_document=false}` and the base final close's `self._document=nil` make the inherited ordinary lookup return `false` even after the **raw instance** field was cleared. **[R39.3.2](R39-3-2-PDF-RAW-ENGINE-CLOSE-CONTRACT.md)** corrects the synthetic guard using `rawget`, while requiring empty DocumentRegistry, genuine Home and final FileManager Close. R39.3.2 **285 host tests PASS; ARM/QEMU pending**. The old R39.3.1 strict FAIL is not reinterpreted as a PASS.

## User-confirmed snapshot and source-derived root cause

The user ran the R39.3.1 guest and separate offline analyzer. The analyzer returned `R39_3_1_HOME_CLOSE_STATE_DIAGNOSTIC_CAPTURED` with `failed_original_predicates=["saved_pdf_engine_not_cleared"]`, `page_navigation_verified_in_this_run=true`, `returned_to_filemanager_verified=false` and `original_r39_3_strict_verdict_not_modified=true`. Its snapshot reported `reader_instance_nil=true`, `reader_document_nil=true`, `doc_is_open=false`, `engine_nil=false`, `registry_refs=none`, `filemanager_instance_nil=true`.

Upstream pinned KOReader v2026.07.2 `frontend/document/pdfdocument.lua` explicitly declares **`_document = false` in the PdfDocument subclass prototype**. Base `frontend/document/document.lua` final-reference `Document:close()` sets `self.is_open=false`, closes the original engine and assigns `self._document=nil`. Because Lua resolves `doc._document` via `__index` when the instance's raw slot is absent, the closed object may expose the **inherited `false`**; the old test erroneously required `doc._document==nil`. An independent executable Lua host repro confirms this behavior. The source-correct test must require `rawget(doc,'_document')==nil`, the inherited PdfDocument sentinel `rawget(getmetatable(doc),'_document')==false`, `is_open=false`, and actual `DocumentRegistry:getReferenceCount(file)==nil`. See [R39.3.2](R39-3-2-PDF-RAW-ENGINE-CLOSE-CONTRACT.md).

**The old diagnostic's `engine_nil=false` remains valid for its old lookup expression, but does not prove a retained native engine.** The diagnostic itself did not verify the raw slot, so historic strict Home-return FAIL remains unmodified and actual Home→FileManager completion stays unverified until the new ARM run.
## Diagnostic-only change, not a closure bypass

This separate source release changes only the **experimental synthetic** `r39/loop_guard.lua`, its new source pin, and adds `r39/analyze_home_close.py`. Real staged KOReader, original R25 control, R39.2.4 PDF scroll draw observer, the three-event budget, source paths and the **unchanged strict R39.3 reviewer** remain intact.

Immediately before the existing combined assertion inside genuine `ReaderUI:showFileManager` → synthetic wrapper around `FileManager:showFiles`, one bounded, read-only snapshot prints `R39_3_1_HOME_CLOSE_STATE` with:
- `reader_instance_nil` (genuine active ReaderUI singleton gone?)
- `reader_document_nil` (previous ReaderUI document field released?)
- `document_present`, `doc_is_open`, `engine_nil` (original PDF wrapper/engine state)
- `registry_refs` (actual `DocumentRegistry:getReferenceCount` for the synthetic test PDF, or `none`/`unavailable`)
- `filemanager_instance_nil` (before real returned FileManager constructor)

No sidecar data or user files are read for this diagnostic. The snapshot never releases a reference, directly closes a document, calls or replaces a rendering operation, bypasses Home, changes any registry count, or substitutes the real returned FileManager. The original closure assertion is still evaluated as before; a mismatch still fails the guest and strict reviewer.

The new **separate** read-only analyzer accepts exactly one snapshot after evidence of genuine page-1/page-2 scroll drawings and real Home dispatch; requires fresh unchanged original R25 strict reviewer PASS, old strict R39.3 reviewer FAIL and the specific closure error. It outputs only `R39_3_1_HOME_CLOSE_STATE_DIAGNOSTIC_CAPTURED` with `diagnostic_only=true`, `returned_to_filemanager_verified=false`, `root_cause_determined=false`. It rejects missing, duplicated, malformed, misordered or contradictory evidence, and never marks R39.3 Home return PASS. If the original strict R39.3 outcome unexpectedly passes, the diagnostic analyzer intentionally does not label it a failure.

**Why refcount matters:** Upstream [`Document:close`](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/document/document.lua#L104-L125) uses [`DocumentRegistry:closeDocument`](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/document/documentregistry.lua#L260-L280). When refs remain, closing one reference does not necessarily set `is_open=false` or clear `_document`. A positive refcount needs separate evidence identifying its owner. It cannot be assumed a legitimate reference or a leak from this log alone.

## Release artifact and host verification

Conversation artifact `pw3-os-r39.3.1-home-close-state-diagnostic.zip`; SHA-256 **`c2e800e7561012970437d7f1c0e845f5ebf91c2f2ef89da04ee67f02d56b7dc8`**. ZIP CRC and **29 SHA-256 payload entries verified**. **235/235 host regression tests PASS**, including missing/duplicate Home state, bad refcount, misordered page-turn, retained reader reference, invalid old reviewer, and immutable safety holds. All Python files compile; POSIX shell syntax and three Lua syntax-only parses PASS. The stage remains private; user-side ARM has not run for R39.3.1.

- New experimental guard SHA-256: `a8c4edcc7171f865ef414ae981c56fbe965e970c0a83e3b8784ddf20d0602a96`
- New diagnostic analyzer SHA-256: `795c79ff93faace34ac0d89ccadd943157c7ee04b3373b4ffc26b12759121244`
- Original R25.3 guard remains `7f5881a9c79da22c626bd0451a580fd13eae8af96330de811a13042cd98ed2b8`.
- Existing R39.3 strict `review_r39.py` unchanged.

## Mac commands (fresh results; original R39.3 output untouched)

```sh
cd ~/Downloads
unzip pw3-os-r39.3.1-home-close-state-diagnostic.zip
cd pw3-os-r39.3.1-home-close-state-diagnostic
python3 -m unittest discover -s tests -v

./run-r39-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json" \
  "$PWD" \
  "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.2.4-scroll-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.3.1-home-first-run"

cat "$HOME/Downloads/pw3-os-r39.3.1-home-first-run/R39-R25-BASELINE-CONTROL.json"
tail -n 180 "$HOME/Downloads/pw3-os-r39.3.1-home-first-run/R39-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r39.3.1-home-first-run/R39-REVIEW.json"

python3 r39/analyze_home_close.py \
  --log "$HOME/Downloads/pw3-os-r39.3.1-home-first-run/R39-EMULATION.log" \
  --baseline "$HOME/Downloads/pw3-os-r39.3.1-home-first-run/R39-R25-BASELINE-CONTROL.json" \
  --strict-review "$HOME/Downloads/pw3-os-r39.3.1-home-first-run/R39-REVIEW.json" \
  --out "$HOME/Downloads/R39.3.1-HOME-CLOSE-DIAGNOSTIC.json"
cat "$HOME/Downloads/R39.3.1-HOME-CLOSE-DIAGNOSTIC.json"
```

Use the individual booleans and `registry_refs` to choose the next narrow correction. Never replace a failed strict R39.3 reviewer with the diagnostic verdict. The 976 staged regular files lacking successful-open evidence remain `UNKNOWN_HOLD`; **NO_DEVICE_ACCESS, NO_FIRMWARE_WRITES, NO_HARDWARE_ACTIONS, NO_BOOT, NOT_BOOTABLE, NO_PRUNING.**
