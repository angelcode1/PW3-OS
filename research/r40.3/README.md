# R40.3 — deduplicated absolute/relative stage opens and optional R26 SHA reconciliation

**2026-11-03: 38 host regressions PASS; user-side local stage runtime-open union PASS, observation only; R26 inventory SHA reconciliation NOT SUPPLIED. NOT_BOOTABLE.**

The user-verified R40.2 local crosswalk found 334 distinct regular staged files opened via verified relative paths and 17 previously observed absolute-path regular file opens from R40.1. The source-bound crosswalk contains 663 successful relative open-like events, 503 failed relative lookups, and a single observed PID with no detected cwd changes. **The two sets may overlap**; R40.3 computes their exact distinct union locally without exporting filenames.

Full runnable release ZIP: `pw3-os-r40.3-r26-union-audit.zip`, SHA-256 `929537cf51b897a2ca063df855c07a37998fbade99790dd85d5d86d44943046e`. ZIP CRC and its three SHA256SUMS-R403 source entries are verified. It contains `r403/union_inventory.py`, `tests/test_r403.py`, `README-R40.3.md`, and `SHA256SUMS-R403`. Python host suite: **38 PASS**, compile PASS. Original R40.1/2 and R39.4.11 source code is unchanged. This separate standalone utility is in the conversation ZIP, not yet as standalone files in GitHub.

The utility pins the exact user-supplied R40.2 SHA-256 values (public summary `cdac30dd46676de490d96a71af582135ca63ee0d9bb705ec0f895afcb652dd1b`; private crosswalk `e28a5f0d51b72545d931e4822099bc7db73d14d2fffcb555c941b4b783be3e41`). Both old R40.1 private crosswalk and source summary must remain local. An optional original R26 `R26-INVENTORY.json` can earn **hash-match evidence only** when the full stage path set, regular-file digests and symlink targets match a recognized schema; missing files, unsupported schemas or any mismatch stay on HOLD. Even matching hashes cannot authenticate a signed image or prove dependency closure.

Use the Mac instructions inside `README-R40.3.md` and upload **only `R40.3-UNION-SUMMARY.json`**, optionally `R40.3-R26-HASH-SUMMARY.json` if the R26 inventory exists. NEVER upload private R40.1 or R40.2 path reports, R26 raw inventory, QEMU logs or stage files. The tool does not execute staged files, follow symlinks, connect to a device, modify files or produce a pruning list.

**Immutable:** 976 original UNKNOWN_HOLD entries preserved; NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE. Research and educational purposes only.

## User-side R40.3 deduplicated union result (2026-11-03)

The user executed the unchanged R40.3 tool with its original R40.1 and R40.2 private crosswalks on the local R13 stage. Host suite: `Ran 38 tests ... OK`. Verdict: `R40_3_DEDUPLICATED_RUNTIME_STAGE_UNION_OBSERVED_NOT_CLOSED`. The exact observed-open union is **347 distinct staged regular files**, combining **17** previously observed absolute-path files and **334** distinct source-bound relative-path files with **4 overlapping filenames** (17 + 334 − 4 = 347). Of the **1,448** enclosing-stage regular files, **1,101** remain unobserved in the single synthetic scenario. The enclosing stage has **2,070** entries. The original R39.4.11 ARM PASS and R40.2 read-only crosswalk results were preserved.

No R26 input file was supplied, so `r26_manifest_status=NOT_SUPPLIED_HOLD`, `r26_static_inventory_hash_reconciled=false`, and `r26_provenance_authenticated=false`. The next action is to run the **existing** `r403/union_inventory.py --r26-inventory <local-R26-INVENTORY.json>` option with a fresh `R40.3-R26-HASH-SUMMARY.json` output, only if the original local R26 record is available. The ZIP's `README-R40.3.md` contains the complete command. Do not upload private paths or R26 raw inventory. If unavailable, retain the hold and do not manufacture or infer provenance.

These 347 observed-open files are not a complete dependency allowlist. Every file not observed, all 976 older `UNKNOWN_HOLD` entries, original firmware and boot assets remain protected. No pruning, stage mutation, device access, boot or firmware writes are authorized.
