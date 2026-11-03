# R39.4.6 — archived first document and two bounded metadata write-opens

**2026-11-03 status: source-only host-tested, 442/442 Python regressions PASS. Fresh user-side ARM/QEMU PENDING; `NOT_BOOTABLE`.** The original R39.4.5 ARM failure and all previous strict FAILs remain preserved.

## Observed source mismatch

Actual R39.4.5 ARM/QEMU attempted the **exact** generated sidecar through genuine `DocSettings:open` via original C `pcall`; prior first-cycle write provenance, file type and caller function identity all passed. However `cycle2=false`: the guard called `r3933_pdf_engine_released()`, which looks up `r39_saved_doc` even though R39.4's lifecycle deliberately moved the first document into `r394_first_doc` and set the former to nil. Source and the logged phase state together establish a synthetic-checker false negative.

The second genuine ReaderUI nevertheless opened the PDF, completed an authentic page-1 MuPDF scroll draw and dispatched Home. Its next metadata save reached the same exact `io.open(...,'wb')`, but the R39.4.5 guard only admitted first-Home write provenance (`cycle=1, events=2, FileManager=1`). Guest aborted with `R23_DENIED_SIDECAR_WRITE_PROVENANCE`. The original strict R39.4 and independent R39.4.5 reviews both returned FAIL. Final FileManager Close and Generic teardown remain unproven.

## Narrow R39.4.6 experimental correction

Only the isolated experimental `r394/loop_guard.lua`, source checker, and new reviewer/tests change. The source-based helper `r394_first_pdf_released()` examines the **archived** first PDF and ReaderUI, confirms `is_open=false`, raw engine field nil, inherited engine default false, cleared reader document, and no DocumentRegistry references to the original temporary PDF. It replaces the inappropriate saved-second-doc check at the second-open sidecar read; the original KOReader `Document:close` and ReaderUI are unchanged.

For the one **exact** disposable path `/tmp/r25-ko-home/library/r39-original-two-pages.sdr/metadata.pdf.lua`, the original `io.open(path,'wb')` is still required to originate at the source-pinned genuine `util.writeToFile` line 1147 with original function identity. The first accepted write-open must occur at the first Home. A **second and only second** write-open can occur at the second Home after one separately verified source-bound `DocSettings` read, a distinct second ReaderUI, a genuine second PDF draw, and the original first PDF release. Alternate paths, modes, functions, extra calls and all other `dofile` requests remain blocked. A counter for exactly two write-opens and one sidecar read is required at final clean exit. Write-open markers are not independent proof of complete file durability.

The unchanged original strict `r394/review_r394.py` is required to PASS independently before **either** separate `review_r3945.py` and `review_r3946.py` can return PASS. The new reviewer independently verifies the two write-open marker positions relative to first and second Home, sidecar read, second engine release and final genuine FileManager Close. Safety controls and runtime limits are unmodified.

## Release integrity

- Conversation ZIP: `pw3-os-r39.4.6-two-cycle-sidecar-provenance-arm-trial.zip`, SHA-256 `61a07f789ecf5a4396b653aa9ff661cad993310a39557f3910d6c8ac03099a89`.
- **76 ZIP entries**, including SHA256SUMS-R3946; **75 internal SHA-256 checks PASS**, ZIP CRC PASS.
- Experimental guard: `696f63de6682f5e50b236683bd16723ce42da7d5da448113bf68c7f1d87d3971`.
- New separate strict reviewer: `58587bd90bf6bd56c626d39fdc5690775ac5cf8bed9a152ba69de369822d74ef`.
- Original R39.4 strict reviewer: `b2d7a44f1acedeb6ec9899074e91bb0f4d3a4fed63b15d0816ff9d7b99d51e57`, **unchanged**.
- Original R39.4.5 reviewer: `8e28fb054aacc0ed4999deafd6b909ce5d88791a7e32451ea0e66c7d2cd322e0`, **unchanged**.
- **442/442 host Python regressions PASS**, including all prior 419 plus 23 new; shell/Python syntax and six Lua 5.4 syntax-only loads PASS. This is not ARM proof.

The ZIP is a separately downloadable research-session artifact and not a bootable image. Its `README-R39.4.6.md` includes exact Mac Docker runner, additional reviewer and evidence packaging commands. Extract into a dedicated `~/Downloads/pw3-os-r39.4.6-isolated` directory, with a **sibling** fresh output directory to avoid the prior source-inside-output preflight error.

**Required new ARM pass markers, if and only if earned:** `R25_REAL_EVENT_LOOP_ARM_PASS`, `R39_4_REOPEN_ARM_GATE_PASS`, `R39_4_SAME_SESSION_REOPEN_ARM_PASS`, and `R39_4_6_TWO_CYCLE_SIDECAR_REOPEN_ARM_PASS`. Preserve any failures; do not claim boot or hardware success.

**Immutable holds:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. All 976 prior `UNKNOWN_HOLD` staged files remain retained. Physical PW3 operation, independent Alpine boot, full dependency closure and global migrations remain unverified. Research and educational purposes only.

## User-side R39.4.6 ARM/QEMU result (2026-11-03; immutable FAIL)

The user provided `R39.4.6-ARM-EVIDENCE.zip` SHA-256 `af3b10736c0caaf1a620766204038326489c6ef0bd288064af37723684cfe994`. ZIP CRC PASS; independent original R25 `R25_REAL_EVENT_LOOP_ARM_PASS`; original R39.4 source preflight `R39_4_PINNED_SOURCES_PASS`. The unchanged original strict R39.4 and separate R39.4.6 review results were **FAIL**, missing the second engine-closed/registry-empty success marker. No final FileManager Close was verified.

The actual first Home closed the PDF and logged `R39_4_6_FIRST_GENUINE_SIDECAR_WRITE_OPEN`; the returned FileManager's original `openFile` performed one successful exact metadata `DocSettings:open`/C-`pcall` read (`R39_4_5_SIDECAR_GATE ... cycle2=true`; loaded marker present). After scheduling ReaderUI, the original ReaderUI initialization caused a **second** `DocSettings:open(file)` access. The same generated metadata file, original `DocSettings` function, ordinary-file and C-`pcall` checks passed, but `r3945_sidecar_loads==0` was no longer true, yielding `R39_4_5_SIDECAR_GATE ... cycle2=false` and one denied DOFILE. The second genuine PDF still rendered, its second Home closed the engine/registry, and `R39_4_6_SECOND_GENUINE_SIDECAR_WRITE_OPEN` succeeded. The post-constructor FileManager state was correct except `denied_zero=false`, so the intentionally unchanged strict assertion prevented final Close and PASS. R39.4.6's old ARM FAIL remains historical; do not reclassify it.

[R39.4.7](R39-4-7-TWO-SOURCE-BOUND-READS.md) adds a separate second, source-identical reader-init-only metadata read condition and distinct, fail-closed markers. No Kindle actions, file pruning or system boot are authorized.
