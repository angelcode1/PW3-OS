# R39.4.11 — user-verified repeat PDF lifecycle in offline ARM/QEMU

**2026-11-03: Application ARM milestone PASS. Independent boot NOT VERIFIED. NOT_BOOTABLE.**

## Evidence integrity

The user uploaded `R39.4.11-ARM-EVIDENCE.zip` SHA-256 `a4f97cf1f1d8348438756de1a1e757b8b21094f8fd9ef662f6b18e1413847800`. Its five members all passed ZIP CRC verification; a separately uploaded `R39.4.11-THREE-READS-REVIEW.json` matched the ZIP copy byte-for-byte. Guest log SHA-256 `e6ae2318ab6a484b19eb1c25afc302453846d3b7e8c24195c640df25dedef819`; original strict R39.4 review SHA-256 `d5774bc66bde162f4578f2afe53a50c8cc481df3f964a843fdf58b45e3da2b58`; independent R39.4.11 review SHA-256 `4bd0dac126cc1e4d9533c322ea22707df13b36a89b3eead6b33c86557f39c70f`. Raw evidence remains held in the conversation, not committed publicly.

- Original independent R25 baseline: `R25_REAL_EVENT_LOOP_ARM_PASS`.
- Source preflight: `R39_4_PINNED_SOURCES_PASS`.
- **Unchanged original R39.4 strict reviewer:** `R39_4_SAME_SESSION_REOPEN_ARM_PASS`.
- **Independent source-bound R39.4.11 reviewer:** `R39_4_11_THREE_SOURCE_BOUND_READS_ARM_PASS`.
- Guest concludes `R39_4_REOPEN_ARM_GATE_PASS` with genuine `R39_REAL_READER_EXIT_BOUNDARY_PASS` and UIManager teardown exit code 0.

## Verified scenario and limitations

The original two-page synthetic PDF was opened through genuine FileManager into genuine ReaderUI and MuPDF. A real UIManager page-turn produced page 2. Home returned to a genuine FileManager with first PDF engine/DocumentRegistry released. Opening the **same** PDF again created a distinct second ReaderUI and PDF document; second MuPDF scroll drew page 2, then second Home released the second engine and all registry refs, returned the genuine FileManager with expected chooser path and sole UI-stack ownership. Final genuine FileManager Close and Generic teardown executed.

The guest recorded **exactly three** source-bound reads of the first-cycle-generated `r39-original-two-pages.sdr/metadata.pdf.lua`, via FileManager provider resolution, original PdfDocument constructor and original ReaderUI:init. There were **two** source/mode-bound metadata write-opens, one per Home close. Write-open observations are not proof of durable fsync. The denied-operation summary is **zero**, and there are no `R23_DENIED_` markers, uncaught crashes or source deviations. Historical R39.4.7–R39.4.10 guest strict FAILs remain FAIL, not retroactively reinterpreted.

The archived source release `pw3-os-r39.4.11-readerui-third-sidecar-arm-trial.zip` SHA-256 is `37ab90f4fc566f98c98ef19efa32e9e3a573e18a62d800e5b3006190d7768f00`, guard SHA-256 `e7f1d0872f91b1ddfac42f9d7f35309072293d9dd551ad5543c455a1bebf88a7`. Its original checksum manifest has 105 payloads. **All 563 source-host Python regressions PASS** on independent reexecution. The experimental source, checksum-pinned checker, separate reviewer, patch and tests are versioned under `research/r39.4.11`.

This verifies **only the offline synthetic ARM application behavior**. It does not establish physical Kindle display or input, original kernel boot with Alpine, firmware compatibility, power/EPDC behavior, completed global migrations or full runtime dependency closure. The **976 `UNKNOWN_HOLD`** staged files remain protected; no file-pruning or boot authorization follows.

Next evidence gate: [R40 offline dynamic dependency evidence plan](R40-OFFLINE-DEPENDENCY-EVIDENCE-PLAN.md), informed by [R26 static inventory](R26-STATIC-DEPENDENCY-INVENTORY.md) and the [unexecuted R27 syscall trace proposal](R27-GUEST-SYSCALL-TRACE.md).

**Immutable:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Research and educational purposes only.
