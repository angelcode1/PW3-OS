# R39.4.5 — first-cycle generated PDF sidecar source-bound read trial

**2026-11-03: Host-tested source release, 419/419 regressions PASS; ARM/QEMU PENDING. NOT_BOOTABLE.** Previous R39.4–R39.4.4 user-side strict FAILs remain historical evidence, and the last fully verified application milestone remains R39.3.3 ARM PASS.

## Evidence and scope

R39.4.4's real ARM trace identified one blocked `dofile` target, exactly the synthetic PDF's `/tmp/r25-ko-home/library/r39-original-two-pages.sdr/metadata.pdf.lua`. The caller remained `other/0`. Upstream KOReader v2026.07.2's `DocSettings:open` uses `pcall(dofile, candidate_path)` (line 276). A host Lua 5.4 call-stack model verifies `debug.getinfo(2)` is the C `pcall` frame and level 3 is the original Lua caller; the ARM LuaJIT call-stack contract remains unverified until fresh execution.

R39.4.5 changes **only the separate, experimental** `r394/loop_guard.lua` and its SHA-pinned source checker, adding `r394/review_r3945.py`, separate tests and documentation. It does not patch original KOReader or relax event/stack/engine ownership checks. A **single, conditional read** of the exact generated metadata filename is permitted only if all conditions hold: original `util.writeToFile` function (identified by loaded function identity and source line 1147) successfully created that same file with `io.open(...,'wb')` during the first Home close; the later read comes through built-in C `pcall` and loaded original `DocSettings:open` at line 276; the file and sidecar directory are regular non-symlinks; this is exactly cycle 2, FileManager count 2, event count 2, prior Home and PDF engine closed, and no other denial has occurred. The original Lua reader must return a table. No other `dofile` target, including backups or legacy files, is permitted; mismatches continue through the original denial counter/exception. This is source-specific for the fixed original synthetic two-page PDF and fresh disposable, networkless `/tmp` home, **not an arbitrary user-book or external-Lua allowance**.

The original strict `r394/review_r394.py` is **unchanged** and is run by the original runner. New `r394/review_r3945.py` can mark its own gate PASS only if the original strict output independently agrees with a freshly evaluated original strict PASS and the unique, ordered `R39_4_5_SIDECAR_GATE` and `R39_4_5_GENUINE_DOCSETTINGS_SIDECAR_LOADED_FROM_FIRST_CYCLE` markers. A failed first-stage source check or blocked execution must remain FAIL.

## Source provenance and verification

Research session source artifact: `pw3-os-r39.4.5-source-bound-sidecar-reopen-trial.zip`, SHA-256 `6da819af0a1a64d9f78a9a0bc16bf3d3519ee6068a955eb70e9e5f025b4adf61`. 71 ZIP entries, 70 SHA-256 payload entries, integrity PASS. Experimental guard SHA-256 `ea4676e0ee8ba068312a946c39932517862b14da00801716d3cf2fd608cbac5c`. Additional strict reviewer SHA-256 `8e28fb054aacc0ed4999deafd6b909ce5d88791a7e32451ea0e66c7d2cd322e0`. Original R39.4 strict reviewer SHA-256 `b2d7a44f1acedeb6ec9899074e91bb0f4d3a4fed63b15d0816ff9d7b99d51e57`, unchanged.

- **419/419 host regressions PASS**, including retained 373 previous tests and new negative cases (wrong caller, source pin, missing sidecar, erroneous original strict PASS, denied operation, source policy and chronological markers).
- Python compileall, POSIX shell syntax and six Lua 5.4 syntax-only parses PASS; a small Lua 5.4 C-`pcall` call-stack model also PASS.
- Fresh offline ARM/QEMU **not run** for R39.4.5. A successful host test is not proof of bootability or a genuine second reader lifecycle.

Extract the ZIP into a **new isolated source directory**, and write results into a **sibling** output directory, as detailed in its `README-R39.4.5.md`. Run the unchanged original R25 baseline, original R39.4 strict reviewer, and separate R39.4.5 reviewer in that order. Preserve any FAIL and upload the raw log and reviews rather than widening the exception.

**Immutable holds:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Preserve 976 prior `UNKNOWN_HOLD` staged files. Physical Kindle operation, global migrations and independent boot are unverified. For research and educational purposes only.
