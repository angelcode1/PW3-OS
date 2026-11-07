# R3877.32 — Historical musl build-log command shapes

Research and educational use only. **NOT_BOOTABLE** remains immutable.

The Mac-local audit package `pw3-r3877-32-command-shape-audit.zip` was verified with 45 offline tests and checksum-clean extraction. It is available as a conversation artifact, not yet committed as Python source in this repository.

The audit checks the exact 1,644,394-byte R3877.30 log with SHA-256 `a8405a50c1849aebc0fefadcab4e4f7fa7da27d9c1296fa2ce46b73df56ca2ce`. R3877.31 reported 1,428 likely compile lines, one likely link line, and printed `-O2`, `-O3`, `-fPIC`, `-fno-asynchronous-unwind-tables`, `-fno-stack-protector`, and a musl soname flag. These are **log observations, not verified compiler identities**.

Expected R3877.32 result only if exact source checks and command-shape counts pass: `PASS_HASH_PINNED_BUILDLOG_COMMAND_SHAPES_ONLY`.

Mac command after extracting the ZIP:

```sh
cd ~/Downloads/pw3-r3877-32
shasum -a 256 -c SHA256SUMS_R3877_32.txt
python3 -B -m unittest -q test_r3877_31.py test_r3877_32.py
set -o pipefail
python3 -B pw3_r3877_32_log_command_shapes.py ~/Downloads/pw3-r3877-30/musl-armv7-build.log | tee r3877_32_result.json
printf 'R3877_32_EXIT_CODE=%s\n' "$?"
```

R3877.32 does not execute ARM code, run Docker, connect to Kindle, compile anything, or establish reproducible binary output. Printed commands alone cannot establish the historical toolchain versions, complete environment, or build output authenticity.
