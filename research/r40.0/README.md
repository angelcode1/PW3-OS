# PW3-OS R40.0 — offline QEMU guest syscall file observation

**2026-11-03: Host-only source release. 602/602 tests PASS. ARM/QEMU observation NOT YET RUN. `NOT_BOOTABLE`.**

## Baseline provenance

This release embeds the unchanged R39.4.11 synthetic ARM/QEMU source, whose **independent user-supplied** prior evidence is `R39_4_11_THREE_SOURCE_BOUND_READS_ARM_PASS`, together with original independent R25 and original strict R39.4 PASS. The original R39.4.11 archive SHA-256 is `37ab90f4fc566f98c98ef19efa32e9e3a573e18a62d800e5b3006190d7768f00` and all 105 original manifest entries are checked without modifying their contents. R40 is a new experiment, not a rewrite of that evidence. Other old R39.4.7–R39.4.10 guest FAILs remain historical failures.

## Source release and verification

ZIP: `pw3-os-r40.0-offline-qemu-file-observer.zip` (created in the ChatGPT conversation), SHA-256 **`bd26fae3bf9bd89f8d0133e1090a07496ceea334d6d7332c43d90c99de221999`**. It is a ZIP-flat source release: unzip into a new dedicated source subdirectory. **115 ZIP entries / 114 manifest-checked payload files**, ZIP CRC PASS and all payload SHA-256 hashes PASS. **602 Python host tests PASS** (563 original R39.4.11 inherited, 39 new). Python syntax compilation and POSIX `sh -n` PASS. This is **not** an ARM/QEMU pass.

Included new scripts: `run-r40-docker.sh`, `r40/check_inputs.py`, `r40/probe_trace_in_container.sh`, `r40/collect.py`, `r40/review.py`, `tests/test_r40.py`, `README-R40.md`, `SHA256SUMS-R40`, plus the validated prior R39.4.11 attestation. R39.4.11 original source and strict reviewers are unchanged. The full runnable scripts are in the **verified separate ZIP**, not standalone GitHub source files as of this commit.

## Actual methodology (pending execution)

1. Require exact original release SHA pins, R39.4.11 attestation and disjoint fresh output paths. Reject stage/source/core output overlap, source tampering and attempts to overwrite results.
2. Execute the unchanged R39.4.11 Docker runner with the independent fresh R25, original R39.4 strict and R39.4.11 source-bound reviewers. Refuse tracing if the original controls do not PASS.
3. In a **separate**, offline, unprivileged, network-disabled, read-only container with readonly stage and source mounts, run the same genuine two-cycle PDF scenario under `qemu-arm -strace`. The `qemu-arm -strace` output is guest syscall information printed to stderr, mixed with guest stderr, and is **incomplete**. It does not require a guest `ptrace` or guest `strace` binary. Keep full raw logs and exact guest paths PRIVATE.
4. Filter QEMU syscall lines into a separate app-only log, rerun the original strict R39.4 and R39.4.11 independent reviewers against that traced replay. Recompute all public counts from the private raw trace; require both replays, source pins, exit code zero and no denials. Do not report success if a stage file was changed or an expected marker is missing.
5. Emit **filename-free** `R40-SUMMARY.json` with syscall and error counts, and `R40-REVIEW.json`. Only those two JSON files are intended for user upload; the raw QEMU trace, raw guest paths and path-level private event file remain local.

The guest observation covers only a **single** synthetic two-cycle PDF/Ink Away scenario. It does **not** capture all Lua-module requires, all `dlopen` decisions, file-backed mmap file identity, EPDC/kernel firmware, font/fallback paths, global migrations or boot/recovery dependencies. The count of unobserved files is **not** a safe deletion set. The old 976 `UNKNOWN_HOLD` entries stay protected.

## User Mac execution

The archive's `README-R40.md` contains exact paths and a 9-argument `sh ./run-r40-docker.sh` command matching the previous R39.4.11 stage/core/reviews. Fresh source directory: `~/Downloads/pw3-os-r40.0-isolated`; fresh sibling output: `~/Downloads/pw3-os-r40.0-observation-first-run`. Package only `R40-SUMMARY.json` and `R40-REVIEW.json` as `R40.0-SHAREABLE-EVIDENCE.zip`, never raw logs.

**Immutable holds:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Stage data, original firmware, existing kernel, hardware interfaces and recovery are untouched. Research and educational purposes only.
