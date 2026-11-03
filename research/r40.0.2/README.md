# R40.0.2 — source-bound offline QEMU trace stream and exit-marker repair

**2026-11-03: 628 host regressions PASS (Linux), ARM/QEMU PENDING. NOT_BOOTABLE.**

## Actual prior failure, evidence scope

The user ran R40.0.1 on macOS, with host Python suite `OK (skipped=3)`, fresh independent `R25_REAL_EVENT_LOOP_ARM_PASS`, original `R39_4_SAME_SESSION_REOPEN_ARM_PASS` and source-bound `R39_4_11_THREE_SOURCE_BOUND_READS_ARM_PASS`. The first, untraced baseline was clean. The new traced reviewers and final R40 review returned **FAIL**. The user uploaded shareable `R40.0.1-SHAREABLE-EVIDENCE.zip` (two JSON files; ZIP CRC PASS).

The summary records **8,333 recognized QEMU syscall lines, 2,713 decoded path operations**, of which **973 succeeded and 1,740 failed**; zero undecoded path syscall lines. Of the failures, `LUA_CODE_OR_SETTINGS` contributes 1,393, but these could include optional Lua loader candidate lookups: classify missing paths by local context before calling anything a required dependency. There is no path-level data in the uploaded summary, and **no evidence permitting deletion or claiming closure**.

### Two distinct harness problems

1. **Confirmed missing exit-gate marker:** the source-pinned original R39.4 runner uses `echo R39_4_REOPEN_ARM_GATE_PASS | tee -a R394-EMULATION.log` **only** after guest exit code zero. The R40 traced probe never emitted this shell-level marker. The original strict reviewer requires exactly one such marker, so traced R40.0.1 cannot earn PASS even with an otherwise clean application run.
2. **Potential interleaving:** `qemu-arm -strace` emits syscall records to stderr, but R40.0.1 used `> "$RAW" 2>&1`, merging stderr into guest stdout. This can split or embed records inside strict application-marker lines. The shareable JSON does not prove that it occurred in this run. The fix is preventative and test-covered, not a post-hoc reinterpretation.

## R40.0.2 trial changes

- `r40/probe_trace_in_container.sh` writes genuine guest stdout to private `R40-GUEST-STDOUT-PRIVATE.log` and QEMU syscall + guest stderr to private `R40-QEMU-RAW-PRIVATE.log`, rather than merging them.
- After the traced guest exits with code **zero**, the probe appends precisely the original shell-level `R39_4_REOPEN_ARM_GATE_PASS` to captured guest stdout. Nonzero/timeout emits a FAIL instead. The parser and independent reviewer do **not** fabricate lifecycle markers.
- `r40/collect.py` parses QEMU syscall records from private stderr and uses intact guest stdout for exact application-marker reviews. The summary reports only counts, SHA-256 and booleans, with no pathnames; the private event file retains detailed observations.
- `r40/review.py` recomputes all public counts and private events from both original captured streams, requires the unchanged R25/R39.4/R39.4.11 PASS results, rejects stdout syscall contamination, displaced stderr markers, guest stderr denials/crashes, missing exit status or unapproved source changes. All original R39.4.11 source and strict reviewers remain unchanged.
- `r40/diagnose.py` can analyze the previous R40.0.1 results **locally**, exporting only exact counts for six known milestone markers, reviewer PASS/FAIL statuses and crash/denial counts. It refuses overwrite; it never exports private paths or raw lines.
- Two modified test fixtures, 25 new negative regressions, host suite **628 tests OK**; Python compile and POSIX shell syntax checks PASS. Linux host only; no new user-side Mac or ARM result yet.

## Release integrity and command path

Full source ZIP: `pw3-os-r40.0.2-split-qemu-stderr-guest-stdout.zip`
SHA-256 **`059575b538aa1422e0e895b1848a3d7d537e80ab644bcaf7cdb97214ada7f685`**.

**119 ZIP entries, 118 SHA256SUMS-R4002 payload entries and 117 SHA256SUMS-R40 payload entries**, CRC and all checksums PASS. All **105 original R39.4.11 source-pin entries** remain verified and unchanged. Modified relative to R40.0.1: release README, Docker runner, tracing probe, parser, reviewer and previous host test; added private-only diagnostic, new negative tests, and full unified patch `PATCH-R40.0.2.diff` inside the ZIP. All other old ZIP payloads unchanged.

Extract into `~/Downloads/pw3-os-r40.0.2-isolated`, separate from the old source directories. The included `README-R40.md` has exact nine-argument command to rerun the guest with a **fresh sibling results directory** `~/Downloads/pw3-os-r40.0.2-split-first-run`. Only upload `R40-SUMMARY.json` and `R40-REVIEW.json`; if the retry fails, the optional local diagnostic can output `R40.0.2-LOCAL-DIAG.json` with marker counts only. Keep private syscall and guest log files locally.

The complete runnable source is in the separate verified conversation ZIP, **not embedded as a distributable stock-device image**. Original R40.0.1 evidence and historical prior failures remain preserved.

**Immutable safety holds:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Keep all 976 staged `UNKNOWN_HOLD` files intact. Nothing about one observed QEMU scenario establishes complete dependency closure, physical Kindle operation, bootability or safe deletion. Research and educational purposes only.
