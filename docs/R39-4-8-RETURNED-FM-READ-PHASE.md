# R39.4.8 — phase-bound returned FileManager sidecar read

**3 November 2026: host-tested release only — 478/478 host regressions PASS. ARM/QEMU PENDING. `NOT_BOOTABLE`.**

## What actual R39.4.7 ARM evidence establishes

The guest passed the independent original R25 control and R39.4 pinned-source preflight. The genuine first two-page MuPDF PDF completed a real UIManager GotoPage(2), returned Home, released the PDF engine and returned genuine FileManager. The second FileManager entered `openFile`; the exact sidecar read had correct C `pcall`, original `DocSettings:open`, regular file and generated-first-cycle-write proof, but the R39.4.7 `cycle2=false` assertion denied it.

The synthetic guard's shared `second_context` tested `real_fm.instance==nil` before the first metadata read. The original KOReader `FileManager:openFile` calls `DocumentRegistry:getProvider(file,true)` **before** `ReaderUI:showReader` closes FileManager. The FM instance is therefore validly present at the first metadata read. The later second `ReaderUI:init` metadata read must find FileManager closed. The previous guard conflated these two states. The subsequent actual second PDF draw does not clear the recorded `stats.denied=1`, and the second Home-close write also failed. All original R39.4.7 strict FAIL evidence remains historical.

## Experimental-only R39.4.8 correction

The versioned guard `research/r39.4.8/r394/loop_guard.lua` distinguishes:

- **First read, FileManager phase:** exact disposable sidecar; source-verified C `pcall` and `DocSettings:open` at line 276; first Home returned, first PDF engine and registry released, exact first writer, first read only, returned genuine FileManager still active, file chooser path equals `/tmp/r25-ko-home/library` and FM is the sole UIManager stack widget.
- **Second read, ReaderUI phase:** same exact sidecar and original source; first read already completed, distinct second genuine Input lifecycle, actual `ReaderUI:init` function identity and line 131, and original FileManager singleton now nil. A new document may already have an active registry reference, so the first pre-open registry-zero check is not reapplied.

The original rejection function, exact file and source pin checks, two-read/two-write limits, input-event budgets, original strict R39.4, R39.4.5, R39.4.6 and R39.4.7 reviewers, original R25 baseline and KOReader production modules remain unchanged. Two read-only markers report the first returned FileManager's active/closed-first-PDF state and the second ReaderUI's FM-closed/input state. Separate `research/r39.4.8/r394/review_r3948.py` can declare PASS only when **every prior strict reviewer independently PASSes**, both phase markers appear once in chronological order, both PDF reads and both Home returns are genuine, no denial or crash occurs, and final genuine FileManager Close completes.

## Release and evidence

Session archive `pw3-os-r39.4.8-returned-fm-sidecar-phase-arm-trial.zip` SHA-256 `67d3611977a957747308c18f9518dcad897abec5e156c4621ac3159efc60c28a`, 88 ZIP entries, CRC PASS, all 87 SHA-256 manifest entries PASS. **478/478** Python host regressions PASS, six Lua source files compile syntax-only with liblua5.4, Python and POSIX shell checks PASS. No Docker/ARM guest is available in the host-test environment; ARM/QEMU execution is pending. The initial R39.4.7 ARM evidence archive SHA-256 is `1ae8aa09f0c2da678c7a0d135dbdf23437f2b17ce5f49adcbbe0018637ef3741`.

Versioned source `research/r39.4.8` records the experimental guard, checker, new independent reviewer, negative regression tests and hash baseline. Exact macOS runner, post-run reviewer and evidence ZIP instructions are in the release's `README-R39.4.8.md`. Extract into `~/Downloads/pw3-os-r39.4.8-isolated`, keep results outside the source tree, and never overwrite old evidence.

Only a fresh actual guest and independent reviewer may establish `R39_4_8_FILEMANAGER_PHASE_BOUND_SIDECAR_ARM_PASS`; host fixtures cannot. Nothing here proves independent boot, physical Kindle rendering, global migrations, complete dependency closure or safe file pruning.

**Immutable holds:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. All 976 staged `UNKNOWN_HOLD` files remain retained. For research and educational purposes only.
