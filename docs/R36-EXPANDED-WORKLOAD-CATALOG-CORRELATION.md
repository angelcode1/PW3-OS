# R36 — local R26/R27/R35 expanded-workload catalog correlation

**2026-11-02:** The user confirmed **R35_GUEST_WORKLOAD_TRACE_CAPTURED** (real offline ARM/QEMU synthetic app workload, fresh R25/R32/R33/R34 strict reviewers PASS). R35 recorded **4,995** guest file path attempts and **1,007** successful open syscalls, versus R27's 2,262 attempts and 697 opens; **175 additional distinct successful-open lexical path strings**, of which **132 were stage-like**. These are not yet proven distinct staged regular-file counts.

**R36 source-only tool is host tested (31/31 synthetic tests PASS); user-side R36 run pending.** This gate maps verified private evidence to verified staged catalog entries, without altering the stage or claiming an Alpine boot.

## Evidence and privacy boundary

The conversation archive `pw3-os-r36-expanded-catalog.zip` has SHA-256 **`22983384a0e16d3d8d6ec4f4a0e4351b73d59d28c02f9a2f3b2253f55916a370`**. ZIP integrity and five internal payload hashes PASS. Python standard library only; no QEMU, Docker or staged binary execution. Original private traces and filenames were not uploaded to GitHub.

R36:

1. Rechecks the unchanged R13 stage sentinel, the entire R26 inventory and all staged regular-file hashes (without following symlinks), as the verified R28 algorithm did.
2. Reconstructs every R27 and R35 guest path syscall attempt from **both actual private raw trace files**, cross-checking original private observations and published aggregate counts, stage/trace SHA-256s and the R35 lexical deltas.
3. Recomputes the old R28 positive-open cohort, requiring it to match the already user-verified R28 summary.
4. Uses the **frozen, SHA-pinned R28 mapper** without altering its conservative handling of relative `openat`/dirfd calls. QEMU guest initial working directory and symlink resolution remain unproven, so no extra path assumption is permitted.
5. Partitions 1,448 regular staged files into positive-open cohorts `observed_in_both`, `r27_only_observed`, `r35_only_newly_observed`, and `unobserved_in_both_UNKNOWN_HOLD`. All 335 symlinks and 287 directories remain held. These categories describe *only two synthetic workloads*, not a safe-to-delete list.
6. Emits one shareable aggregates-only `R36-SUMMARY.json` and one **PRIVATE** per-file `R36-CATALOG.PRIVATE.json` into a fresh 0700 results directory. Rejects old/existing output paths or writes under the stage. No device access, firmware modifications, executable rootfs, new Alpine stage, actual PW3 boot or file removal.

The 31/31 synthetic tests cover modified stage contents/modes, extra catalog objects, altered raw traces or observation ordering, forged summary deltas, fake boot/file-removal claims, AT_FDCWD ambiguity, non-stage paths, failed opens, malformed R28 prior reference, output collisions and absent positive evidence. **These host tests are not user-side R36 results.**

## Run on user's Mac (no Docker, stage execution or network needed)

```sh
cd ~/Downloads
unzip pw3-os-r36-expanded-catalog.zip
cd pw3-os-r36-expanded-catalog
python3 -m unittest discover -s tests -v

python3 r36/compare.py \
  --stage "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  --r26-inventory "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-INVENTORY.json" \
  --r26-summary "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-SUMMARY.json" \
  --r27-observations "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-OBSERVATIONS.PRIVATE.json" \
  --r27-summary "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-SUMMARY.json" \
  --r27-trace "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-QEMU-GUEST-SYSCALLS.PRIVATE.log" \
  --r28-summary "$HOME/Downloads/pw3-os-r28-correlation-first-run/R28-SUMMARY.json" \
  --r35-observations "$HOME/Downloads/pw3-os-r35-workload-trace-first-run/R35-OBSERVATIONS.PRIVATE.json" \
  --r35-summary "$HOME/Downloads/pw3-os-r35-workload-trace-first-run/R35-SUMMARY.json" \
  --r35-trace "$HOME/Downloads/pw3-os-r35-workload-trace-first-run/R35-QEMU-GUEST-SYSCALLS.PRIVATE.log" \
  --out "$HOME/Downloads/pw3-os-r36-catalog-first-run"

cat "$HOME/Downloads/pw3-os-r36-catalog-first-run/R36-SUMMARY.json"
```

**Expected verdict only after user run:** `R36_EXPANDED_WORKLOAD_CATALOG_CORRELATED`. Share the *summary only*; all private path reports and raw traces stay on Mac. The result will be **guest lexical positive evidence**, never a fully resolved dependency closure.

## After R36

Revisit genuine ReaderUI instance lifecycle with a separate synthetic event contract, while rigorously auditing the per-document migration boundary. Then gather additional guest traces and consider a fresh, minimal Alpine userspace assembled from permitted audited inputs; no original Kindle or stage files may be pruned.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.
