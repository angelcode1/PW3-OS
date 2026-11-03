# R40.3 — deduplicated absolute/relative stage opens and optional R26 SHA reconciliation

**2026-11-03: 38 host regressions PASS; Mac stage execution PENDING; NOT_BOOTABLE.**

The user-verified R40.2 local crosswalk found 334 distinct regular staged files opened via verified relative paths and 17 previously observed absolute-path regular file opens from R40.1. The source-bound crosswalk contains 663 successful relative open-like events, 503 failed relative lookups, and a single observed PID with no detected cwd changes. **The two sets may overlap**; R40.3 computes their exact distinct union locally without exporting filenames.

Full runnable release ZIP: `pw3-os-r40.3-r26-union-audit.zip`, SHA-256 `929537cf51b897a2ca063df855c07a37998fbade99790dd85d5d86d44943046e`. ZIP CRC and its three SHA256SUMS-R403 source entries are verified. It contains `r403/union_inventory.py`, `tests/test_r403.py`, `README-R40.3.md`, and `SHA256SUMS-R403`. Python host suite: **38 PASS**, compile PASS. Original R40.1/2 and R39.4.11 source code is unchanged. This separate standalone utility is in the conversation ZIP, not yet as standalone files in GitHub.

The utility pins the exact user-supplied R40.2 SHA-256 values (public summary `cdac30dd46676de490d96a71af582135ca63ee0d9bb705ec0f895afcb652dd1b`; private crosswalk `e28a5f0d51b72545d931e4822099bc7db73d14d2fffcb555c941b4b783be3e41`). Both old R40.1 private crosswalk and source summary must remain local. An optional original R26 `R26-INVENTORY.json` can earn **hash-match evidence only** when the full stage path set, regular-file digests and symlink targets match a recognized schema; missing files, unsupported schemas or any mismatch stay on HOLD. Even matching hashes cannot authenticate a signed image or prove dependency closure.

Use the Mac instructions inside `README-R40.3.md` and upload **only `R40.3-UNION-SUMMARY.json`**, optionally `R40.3-R26-HASH-SUMMARY.json` if the R26 inventory exists. NEVER upload private R40.1 or R40.2 path reports, R26 raw inventory, QEMU logs or stage files. The tool does not execute staged files, follow symlinks, connect to a device, modify files or produce a pruning list.

**Immutable:** 976 original UNKNOWN_HOLD entries preserved; NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE. Research and educational purposes only.
