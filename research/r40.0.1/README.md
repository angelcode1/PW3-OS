# R40.0.1 — macOS canonical temporary path regression correction

**2026-11-03: host-tested source fix only; R40 ARM/QEMU remains PENDING; NOT_BOOTABLE.**

## User-side observed failure

The original R40.0 host test completed `Ran 602 tests ... FAILED (failures=1, skipped=3)`. The single failing case `tests/test_r40.py::R40Test.test_outside_output_pass` compared `check_paths(...)`'s **canonical** `/private/var/folders/.../NEW` against the **unresolved** `/var/folders/.../NEW` created by macOS `tempfile.TemporaryDirectory()`. Those strings refer to the same directory because macOS aliases `/var` to `/private/var`. The test mismatch does not establish a permission failure or an R40 ARM execution.

## Minimal change

R40.0.1 changes exactly the host test and release README, plus its rebuilt checksums. The assertion now compares against `str((Path(out)/'NEW').resolve())`. One new portable test creates an ordinary symbolic alias to a disjoint temporary directory and verifies that `check_paths` returns the canonical output path. The **production** `r40/check_inputs.py`, `run-r40-docker.sh`, guest probe, collector, reviewer and embedded R39.4.11 original source and strict reviewers are byte-for-byte unchanged. The path disjointness check, refusal to overwrite and refusal to use existing/special outputs are retained intact.

Full source ZIP (available in the research conversation): `pw3-os-r40.0.1-macos-canonical-path-fix.zip`; SHA-256 `5dbed5cf2fdc3074dfc7657c27da177650bf728e6d6c29df195f0719022a23db`. ZIP has 115 members; 114 SHA256SUMS-R40 payloads and ZIP CRC PASS. The only changed members relative to the original R40.0 ZIP are `tests/test_r40.py`, `README-R40.md` and `SHA256SUMS-R40`. `r40/check_inputs.py` SHA-256 `cf9206499dbd37328a5f5ad0a4558dc7d7bc08b51cd9eac988295367942a87f8` is unchanged.

Host Python: **603 tests executed/discovered, all OK** on Linux; Python compile and POSIX shell syntax PASS. The user must independently rerun on macOS to verify its `/var` alias case. There is no evidence yet of an R40 guest run, traced dependency summary, or exhaustive dependency closure.

## Mac execution

Extract into a fresh sibling source directory `~/Downloads/pw3-os-r40.0.1-isolated` rather than modifying `pw3-os-r40.0-isolated`. Then run:
```sh
cd "$HOME/Downloads"
SRC="$HOME/Downloads/pw3-os-r40.0.1-isolated"
mkdir -p "$SRC"
unzip -q pw3-os-r40.0.1-macos-canonical-path-fix.zip -d "$SRC"
cd "$SRC"
shasum -a 256 -c SHA256SUMS-R40
python3 -m unittest discover -s tests -q
```
On host PASS, use the original nine-argument `sh ./run-r40-docker.sh` command in the ZIP's README with the **new** source directory and distinct new output directory `~/Downloads/pw3-os-r40.0.1-observation-first-run`. Upload only the two aggregate JSON files, not private QEMU trace or path-level events.

The versioned patch [`PATCH-R40.0.1.diff`](PATCH-R40.0.1.diff) applies to the original R40.0 ZIP's `tests/test_r40.py`; the full runnable release, including original R39.4.11 files, is the research ZIP above. Preserve the old failed test report as historical evidence.

**Immutable:** NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE. Preserve all 976 UNKNOWN_HOLD stage entries. Research and educational purposes only.
