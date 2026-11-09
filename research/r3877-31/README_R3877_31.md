# R3877.31 — Public Alpine ARMv7 musl build-log static evidence

**Research and educational use only. NOT_BOOTABLE is an immutable hold.**

R3877.30 succeeded at downloading and hashing the public log of `musl-1.2.6-r3` from `https://build.alpinelinux.org/buildlogs/build-3-24-armv7/main/musl/musl-1.2.6-r3.log`.

The user-reported file is **1,644,394 bytes** with SHA-256 `a8405a50c1849aebc0fefadcab4e4f7fa7da27d9c1296fa2ce46b73df56ca2ce`. This hash is user-reported, not signed by the builder; the raw log has not been inspected here.

The R3877.31 host-only diagnostic created in the accompanying research conversation verifies the exact file hash and byte count before reporting bounded observations: compiler-like commands, allowlisted ABI/optimization flags, log line numbers and version banner numbers, **never the raw lines**. It has 27 synthetic offline tests and is supplied as the downloadable `pw3-r3877-31-buildlog-evidence.zip` conversation artifact.

Run on the Mac after extracting that ZIP:

```sh
shasum -a 256 -c SHA256SUMS_R3877_31.txt
python3 -B -m unittest -q test_r3877_31.py
set -o pipefail
python3 -B pw3_r3877_31_buildlog_audit.py ~/Downloads/pw3-r3877-30/musl-armv7-build.log | tee r3877_31_result.json
printf 'R3877_31_EXIT_CODE=%s\n' "$?"
```

Expected classification **only if** hash and package marker match: `PASS_HASH_PINNED_PUBLIC_BUILDLOG_STATIC_EVIDENCE_ONLY`. No device access, compiler invocation or guest execution.

The parser archive is **not included in this repository commit**. The only committed code here is this methodology and the selected user-reported baseline. Do not equate CI-less source notes with passing a real R3877.31 log audit.

A log's references to GCC or flags cannot verify the exact historical toolchain executable and environment, cannot reproduce the signed loader, and cannot establish Kindle compatibility. Continue to refuse any installation, firmware write, boot or recovery claim.
