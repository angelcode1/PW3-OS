# R39.3.2 — source-pinned raw PDF engine closure and genuine FileManager return

**2026-11-02 status: SOURCE-ONLY HOST PASS (285/285 tests); ARM/QEMU PENDING.** User's R39.3.1 ARM diagnostic returned `R39_3_1_HOME_CLOSE_STATE_DIAGNOSTIC_CAPTURED`, while the historical strict Home reviewer remained FAIL and unchanged independent original R25 control PASS. This R39.3.2 trial is a new release, not retrospective relabeling.

## Root cause grounded in the user's trace and pinned KOReader

The user's snapshot showed ReaderUI instance gone, saved ReaderUI document field nil, saved PDF `is_open=false`, DocumentRegistry `registry_refs=none`, but `engine_nil=false` under a **normal property lookup**. A separate source audit of KOReader v2026.07.2 shows `PdfDocument` declares `_document=false` **on its inherited prototype**, whereas final-reference `Document:close()` assigns the actual instance's `_document=nil` after closing the native engine. Lua's `__index` fallback then resolves the closed instance's `doc._document` to prototype `false`; `doc._document==nil` fails although `rawget(doc,'_document')==nil`. The raw-field/inheritance behavior was reproduced in executable Lua host tests, including live-engine negative cases. The previous R39.3 and R39.3.1 strict FAILs remain unchanged and Home→FileManager still needs a fresh guest test.

## Minimal fix and independent positive contract

The R39.3.2 fork replaces only the *experimental synthetic R39* assertions that incorrectly checked normal `doc._document==nil`. Its `r3932_genuine_pdf_closed()` requires: actual document instance table; `is_open==false`; PdfDocument prototype `rawget(getmetatable(doc),'_document')==false`; **raw instance** `rawget(doc,'_document')==nil`; loaded original DocumentRegistry with `getReferenceCount(exact_temp_pdf)==nil`. The existing separate constraints that ReaderUI singleton and saved reader field are nil remain; the actual `Home` event, genuine `ReaderUI:showFileManager` → `FileManager:showFiles`, real FileManager restored on temporary library, final FileManager `Close`, empty UI stack, plugin cleanup, Generic exit and app exit all remain required.

The strict new reviewer mandates exactly one `R39_3_2_PDF_RAW_ENGINE_CLEARED_AND_REGISTRY_EMPTY` marker **after** real Home and **before** FileManager restoration, and the fresh source-preflight attestation. The old diagnostic marker, which may continue to display `engine_nil=false` for the inherited lookup, is retained only for comparison; it cannot grant PASS. The original PDF fixture, page 1→2 genuine scroll drawing, event budget, R25 immutable control and R39.2.4 previous strict page-turn PASS are preserved. No production ReaderUI, PdfDocument, Document, FileManager, UIManager or registry methods are replaced, and no document is closed manually.

## Additional source provenance

The user-side preflight now requires exact **Git blob IDs** for these three staged KOReader v2026.07.2 files, with underlying source semantic anchors checked:

- `frontend/document/document.lua` — `7c5f9b1a314651fb65ed2b54995569a306407c4b`
- `frontend/document/pdfdocument.lua` — `62cd04f09f73e3c20ab91ed270a94e79fe707cd1`
- `frontend/document/documentregistry.lua` — `aaac8eef2fe9c4463e722c7547582599fcc844c4`

Any mismatch must **FAIL CLOSED**; do not override the staged source check. Original six R37 staged source SHA256 pins, ReaderView upstream blob, original R25 guard, original two-page PDF, and previous R39.1/R39.2.4 evidence remain pinned. This additional preflight is not a claim that this assistant executed the user's private ARM stage.

## Host release and execution

Conversation ZIP: `pw3-os-r39.3.2-pdf-raw-engine-close-contract.zip`. SHA-256 **`1719ca80a916585247d7652294dba1388b36e17048a561e48e8fa9572951175a`**. ZIP CRC and 31 file SHA256 entries PASS. **285/285 host tests PASS** (235 inherited + 50 new), including executable Lua tests that reject live raw engine, still-open PDF, any present registry ref, wrong prototype, and missing registry, along with ordered-marker/reviewer and source-attestation failures. Python compilation, POSIX shell syntax and three Lua source syntax parses PASS. No R39.3.2 ARM execution performed here.

New forked R39 guard SHA256: `29e7af2ce01e9d10f1cf53957ec6a9e15dc1a059d6b7c3c3bdff77879410f65b`.
New strict R39.3.2 reviewer SHA256: `09734b0345eb188a4a6b49354ed834e302315d3657e44cc75365b2c4d75613f0`.
Original R25.3 event guard remains `7f5881a9c79da22c626bd0451a580fd13eae8af96330de811a13042cd98ed2b8`.

### Mac command — separate new results directory

```sh
cd ~/Downloads
unzip pw3-os-r39.3.2-pdf-raw-engine-close-contract.zip
cd pw3-os-r39.3.2-pdf-raw-engine-close-contract
python3 -m unittest discover -s tests -v

./run-r39-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json" \
  "$PWD" \
  "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.2.4-scroll-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.3.2-home-first-run"

cat "$HOME/Downloads/pw3-os-r39.3.2-home-first-run/R39-R25-BASELINE-CONTROL.json"
tail -n 200 "$HOME/Downloads/pw3-os-r39.3.2-home-first-run/R39-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r39.3.2-home-first-run/R39-REVIEW.json"
```

**New target if actual user-side guest run succeeds:** `R39_3_HOME_RETURN_ARM_GATE_PASS` and strict `R39_3_READERUI_HOME_FILEMANAGER_RETURN_ARM_PASS`, with real PDF close, registry empty, FileManager returned, final FileManager Close, genuine app shutdown and independent unchanged R25 control PASS. All earlier failed R39.3/3.1 reviewer results remain preserved. If an unrelated Home return or metadata operation fails, keep it as a separate FAIL and do not weaken the reviewer.

**Immutable holds:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT_ACTIONS; NOT_BOOTABLE; NO_PRUNING`. Application Docker run remains networkless with read-only stage and source, no devices and disposable `/tmp`. Global migrations skipped. All 976 unobserved regular files from R36 remain `UNKNOWN_HOLD`; no independent rootfs boot or physical Kindle screen result is claimed.

References: [R39.3.1 user-confirmed diagnostic](R39-3-1-HOME-CLOSE-STATE-DIAGNOSTIC.md), [R39.3 historical strict FAIL](R39-3-READERUI-HOME-FILEMANAGER-RETURN.md), [R39.2.4 page-turn ARM PASS](R39-2-4-SCROLL-RENDER-OBSERVER.md), and upstream [PdfDocument prototype](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/document/pdfdocument.lua#L14-L22) and [Document final close](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/document/document.lua#L104-L125).