# R40.2 — source-bound working-directory crosswalk (host-only trial)

**2026-11-03: user-side R40.2 local stage crosswalk PASS (observation only); 32 host tests PASS; `R40_2_SOURCE_BOUND_CWD_CROSSWALK_OBSERVED_NOT_CLOSED`. NOT_BOOTABLE.**

## Verified R40.1 input

The user ran the original R40.1 host tests successfully, then reconciled the original *private* QEMU trace against `stage-r13-fixed/rootfs` using `r401/reconcile.py`. Public verdict: `R40_1_STAGE_RUNTIME_CROSSWALK_OBSERVED_NOT_CLOSED`, 2,713 operations, 2,067 rootfs entries (1,446 regular files; 286 directories; 335 symlinks). Only 17 distinct staged regular files were directly observed through successful open-like operations. **752 successful relative operations, 503 failed relative operations** were not mapped; these remain essential unknown/hold evidence, not safe-removal candidates. Original R40.0.2 trace PASS and source pins remained intact; R26 static hash reconciliation is false. R26's 2,070 total may use the enclosing stage directory rather than the rootfs child.

## R40.2 new local-only experiment

The original source-pinned R40.0.2 probe `r40/probe_trace_in_container.sh` SHA-256 `646461eb9b61303acc0b0d6237c1c786d909d5f7d90f0952156a96346e318607` first executes `cd /stage/rootfs/opt/koreader-compat/app`. The pinned original R40 collector `r40/collect.py` SHA-256 `e7debc070b150d5df8b40bd7a58e66b252ccb68cce381642b8f30f462347b2fe` decodes original QEMU guest syscall stderr; R40.1 `r401/reconcile.py` SHA-256 `1f9c4f2d244b8eb68a74d1ecf1c4a7cf490bdd5164736ef2e9f145ab151a030e` inventories the same stage without following symlinks.

The new `r402/reconcile_cwd.py` requires these three exact source pins, the original R40.0.2 SHA-pinned passing public outputs, the original private raw syscall log and R40 private event list, and both R40.1 private/public results. It recalculates the syscall sequence and matches the R40.1 path observations. It provisionally maps a relative pathname from the pinned starting cwd only if all observed guest syscall lines have exactly one PID, **no recorded working-directory/process mutators**, and the cwd and ancestor components are original non-symlink stage directories. Non-`AT_FDCWD` dirfds, symlink prefixes, escaped paths, multi-path syscalls and outside-stage targets remain unresolved. Because QEMU's syscall decoder is incomplete, absence of a recorded mutation is **not** proof of a complete runtime history. Public output records only source-conditional counts; path-level records are private and created mode 0600.

The optional rootfs-parent comparison checks whether the enclosing stage metadata-only entry count agrees with R26's reported 2,070. It **does not** claim R26 hash-by-hash matching, full dependency closure or safe deletion.

## Host artifact and integrity

Release: `pw3-os-r40.2-source-bound-cwd-crosswalk.zip`, SHA-256 `9f360078541fa58ef449f00d5caf3fe8ec97120d438948ba821cf405b1bfda1a`. **6 ZIP entries**, 5 SHA256SUMS-R402 verified payloads, CRC PASS. `r402/reconcile_cwd.py` SHA-256 `44f4f94e350f6bc0403131314c688cc611b1e9211ad04e11b5b2c524738942b5`; tests SHA-256 `ba57def7e65a8f03399f867ad0a0e90d9b68d56cbf784797688c241802955451`; **32/32 host tests PASS** and Python syntax PASS. No new Docker/ARM run needed; existing private R40.0.2 trace is the source. The ZIP provides full runnable source, copies of the pinned R40 and R40.1 collectors for reproducible host regression, plus a complete Mac command.

The user should extract `pw3-os-r40.2-source-bound-cwd-crosswalk.zip` into an isolated source subdirectory, validate `SHA256SUMS-R402`, run `python3 -m unittest discover -s tests -q`, then run the command in its `README-R40.2.md` against local R40.0.2 source/output and R40.1 source/private/public evidence. Upload **only** `R40.2-SUMMARY.json`; keep private raw logs, events and path-level records local. The new result is still an **observed-not-closed** claim and not a list of safe-to-prune files.

**Immutable:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Preserve the original 976 unknown-hold stage entries, all symlinks and all unobserved paths. Research and educational purposes only.

## Actual R40.2 user-side results — 2026-11-03

The user ran the host suite (32 PASS) and original local-only crosswalk. The uploaded public summary SHA-256 is `cdac30dd46676de490d96a71af582135ca63ee0d9bb705ec0f895afcb652dd1b`, and its private crosswalk SHA-256 is `e28a5f0d51b72545d931e4822099bc7db73d14d2fffcb555c941b4b783be3e41`. Those reports agree on event/classification/open counts and all no-removal restrictions. The private report, including original paths, is **not committed**.

The source-bound cwd run recorded one guest PID, zero observed cwd/process mutators, and a non-symlink working-directory chain. It checked **1,255 relative path operations**: 725 successful regular-stage path matches, 27 successful directory operations, and 503 failed missing-path lookups. Among the regular successes, **663 were successful open-like operations spanning 334 distinct staged regular files**. R40.1 had previously observed 17 distinct regular files through direct absolute paths. Those sets have not yet been deduplicated; 334 + 17 is **not** a proven distinct count. R26 outer-stage count agrees (2,070), with 2,067 entries inside rootfs, including 1,446 regular files, 286 directories and 335 symlinks. **R26 hash reconciliation remains false**, and QEMU guest syscall decoding remains incomplete.

The next host-only [R40.3](../r40.3/README.md) examines the private absolute/relative union and optionally checks the original R26 inventory hash-by-hash. It does not permit pruning or booting.
