# R39.4.10 — source-bound PdfDocument constructor trial

Status as of 2026-11-03: 538 host tests PASS; ARM/QEMU pending; NOT_BOOTABLE.

## Actual R39.4.9 ARM/QEMU result (FAIL preserved)

The uploaded evidence ZIP passes CRC verification. The independent R25 baseline returns R25_REAL_EVENT_LOOP_ARM_PASS; source preflight returns R39_4_PINNED_SOURCES_PASS. Both the original R39.4 and separate R39.4.9 reviewers remain FAIL.

The first generated-PDF-metadata sidecar read from the active returned FileManager succeeded. The second read reported fm_closed=true, input_cycle1=true, prior_document_released=true, registry_empty=true, and confirmed DocSettings via C pcall, but all the expected DocumentRegistry:getAssociatedProviderKey / getProvider / openDocument frames were false. The read was denied, and the later second Home write was also rejected. No full second Home return and no final FileManager Close were proven.

## Source-level diagnosis and new experimental boundary

KOReader v2026.07.2 frontend/document/pdfdocument.lua has PdfDocument:init at line 34 calling self:convertKoptToReflowableFontSize(); the latter invokes DocSettings:open at line 74 when the generated PDF sidecar exists. The staged document is pinned to SHA-256 963cbae1a42e5cb163361e89585a47ca2994477cac5741da743d314fa2b5fe60 in the unchanged inherited source gate.

R39.4.10 changes only the separate experimental R39.4 guard, its source pin and an additional independent reviewer/test suite. The second read remains limited to the exact disposable PDF metadata sidecar, original DocSettings:open line 276 and C pcall, but now also requires live function identity and exact source lines for PdfDocument:convertKoptToReflowableFontSize (74) and PdfDocument:init (34). The original first source-bound read, no-denial, registry, input-cycle, historical engine and file type conditions remain. Every other DOFILE request is still denied. The original R25 baseline and strict R39.4/R39.4.5/R39.4.6 reviewers are unchanged; the prior R39.4.7/8/9 failure history is preserved.

## Release checks

Research-session source ZIP: pw3-os-r39.4.10-pdfdocument-constructor-sidecar-arm-trial.zip; SHA-256 11104a09e3db5cb48c9fa5dc8c5efa379455460252c5066042b6f15675fd12c9.

538 Python host tests PASS (509 inherited + 29 new); Python compileall PASS, three shell syntax checks PASS, six Lua 5.4 syntax-only checks PASS. The 100 ZIP entries and 99 payload manifest hashes verify. The generated runnable overlay is in the separately downloadable ZIP; it is not included in this repository documentation commit. No R39.4.10 ARM PASS claim.

Safety: NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE. All 976 UNKNOWN_HOLD staged files are retained. For research and educational purposes only.
