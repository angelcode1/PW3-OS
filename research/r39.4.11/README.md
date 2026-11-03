# R39.4.11 — three original PDF metadata consumers in one genuine reopen

**Status 2026-11-03: HOST-TESTED ONLY, ARM/QEMU PENDING, NOT_BOOTABLE.**

The user's unmodified R39.4.10 ARM evidence ZIP SHA-256 is `10b9d4205e705a5119ba7f840e5ec2c6acbb5d3ccf30f1f20848a1366820a3c9`, ZIP CRC PASS. The independent original R25 strict ARM control remained `R25_REAL_EVENT_LOOP_ARM_PASS`. Source preflight was `R39_4_PINNED_SOURCES_PASS`, with the R39.4.10 PdfDocument phase pinned. The *original strict R39.4 and separate R39.4.10 reviewers* both correctly returned `FAIL`; the stage did **not** reach `R39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY` or final FileManager Close proof.

Real ARM execution logged an exact first PDF metadata sidecar read during returned FileManager `openFile`, followed by a verified second read through `PdfDocument:convertKoptToReflowableFontSize` (source-pinned original `frontend/document/pdfdocument.lua` lines 74/34). Both source-bound reads succeeded. After the genuine second `ReaderUI:init` called `Input:inhibitInput(true)`, **one further exact PDF sidecar `DOFILE` was denied**. The actual original KOReader v2026.07.2 `ReaderUI:init` calls `DocSettings:open(file)` at `frontend/apps/reader/readerui.lua:131`. The second PDF still completed a real scroll draw and second Home-close write, then the experimental guard rejected the second FileManager active check because `stats.denied=1`. The original strict FAIL is retained, not upgraded.

R39.4.11 is a bounded experimental test of **three** source-specific, exact-sidecar reads: FileManager provider lookup; original PdfDocument constructor; original ReaderUI:init at line 131 after the second input inhibit and before its release. The new third condition requires original function identity and source line, C `pcall` and genuine `DocSettings:open` at line 276, a first PDF already released, a distinct second live PDF in `DocumentRegistry` with reference count 1, the exact regular non-symlink synthetic sidecar, no other denial, and the exact lifecycle phase. Every other `dofile` request is still blocked. Only two genuine source-/mode-bound metadata write-opens, one per Home, are permitted. The original strict R39.4, R39.4.5 and R39.4.6 reviewers and independent R25 baseline remain **byte-for-byte unchanged**; the separate new R39.4.11 reviewer requires their independent PASS as a prerequisite and further enforces all three read markers and final cleanup.

## Host verification and release

- **563/563 Python host regressions PASS** (538 inherited + 25 new).
- Python `compileall`, POSIX shell checks and six Lua 5.4 syntax-only loads PASS.
- New source release ZIP: `pw3-os-r39.4.11-readerui-third-sidecar-arm-trial.zip`; SHA-256 `37ab90f4fc566f98c98ef19efa32e9e3a573e18a62d800e5b3006190d7768f00`.
- ZIP contains **106 entries**, including `SHA256SUMS-R39411`; 105 payload SHA-256 checks and ZIP CRC PASS.
- Experimental guard SHA-256: `e7f1d0872f91b1ddfac42f9d7f35309072293d9dd551ad5543c455a1bebf88a7`.
- Source checker SHA-256: `a4a44554c6dc15442090a48895d5fb1097707721f335a3dc2014c870482d64a3`.
- New separate strict reviewer SHA-256: `688e38c0229103b6557bc5a33d39301997d068ef8bd4869f080fc70f16824021`.
- Complete patch SHA-256: `db9d901945c8729b577b5031d3229c88a35859ab4d258f5f3e4f20481d4490c3`.
- Source-pin baseline SHA-256: `0965cc63a5874b684200499558bae8dd01581fb0e71094419d2a7d3d47b3e2ea`.

**The runnable patch, full guard, checker, reviewer and regression tests are in the separate verified research-session ZIP. They are not yet installed as standalone files in this GitHub tree.** The new ARM test has not been executed.

## Mac command overview

Extract into isolated `~/Downloads/pw3-os-r39.4.11-isolated`, not directly into Downloads, and run outputs into sibling `~/Downloads/pw3-os-r39.4.11-third-read-first-run`. Read the archive's `README-R39.4.11.md` for the complete nine-argument `sh ./run-r394-docker.sh`, separate `r394/review_r39411.py` command and `R39.4.11-ARM-EVIDENCE.zip` collection. Always preserve any strict FAIL as such.

**Safety:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. All 976 `UNKNOWN_HOLD` staged files are retained. No physical PW3 test or independent boot is authorized. For research and educational purposes only.
