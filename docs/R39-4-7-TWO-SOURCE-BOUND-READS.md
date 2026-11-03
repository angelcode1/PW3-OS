# R39.4.7 — original FileManager and ReaderUI source-bound metadata reads

**2026-11-03 status: HOST-TESTED ONLY (462/462 regressions PASS); fresh ARM/QEMU PENDING; NOT_BOOTABLE.**

The uploaded R39.4.6 ARM failure establishes that the **same** generated synthetic PDF metadata file was requested twice during one genuine second opening: first through FileManager before scheduling the reader, second within original `ReaderUI:init` at source-pinned `frontend/apps/reader/readerui.lua:131`. The first exact, builtin-C-`pcall`/original-`DocSettings:open` read passed; the second was denied by the former single-read counter, although the second genuine PDF draw and Home metadata write-open then succeeded. Original strict reviewers properly stayed FAIL; final FileManager Close was not verified.

In R39.4.7 the **experimental** fork's `r394/loop_guard.lua` allows exactly two reads of the one original first-cycle-generated `r39-original-two-pages.sdr/metadata.pdf.lua`, each through the builtin C `pcall` and source-pinned loaded original `DocSettings:open` at line 276. The first retains the actual first document release and **empty DocumentRegistry** check during returned FileManager reopening. The second requires the loaded original `ReaderUI:init` function identity, caller line 131, audited second Input inhibition phase, genuine closed first reader/document, inactive FileManager, ordinary non-symlink metadata file and directory, correct source-bound first write and first successful read, no second draw/Home yet and no recorded denials. The second reader may itself own a registry reference at this phase, so the first read's global empty-registry check is not incorrectly reused. Exactly two original write-opens (one per Home) remain source/mode/path restricted; all other `dofile` paths remain denied. KOReader production sources are unchanged.

The existing original R39.4, R39.4.5 and R39.4.6 reviewers are unchanged. A new independent [`review_r3947.py`](../research/r39.4.7/r394/review_r3947.py) first requires all three prior reviews' PASS conditions, then additionally requires unique and ordered first/second read-gate and loaded markers, two exact target observations, genuine second ReaderUI input, second PDF scroll draw, both Home returns, two bounded metadata writes, zero denials, genuine final FileManager Close and immutable safety holds.

**Reproducible source and patch:** [`research/r39.4.7/`](../research/r39.4.7/README-R39.4.7.md) contains the experimental guard, source checker, reviewer, previous adjusted source assertion, new tests, source hashes and exact patch against the R39.4.6 research distribution. The complete session release `pw3-os-r39.4.7-two-source-bound-sidecar-reads-arm-trial.zip` SHA-256 is `7f5dfd322c8e34e2598a37fbfc9f40be5301c1b4a810bd8cece8c7686730a83d`; ZIP CRC and all 81 payload hashes PASS (82 ZIP entries).

**Host test results:** 462/462 Python regressions PASS (442 inherited plus 20 new); Python compileall, POSIX shell syntax and six Lua 5.4 syntax-only checks PASS. The authoring environment has no Docker guest; therefore **R39.4.7 ARM success is NOT CLAIMED**. For the exact Mac commands, reviewer and evidence packaging, use the versioned research README.

**Safety holds unchanged:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Preserve all 976 `UNKNOWN_HOLD` staged files. No hardware/firmware operation, independent Alpine boot, global migrations or dependency closure proven. Research and educational purposes only.

## User-supplied real R39.4.7 ARM/QEMU result (2026-11-03)

The user's original `R39.4.7-ARM-EVIDENCE.zip` SHA-256 `1ae8aa09f0c2da678c7a0d135dbdf23437f2b17ce5f49adcbbe0018637ef3741` passes ZIP CRC and includes the fresh original independent R25 `R25_REAL_EVENT_LOOP_ARM_PASS`, experimental `R39_4_PINNED_SOURCES_PASS` preflight with the R39.4.7 source pin, original strict R39.4 **FAIL**, and separate R39.4.7 **FAIL**. Neither reviewer establishes a completed repeated-reader lifecycle.

At the first exact metadata sidecar `dofile` inside the returned FileManager's `openFile`, the guest recorded:

```text
R39_4_4_DOFILE_TARGET path_kind=exact_pdf_sidecar caller_kind=other line=0 cycle=2 events=2 filemanagers=2
R39_4_5_SIDECAR_GATE exact=true c_pcall=true docsettings=true fresh_write=true regular_file=true cycle2=false
R39_4_3_FIRST_DENIAL kind=DOFILE caller=other line=0 cycle=2 events=2 filemanagers=2
```

The original first PDF completed Home/engine release and first genuine FileManager return. The second ReaderUI subsequently opened the PDF and rendered page 1, but its second Home-close write failed with `R23_DENIED_SIDECAR_WRITE_PROVENANCE` because the first sidecar read remained denied and counts could not be reset. The original strict reviewer therefore correctly reports a missing `R39_4_SECOND_DOCUMENT_ENGINE_CLOSED_REGISTRY_EMPTY` marker; final FileManager Close is still unverified.

Source inspection establishes a narrow experimental-guard mismatch: R39.4.7's common second-read context required `real_fm.instance==nil` before provider selection in the original `FileManager:openFile` (where the instance must still be active). Original KOReader v2026.07.2 calls `DocumentRegistry:getProvider` first (line 1619), then schedules `ReaderUI:showReader` (line 1635), which releases FileManager. The later `ReaderUI:init` sidecar read properly requires FileManager to have been closed.

This is evidence of a **synthetic guard precondition**, not a KOReader production bug. No denial is bypassed, the historic R39.4.7 real-ARM FAIL remains unchanged, and no independent boot or hardware verification is claimed. [R39.4.8 trial](R39-4-8-RETURNED-FM-READ-PHASE.md) corrects only the phase-specific FM state.
