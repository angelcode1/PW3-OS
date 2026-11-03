# R40.0.2 — user-verified offline QEMU file observation

**Date:** 2026-11-03. **ARM/QEMU file-observation milestone: PASS for one synthetic workload.** This is not complete dependency closure or independent Alpine boot; **NOT_BOOTABLE**.

## Provenance

The user uploaded `R40.0.2-SHAREABLE-EVIDENCE.zip` (SHA-256 `9943750834796e62d14eba4949f2ba247242a69e35467bf254978c765e47b003`). ZIP CRC PASS. The ZIP contains `R40-SUMMARY.json` (SHA-256 `b8fdcf502fa791816430c528feae57237872932631a369b674f272352c3739e2`) and `R40-REVIEW.json` (SHA-256 `d23d2bf43d6995c9fee73dd096e081dfc934d3d82269b4ab36b556d394b9302f`). The latter agrees byte-for-byte with the user's separately uploaded passing `R40-REVIEW(1).json`. The standalone `R40-REVIEW.json` whose verdict is `FAIL` matches historical R40.0.1 evidence, and is **not** a contradiction or reinterpretation of the R40.0.2 passing ZIP.

The original R25 control and R39.4.11 source-bound application baseline PASS. During the traced replay, the **unchanged original R39.4 strict** and **separate R39.4.11** reviewers independently PASS. The R40.0.2 reviewer passes the independent trace/source/safety contract and reports `R40_OFFLINE_QEMU_FILE_OBSERVATION_PASS`.

## Summary counts (QEMU Linux-user strace)

| Metric | Observed |
|---|---:|
| Guest syscall lines | 8,356 |
| Decoded path operations | 2,713 |
| Successful path operations | 973 |
| Failed path operations | 1,740 |
| Unique successful path/syscall pairs | 505 |
| Unique failed path/syscall pairs | 1,594 |
| Undecoded file-syscall lines in recognized set | 0 |
| Lua/settings category successful calls | 555 |
| Lua/settings category failed calls | 1,393 |
| Shared-library category successful calls | 45 |
| Shared-library category failed calls | 127 |
| Font/locale/dictionary category successful calls | 83 |
| Font/locale/dictionary category failed calls | 17 |

The 1,740 failed operations may be intentional candidate/fallback lookups, not guest crashes. Each operation is **not** a unique loaded file, and a stat success is not an open; there may be omissions from QEMU's incomplete decoder. Raw QEMU stderr, guest stdout and the exact path-level private-event file are **not** in the shareable artifact; they remain on the user's Mac. The verified trace has no unexpected guest-stderr runtime error signals or displaced lifecycle markers.

## Next gate: R40.1

A separately host-tested [local stage-runtime crosswalk](../research/r40.1/README.md) matches only unambiguous absolute `/stage/rootfs/...` guest paths to an immutable local R13 stage using non-following `lstat`. It distinguishes successful opens from metadata lookups; unobserved, symlink and relative paths remain protected. It emits only a counts-only shareable summary and a private local path-level report. The crosswalk is **not yet user-executed** and is not a substitute for R26's full static inventory nor independent scenario coverage.

R40.0.2 release SHA-256: `059575b538aa1422e0e895b1848a3d7d537e80ab644bcaf7cdb97214ada7f685`. 628 Linux host regressions PASS for the release; user-side Mac ARM trace PASS as above.

**Immutable:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Preserve the 976 earlier `UNKNOWN_HOLD` entries. Do not delete stock firmware or stage files. Research and educational purposes only.
