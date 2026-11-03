# PW3-OS R40.4.1 — independent FileManager-only QEMU trace

**2026-11-03: HOST TESTS PASS (44); ARM/QEMU FILEMANAGER-ONLY PENDING. NOT_BOOTABLE.**

## Why this follows R40.4.0

The user's Mac ran R40.4.0 successfully: 62 Python host tests passed, R26 2,070 stage entries rehashed, all 83 ELF objects parsed, 823 Lua files scanned, 209 ELF DT_NEEDED candidate edges and 6,272 Lua lexical candidate edges. None prove that a dependency loaded in the tested workload. The prior R40.0.2 same-session two-PDF runtime observation remains PASS but is a **different scenario**.

R40.4.1 prepares a separate **genuine FileManager-only** startup and Close workload, retaining the 976 older UNKNOWN_HOLD and 1,101 PDF-unobserved regular-stage-file holds. Ink Away plugin ownership is exercised but **its canvas/stroke/save workflow is not tested**. The future optional puzzle pack remains **not built and untested**.

## Tested new source archive

`pw3-os-r40.4.1-filemanager-only.zip`, conversation download, SHA-256 **`0e8600ba4c36449ba633d8c167cb64ebe15b9539304a77bc4d71329d63c6ca18`**. 13 ZIP entries; 12 verified SHA256SUMS-R4041 entries; CRC PASS; **44 Python host regression tests PASS**, Python compilation and POSIX shell syntax PASS. No R40.4.1 guest run or real Kindle access occurred in preparation.

**Reproducible experiment:** original `research/r39.4.11/r394/loop_guard.lua` SHA-256 `e7f1d0872f91b1ddfac42f9d7f35309072293d9dd551ad5543c455a1bebf88a7`, left unchanged. The committed [`PATCH-R40.4.1.diff`](PATCH-R40.4.1.diff) reproduces the separate 89,568-byte experimental guard (`r4041/loop_guard.lua`, SHA-256 `edc504d11495942f0f82fff9d443abdd17c7b96f6ea4ad63f8a9b253cbcd4020`) with a strictly bounded first genuine FileManager startup, synthetic UIManager Close, true stock Generic exit and post-exit verification. **Never apply the patch in place to the original R39.4.11 source or the R13 stage.** The independent entrypoint and guest probe are also committed in `r4041/`.

The **complete runnable preflight, Docker runner, collector, independent strict reviewer and 44-test suite are in the checksum-verified release ZIP**; they are not all separate GitHub files in this commit. No claim that the R40.4.1 experimental guest is proved working until the user supplies a new traced run.

## Mac commands

```sh
cd "$HOME/Downloads"
SRC="$HOME/Downloads/pw3-os-r40.4.1-filemanager-only"
mkdir -p "$SRC"
unzip -q pw3-os-r40.4.1-filemanager-only.zip -d "$SRC"
cd "$SRC"
shasum -a 256 -c SHA256SUMS-R4041
python3 -m unittest discover -s tests -q
```

Offline QEMU trial uses *the original local paths* to the prior source and private verification evidence, without accessing a physical Kindle:

```sh
sh ./run-r4041-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  "$HOME/Downloads/pw3-os-r40.0.2-isolated" \
  "$HOME/Downloads/pw3-os-r40.0.2-split-first-run" \
  "$HOME/Downloads/pw3-os-r40.4.0-static-dependency-graph" \
  "$HOME/Downloads/R40.4.0-SUMMARY.json" \
  "$HOME/Downloads/R40.4.0-PRIVATE-STATIC-GRAPH.json" \
  "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-INVENTORY.json" \
  "$HOME/Downloads/pw3-os-r40.4.1-fm-only-first-run"
```

Share only `R4041-SUMMARY.json` and `R4041-REVIEW.json`, generated in the new output directory. The private raw trace, app log, guest stdout, path-level event report, R26 inventory and R40 static graph must remain on the Mac. If the run fails, preserve it as FAIL and do not repeat in place: any retry requires fresh output. The reviewer requires source-pinned real FileManager + plugin startup, exactly one genuine UIManager Close, zero denials, strict cleanup, nonzero syscall evidence, independent QEMU exit zero and a shell-only post-exit marker. It must reject any PDF lifecycle/ReaderUI opening.

**Unchanged:** `NO_DEVICE_ACCESS`, `NO_FIRMWARE_WRITES`, `NO_HARDWARE_ACTIONS`, `NO_BOOT`, `NO_PRUNING`, `NOT_BOOTABLE`; R40.0.2 and R39.4.11 original success histories unchanged. Research and educational purposes only.

## Historical source pin defect (R40.4.1 old release)

The user confirmed the R40.4.1 preflight refused twice before Docker execution. Root cause: released `PIN_R4002_REVIEW` was mistakenly **63 hex characters** (missing the final `f`), so it could not equal a genuine SHA-256. This was an erroneous **preflight** fail, not evidence corruption or an ARM trial failure. A separately versioned [R40.4.1.1 correction](../r40.4.1.1/README.md) fixes the sole preflight pin typo and adds 3 host regressions (47 PASS). Both historical failed preflights are retained as evidence. Old R40.4.1 source remains unchanged; no QEMU scenario PASS has been claimed.
