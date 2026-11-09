# R3877.51.2 live Kindle config decoder HOLD; R3877.51.3 follow-up

**User-reported source:** password-authenticated SSH read-only selected-line receipt from running PW3 Kindle; prior R3877.51.2 Mac-local parser.

**Live kernel:** `3.0.35-lab126`, ARMv7 (`armv7l`).
**Live symbol names:** 14/14 present in `/proc/kallsyms` (no addresses published).
**Kernel config:** `/proc/config.gz` **readable** but `zcat`, `gzip`, `gunzip` and `busybox zcat` reported **TOOL_ABSENT** in R3877.51.2. Config decoder `NONE`; 18/18 selected config flags remain `UNKNOWN`.
**R3877.51.2 result:** `HOLD`, `LIVE_KERNEL_CONFIG_READABLE_BUT_DECODE_FAILED`, exit 2.

This does **not** imply the kernel config is missing or that any syscall implementation is absent. The next offline step is a one-shot, read-only `cat /proc/config.gz` transfer via the already-known password-authenticated Kindle SSH session, followed by **Mac-local** bounded gzip decode, CRC verification, SHA-256 logging, allowlisted selected Kconfig values, and comparison to the pinned prior 14-symbol receipt. No new binaries on the Kindle, no raw kernel config in GitHub.

The separately distributed R3877.51.3 ZIP includes the complete local host-only parser, 28 synthetic unit tests, sanitized receipt fixture, safety checks, and runbook. **The executable source and tests are not yet committed to this repository**, and GitHub CI for R3877.51.3 has not run.

The running kernel's exact binary provenance, full syscall dispatch, musl Linux 3.0.35 compatibility, KOReader ABI, and recovery remain unverified. **`NOT_BOOTABLE` remains immutable.**
