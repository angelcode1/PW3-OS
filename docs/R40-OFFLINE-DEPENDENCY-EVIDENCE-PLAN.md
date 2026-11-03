# R40 — offline dynamic dependency evidence and closure matrix (proposal)

**2026-11-03: R40.0 source-only host implementation released (602 tests PASS), ARM/QEMU NOT RUN, no rootfs reconstruction or removal authorization. NOT_BOOTABLE.**

## Why the next gate matters

[R39.4.11](R39-4-11-ARM-VERIFIED.md) now verifies two genuine same-session PDF lifecycles in offline ARM/QEMU, clean dual Home returns, three source-bound generated-sidecar reads, two write-opens and a final FileManager Close. It **does not** enumerate every Lua module, shared library, font, plugin asset, fallback file, subprocess, device blob or firmware requirement. [R26 static inventory](R26-STATIC-DEPENDENCY-INVENTORY.md) enumerated 2,070 stage entries, 83 ELFs and 976 distinct unclassified `UNKNOWN_HOLD` file entries from prior analysis, but did not trace runtime access. The proposed [R27 guest syscall trace](R27-GUEST-SYSCALL-TRACE.md) has no confirmed ARM result.

## Proposed read-only gates

1. Bind R40 input provenance to the exact SHA-pinned R13 stage, R26 catalog, R39.4.11 source overlay and original strict PASS. Reject stage modifications, unsafe symlink traversal, in-source outputs, unapproved networks and any physical-device mount.
2. Inside an **isolated, offline ARM/QEMU clone**, collect successes and failures for `open/openat/stat/execve`, file-backed mmap, dynamic `dlopen`, Lua `require/package.loaded` and plugin/resource access. Include time, pathname, caller or module, return code, scenario and an observed-vs-inferred classification; keep full path logs local and share only redacted aggregates.
3. Run several independent, synthetic-only cases: cold FileManager and Ink Away load/draw/save, two-page PDF open/scroll/Home/reopen/Home/final Close, and intentionally missing optional fonts/resources to expose fallback lookups. Require the same unmodified original application strict reviewer to PASS, zero unexpected I/O denials, and a reproducible scenario hash.
4. Reconcile dynamic observations to ELF `DT_NEEDED/PT_INTERP`, Lua literal/computed requires, fonts/locale and R26 static candidate graph. Treat absent syscall observations as **unknown**. Flag unresolved symlinks, ABI mismatches, and kernel/EPDC/boot/firmware dependencies as separate protected holds.
5. Deliver a machine-readable local-only path inventory and a publishable **summary-only coverage matrix**. Classify `OBSERVED_RUNTIME`, `STATIC_TRANSITIVE_CANDIDATE`, `KERNEL_OR_BOOT_HOLD`, `UNKNOWN_HOLD`, `PROPRIETARY_RESTRICTED`. Explicitly preserve every original stage file and all prior failed evidence.

An R40 pass, if later earned, will mean **observed runtime dependency evidence for the tested scenarios only**. It does not imply exhaustive dependencies, safe deletion, hardware-readiness, migration completeness, or independent Alpine bootability. If a future rootfs is built, create it separately from licensed and SHA-pinned inputs with a manifest; never prune stock Kindle userspace or original staged data in place.

**Immutable:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Research and educational purposes only.

## R40.0 first implemented gate: QEMU syscall-path observation

The release [R40.0 host-tested observer](../research/r40.0/README.md) packages the original SHA-pinned R39.4.11 release unchanged, re-runs independent R25/R39.4/R39.4.11 strict controls on the user's offline synthetic ARM/QEMU setup, then runs a **separate** replay under `qemu-arm -strace` in networkless, read-only Docker. It parses a private path-level syscall trace into guest-only application markers for the original strict reviewers and an **aggregate, filename-free** `R40-SUMMARY.json`. The fail-closed R40 reviewer re-parses the raw private trace rather than trusting the public summary. It tracks positive and negative file path syscalls; the trace is incomplete, does not attribute all file-backed mappings, cannot see all dynamically resolved resources or kernel requests, and **cannot justify file deletion**. Full R26 catalog reconciliation and additional workloads remain future work.

The shareable source ZIP has SHA-256 `bd26fae3bf9bd89f8d0133e1090a07496ceea334d6d7332c43d90c99de221999`, 115 entries including checksum manifest, all 114 payload hashes PASS; **602/602 host regressions PASS**. The full runnable source is in the verified user-conversation ZIP, not yet uploaded as standalone files in GitHub. **No R40 guest results exist at the time of this commit.**
