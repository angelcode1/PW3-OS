# R40.4.1.1 — correction to source-bound R40.0.2 review pin

**Date: 2026-11-03. 47/47 host Python tests PASS. New FileManager-only QEMU/ARM scenario NOT YET RUN. NOT_BOOTABLE.**

## Root cause (independently reproduced)

The original R40.4.1 preflight was released with a **63-character SHA-256 constant**, `PIN_R4002_REVIEW=d23d2bf43d6995c9fee73dd096e081dfc934d3d82269b4ab36b556d394b9302` (missing final `f`). A valid SHA-256 is 64 lowercase hexadecimal characters. The independently verified original `R40-REVIEW.json` from the passing `R40.0.2-SHAREABLE-EVIDENCE.zip` hashes to `d23d2bf43d6995c9fee73dd096e081dfc934d3d82269b4ab36b556d394b9302f`. Hence the original preflight erroneously and invariably refused *both* the original and recovered legitimate public records, producing `ValueError: original R40 successful trace records changed`. No new Docker/QEMU runs occurred on the two user-reported preflight-refusal attempts.

The user's verified recovery tool next reported `R4002_ORIGINAL_ARCHIVE_AND_BOTH_PINNED_RECORDS_PASS` and `R4041_FRESH_PUBLIC_RECORDS_SHA256_PASS`, followed by `ValueError: installed R4041 preflight pin differs from audited R4002 source`. That secondary guard diagnosed this exact source defect.

## Corrective release and integrity

**Downloadable executable release:** `pw3-os-r40.4.1.1-preflight-pin-fix.zip`, SHA-256 `ed57a88705068ada02679c3793a7172c24ce494ffe5cbe1de90341f72971ebe4` (13 ZIP entries; all 12 `SHA256SUMS-R4041` file digests and ZIP CRC verified).

The **only changed source files** versus old R40.4.1 are `r4041/preflight.py` (adds the missing final `f`) and `tests/test_r4041.py` (3 regression tests for exact source hashes, 64-character length and rejecting the historical failed review). In addition the README and release checksum manifest are updated. The original R39.4 guard, new experimental guard, entrypoint, probe, collector, reviewer and Docker runner are byte-identical to the prior release; rootfs, R26 inventory, historical logs and private evidence remain untouched.

| File | SHA-256 of corrected release |
|---|---|
| `r4041/preflight.py` | `c0c2ca6727aced09e4704c0a53bfc823eb8c3ea9d7d47657f6e8ee8b39a20a0d` |
| `tests/test_r4041.py` | `3c4b05e52fe84dba00ebfd5d0bbcbdc21a4a4e143faad15c82794d4058176070` |
| `README-R40.4.1.md` | `16adc2e996b3867ddf3c0bb9178927f57ed7143d3d36a8d3fdf9082a152e4f46` |
| `SHA256SUMS-R4041` | `213ab06e6d8139c04ae6eb7cfc568e13287851e17608450117ab632288192aa5` |

See the [minimal corrective diff](PATCH-PREFLIGHT-PIN.diff). No integrity or safety validation was bypassed. Old broken R40.4.1 is retained as historical **PREFLIGHT_FAIL**, not an ARM result. The new R40.4.1.1 is **HOST_TESTED_ARM_PENDING**, not PASS for guest execution.

## Exact local steps

Use `README-R40.4.1.md` **inside the corrected release** for the full original eight-argument Docker command. Extract into the new `~/Downloads/pw3-os-r40.4.1.1-preflight-pin-fix` directory (not the original R40.4.1 directory), verify `SHA256SUMS-R4041` and run `python3 -m unittest discover -s tests -q` (expected: 47 tests). Use the already created `~/Downloads/pw3-os-r40.0.2-verified-shareable-records-r4041-clean` directory as the **third** runner argument. Use a fresh nonexistent output directory for the eighth argument. No repeat recovery is required.

If preflight still refuses, run the read-only `r4041/preflight.py` functions under an explicit local diagnostic to identify a **new** gate; do not modify source pin, old evidence, stage or result directories in place.

## Holds

No R40.4.1.1 offline FileManager-only ARM/QEMU run has been verified. `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. No file exclusion or rootfs edit is authorized. The 347 PDF-observed open and 1,101 unobserved counts remain from the **earlier** R40.0.2 scenario. The 976 historic `UNKNOWN_HOLD` entries are retained, as is the future optional puzzle-pack `NOT_BUILT_NOT_TESTED_HOLD`.

Research and educational purposes only.
