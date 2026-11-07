# R3877.5 — Native QEMU execution passed; ARMv7 BusyBox exit 127 (HOLD)

**Research/educational use only. NOT_BOOTABLE.**

## Observed on user's Mac (not in GitHub CI)

After verifying 254/254 host regression tests, the user ran the R3877.5 explicit QEMU test on AArch64 Colima. The cached official-signature-verified Alpine ARMv7 image and external AArch64 static QEMU helper were re-identified. A stopped preparation container successfully received QEMU. The runner committed it to a unique tagged derived image, **verified the derived image ID and ARMv7 platform using Docker JSON inspection**, created separate read-only guests and reported successful cleanup of helper, preparation, guest containers, **temporary tag, and exact derived image ID**. The original Alpine image ID remained unchanged.

- `qemu_version`: **PASS, exit 0**. This confirms an AArch64 executable QEMU can launch. It **does not** prove ARMv7 program execution.
- `busybox_help`: **HOLD, exit 127**, error family `UNCLASSIFIED_NONZERO_EXIT`. The runner failed closed at this first ARMv7 program test; BusyBox shell, uname and musl probes did not run. Actual QEMU diagnostic text was not exported by R3877.5; **the cause of exit 127 is unknown**.
- No original R13 stage, physical Kindle, firmware, binfmt registration, host mounts or guest networking were used. `NOT_BOOTABLE` persists.

A selected-field, explicitly **user-reported** record is stored in `USER-MAC-R3877-5-SELECTED-RESULT.json`. The raw complete Mac stdout/stderr has **not** been committed; GitHub does not run the user's Colima environment.

## Focused follow-up R3877.6 (Mac test pending)

The separate downloadable ZIP `pw3-r3877-6-qemu-guest-exit127-diagnostic.zip`, SHA-256 `f1e70eb204cb7fdde31f4e69f5f83e5527785a1ecb9c3f7a6c705ca04a74e749`, passed **274/274 authoring-host tests** (254 inherited and 20 new), 29 checksum entries and a clean-extraction test; the offline preflight returned exit 2. **No actual R3877.6 Colima guest execution has been reported.**

R3877.6 SHA-256 pins and reuses the **unchanged** R3877.5 runner `e462119e22151af5456c52c110b4e3a17d28df408cfcd4f80d877de9cd0c3166`. It intercepts the existing Docker guest-output results in memory, classifies the failure and exports a short paths-redacted excerpt. It adds **no guest commands** and does not alter tagged-image setup or cleanup. The original R3877.5 HOLD is retained as separate fields.

We should not modify the signed Alpine image, symlinks or musl interpreter based only on the 127 code. Capture the actual classified error first. Even a later ARMv7 QEMU pass would not verify a physical Kindle Linux 3.0.35 ABI/TLS, guest PT_INTERP placement, KOReader/glibc, device recovery or bootability. **NOT_BOOTABLE.**
