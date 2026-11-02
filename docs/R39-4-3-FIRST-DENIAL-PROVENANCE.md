# R39.4.3 — first denied-operation provenance diagnostic

**2026-11-03 status: host-tested diagnostic only; 356/356 host regressions PASS, ARM/QEMU fresh run PENDING; NOT_BOOTABLE.** The actual R39.4.2 guest reviewer remains FAIL.

## Source-supported reason

The R39.4.2 user-side guest trace confirms the *second* genuine FileManager is present, its chooser path equals the expected disposable library path, and it is the sole UIManager stack widget. The identical strict second-FileManager assertion nevertheless fails because its fourth condition `stats.denied==0` is false. The R39.4.2 analyzer correctly isolated `denied_operation_recorded` but did not determine the specific denied call or its safety significance.

In the experimental guard, `deny(reason)` increments `stats.denied` and throws `R23_DENIED_...`. If KOReader catches the exception, the counter remains nonzero even after later FileManager construction. Whether this occurred, and whether it was a benign guarded probe or a real prohibited action, remains UNKNOWN.

## Exact experimental change

R39.4.3 changes only the **separate experimental fork** `r394/loop_guard.lua`, source pins, and new Python read-only analyzer/tests. On the **first** denied call, the original `deny` function emits one bounded `R39_4_3_FIRST_DENIAL` marker with enumerated denial kind, redacted staged caller and line, and cycle/event/FileManager counts. It still increments `stats.denied` and raises the same `R23_DENIED_...` error. At the existing R39.4.2 post-constructor snapshot, one `R39_4_3_DENIAL_SUMMARY` marker records the counter. No raw requested paths, device data or full stack dumps are reported.

**Preserved unchanged:** the original strict `r394/review_r394.py`, original R39.4.2 diagnostic snapshot/analyzer, real production KOReader, PDF, ReaderUI, FileManager, DocumentRegistry, hard filesystem/module/exec denials, two genuine Home transitions, four-event/eight-poll ceiling, final FileManager cleanup assertion, original R25 baseline and `NOT_BOOTABLE` holds.

The separate `r394/analyze_denial_provenance.py` demands the existing strict R39.4 **FAIL** and the R39.4.2 diagnosis isolating a nonzero denied counter, a fresh original R25 PASS, pinned R39.4.3 sources, and a unique bounded first-denial marker ordered after the first verified Home return and before the second FileManager strict failure. It produces only `R39_4_3_FIRST_DENIAL_PROVENANCE_CAPTURED` with `root_cause_determined=false`, `new_arm_success_claimed=false`, `diagnostic_only=true`. It rejects contradictory, duplicate, malformed, misordered or unsafe evidence and never relabels the original strict failure.

## Host-provenance release

Session archive `pw3-os-r39.4.3-denied-operation-provenance-diagnostic.zip`, SHA-256 `8ef3e57b8ecf7a2d31787f59a6da23e115c123bedf894822fab46df9ec5c0ceb`; 61 ZIP entries, CRC and all 60 SHA-256 manifest items PASS. New experimental guard SHA-256 `6316ed566fedad8a72591d6e60678524f530454d0fb49517cdf46c6151c4527a`; analyzer SHA-256 `a74b0e7af52e9b291d10a341e6e9ae505fe947a4d2eaef34ff2c5270dd18569b`. Original strict reviewer SHA-256 remains `b2d7a44f1acedeb6ec9899074e91bb0f4d3a4fed63b15d0816ff9d7b99d51e57`.

**356/356 host regressions PASS**, Python compileall and POSIX shell syntax PASS, six Lua files pass Lua 5.4 syntax-only load via liblua5.4. No actual new ARM/QEMU run for R39.4.3 has been carried out in the research session. The downloadable archive's `README-R39.4.3.md` contains the Mac Docker run, fresh result directory, post-run analyzer, and evidence ZIP collection.

Original R39.4, R39.4.1, and R39.4.2 strict `FAIL` evidence is preserved; no source/package update justifies asserting an ARM PASS. **NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE.** The 976 staged `UNKNOWN_HOLD` files remain retained; no physical Kindle test, migrations or independent boot proof.
