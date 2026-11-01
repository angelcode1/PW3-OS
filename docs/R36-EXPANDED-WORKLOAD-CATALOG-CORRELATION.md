# R36 — local R26/R27/R35 expanded-workload catalog correlation

**2026-11-02:** The user confirmed **R35_GUEST_WORKLOAD_TRACE_CAPTURED** (real offline ARM/QEMU synthetic app workload, fresh R25/R32/R33/R34 strict reviewers PASS). R35 recorded **4,995** guest file path attempts and **1,007** successful open syscalls, versus R27's 2,262 attempts and 697 opens; **175 additional distinct successful-open lexical path strings**, of which **132 were stage-like**. These are not yet proven distinct staged regular-file counts.

**R36 USER-SIDE PASS**, as reported by the user: `R36_EXPANDED_WORKLOAD_CATALOG_CORRELATED`, with SHA-revalidated R26 catalog and private R27/R35 replay. The 31/31 host tests also passed. No rootfs mutation, boot or pruning. This gate maps verified private evidence to verified staged catalog entries, without altering the stage or claiming an Alpine boot.

## User-verified R36 results — 2026-11-02

The user ran R36 on their private evidence. It independently revalidated the **2,070**-entry R26 catalog, all staged hashes, R27/R35 raw trace vs observations, and the prior R28 mappings. The aggregate summary reports:

| Property | R27 startup trace | R35 combined workload |
|---|---:|---:|
| Distinct staged **regular files** with successful-open evidence | 341 | **472** |
| Files appearing in R27 but not R35 | — | **0** |
| **New** distinct cataloged regular files opened in R35 | — | **131** |
| Distinct cataloged regular files without successful-open evidence across either trace (`UNKNOWN_HOLD`) | | **976 / 1,448** |
| Successful guest opens (calls, not files) | 697 | 1,007 |

R35's 132 new *stage-like lexical strings* therefore correspond to **131 new cataloged regular files** under the conservative R28 lexical mapper; the difference must not be interpreted as a missing file without inspecting private records. R35 has nine ambiguous dirfd-relative events; directory-FD target/CWD and symlink resolution remain unproven. R35's 1,111 stage-looking absent-catalog lexical attempts include failures and are not evidence of missing required files.

The summary preserves `complete_dependency_closure_proven=false`, `files_unobserved_are_not_unused=true`, `safe_to_delete_inferred=false`, `guest_working_directory_resolution_proven=false`, `symlink_resolution_proven=false`, `new_rootfs_created=false`, `stage_rootfs_mutated=false`, and every boot, device, firmware and removal authorization false; `NOT_BOOTABLE`. No device action or deletion was performed.

R27 raw SHA `d02193b9b800fdc59cd7b7bf6367c7e2835e0afcfe0e1663ff0f6faa7e6ef49a`; R35 raw SHA `5a564aeea8ba6b46cf77e36dee86784afae8829ed772d4f2335f725dda8fdcbe`; stage sentinel SHA `7eb0d027b2b407fe6963ea9b9a1fe7fee1db96ae66f9399ece179238939176ed`.

**Next:** Add genuinely new ReaderUI opening/turning/return workloads with audited, ephemeral document settings and separate application-loop/event reviewers; then collect their guest path traces. Do not classify the 976 unobserved regular files as safe to remove.

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
