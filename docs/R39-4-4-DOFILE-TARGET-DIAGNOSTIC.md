# R39.4.4 — exact DOFILE target and caller classification

**2026-11-03: Source-only host tested, 373/373 Python tests PASS; ARM/QEMU PENDING. `NOT_BOOTABLE`.**

## Confirmed problem

R39.4.3 user's independent ARM/QEMU test recorded a genuine reopened second ReaderUI and PDF draw, a second Home that released the PDF engine/registry, and a returned FileManager correctly on top of the UIManager stack. The original strict R39.4 reviewer still **FAILed** because the test's denied-operation counter was one. Its first-denial marker identified **`DOFILE`**, `cycle=2 events=2 filemanagers=2`, with source caller `other`, line 0. The denied path is not in that trace. No final FileManager Close has been proven.

Relevant staged upstream KOReader v2026.07.2 sources: [`DocSettings:open`](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/docsettings.lua#L221-L295) reads existing sidecar metadata using `pcall(dofile, candidate_path)`, and [`getSidecarFilename`](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/docsettings.lua#L143-L146) derives `metadata.pdf.lua` from this PDF suffix. [`getSidecarDir`](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/docsettings.lua#L118-L141) derives the document-sidecar `.sdr` directory. This suggests `/tmp/r25-ko-home/library/r39-original-two-pages.sdr/metadata.pdf.lua` may be the denied read **but it has not been observed at runtime**.

## R39.4.4 experimental-only diagnostic

The release changes only the experimental `r394/loop_guard.lua`, `r394/check_inputs.py` source pins, and adds `r394/analyze_dofile_target.py`, tests and documentation. Immediately before the existing unchanged `deny('DOFILE:'..tostring(path))`, a one-time redacted marker `R39_4_4_DOFILE_TARGET` categorizes the target by **exact** string equality to the expected synthetic document-sidecar, backup or legacy candidate; otherwise generic protected/temporary/unknown classifications. It classifies the *immediate* original Lua caller using `debug.getinfo(2,'Sl')` into `docsettings`, `luasettings`, `documentregistry` or `other`. It logs no raw file paths or Lua source contents.

No file is read by the observation. The original forbidden operation still increments `stats.denied` and raises the same error. No changes to production KOReader, R25 baseline, R39.4 original strict reviewer, event budget, FileManager constructor or physical device occur. Original R39.4.2 and R39.4.3 diagnostics remain intact.

The new fail-closed analyzer requires the original R39.4.3 read-only diagnostic chain, **exactly one `DOFILE`**, fresh R25 PASS, original strict R39.4 **FAIL**, source pins and ordered markers. It reports only `R39_4_4_DOFILE_TARGET_DIAGNOSTIC_CAPTURED`, sets `diagnostic_only=true` and `new_arm_success_claimed=false`, and never marks FileManager final Close verified. Its `exact_sidecar_proven` can be true only for `path_kind=exact_pdf_sidecar` and `caller_kind=docsettings`; this is observation, not an authorization to execute.

## Release provenance

Source archive: `pw3-os-r39.4.4-dofile-sidecar-provenance-diagnostic.zip`, SHA-256 `2a8320269b14e0046985627aeb9e0f8224251722efc6052dd65b0cc4529ec786`; **66 ZIP entries and 65 manifest entries**, CRC and hashes verified. Original R39.4 strict reviewer SHA-256 remains `b2d7a44f1acedeb6ec9899074e91bb0f4d3a4fed63b15d0816ff9d7b99d51e57`.

- Experimental guard SHA-256 `f0fddcdc93c7926467b6774be423c1fe078e0f3631efb47743bc7aa0cdca4ecd`
- Separate target analyzer SHA-256 `dc54bb8cc05efdd1bd85ef8ba6ccf414001d01617fc0e1a4b5674c8bd118153b`
- New source checker SHA-256 `a7bd780b2003d5323a6d05428a1d912a2d2acf283c46344e4a343f8f91966d0a`
- **373/373 Python host regressions PASS**, six Lua 5.4 syntax-only checks PASS, Python compilation and POSIX shell syntax PASS.

This is a separately downloadable research-session ZIP, not a bootable image. It is deliberately ZIP-flat: **unzip into a dedicated subdirectory** (`~/Downloads/pw3-os-r39.4.4-isolated`) rather than into `~/Downloads`, and place output in a *sibling* directory (`~/Downloads/pw3-os-r39.4.4-dofile-first-run`). The archive's `README-R39.4.4.md` supplies the complete Mac runner, analyzer and ZIP collection commands.

**Strict R39.4 ARM result remains FAIL; no R39.4.4 ARM result yet.** No allowlist expansion is justified without the exact observed target and source.

**Immutable safety holds:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Preserve all 976 `UNKNOWN_HOLD` staged files. No physical Kindle screen, kernel, boot, firmware or hardware test. Research and educational purposes only.
