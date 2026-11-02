# R39.3.3 — user-supplied ARM/QEMU evidence verified (2026-11-02)

**Status: user-side ARM/QEMU PASS, with two separate strict reviewers and an independently rerun original R25.3 baseline PASS.** This is a synthetic-memory-screen application test, not a physical Kindle test.

The user's archive `R39.3.3-ARM-EVIDENCE.zip` contained the fresh original R25 review, pinned source preflight, emulation log, original strict R39.3 review and separate R39.3.3 sentinel review. The ZIP integrity check passed, and the two reviews agreed with the logged lifecycle.

Observed gate results:

```text
R25_REAL_EVENT_LOOP_ARM_GATE_PASS
R25_REAL_EVENT_LOOP_ARM_PASS
R39_3_HOME_RETURN_ARM_GATE_PASS
R39_3_READERUI_HOME_FILEMANAGER_RETURN_ARM_PASS
R39_3_3_HOME_ENGINE_SENTINEL_ARM_PASS
```

The genuine FileManager opened the original two-page PDF, completed page-1/page-2 MuPDF scroll rendering, delivered `GotoPage(2)` and Home through the original UIManager, released the ReaderUI instance and registry document, constructed the returned genuine FileManager, delivered its final Close, and finished ordinary Generic teardown.

The captured engine state was:

```text
raw_engine_nil=true
inherited_engine_false=true
registry_refs=none
doc_is_open=false
reader_instance_nil=true
reader_document_nil=true
```

Upstream `PdfDocument` class defines `_document=false`; `Document:close()` sets the **instance** field to nil, causing ordinary inherited lookup to return false. The original strict R39.3 failure at `saved_pdf._document==nil` was therefore a false-negative assertion. The R39.3.3 guard corrects its own read-only check to `rawget(doc,'_document')==nil` and also enforces the inherited sentinel and empty registry; production KOReader was not modified.

The actual previous R39.3 and R39.3.1 strict-review FAILs and later source-only R39.3.2 diagnosis stay historical and must not be overwritten. Original R25.3 baseline and R39.2.4 page-turn proofs remain distinct.

Source release `pw3-os-r39.3.3-home-engine-sentinel-arm-trial.zip` was distributed through the research session; the repository documents results, not a firmware image. The exact user-side sentinel reviewer JSON SHA-256 was `0495144ebea105d337ea0bcf0b7009bcb679b3dcaafaa22f2ed3a48753f1dbb6`.

**Holds:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. The 976 staged `UNKNOWN_HOLD` files remain retained; physical PW3 display, real hardware initialization, complete dependency closure, global startup migration and boot remain unverified.
