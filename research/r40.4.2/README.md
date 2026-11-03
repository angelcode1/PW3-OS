# R40.4.2 — PDF vs FileManager-only staged-open comparison

**2026-11-03: Source-only host regression suite 46 PASS; user-side runtime set comparison PENDING. NOT_BOOTABLE.**

The user-supplied R40.4.1 final strict review PASS and R4041 counts-only summary are distinct from the earlier R40.0.2 PDF review PASS. The R40.4.1 summary has `guest_filemanager_only_reviewer_pass=false` intentionally set **before** the final strict reviewer; this is not a contradiction with the final review.

**Runnable release:** `pw3-os-r40.4.2-scenario-open-comparison.zip` SHA-256 `b34fa8a311089379f590bd844f21342ac1457fea6202aa50d76e580839a2107a`, containing `r4042/compare.py`, `tests/test_r4042.py`, `SCENARIO-MATRIX-R4042.json`, `README-R40.4.2.md`, and `SHA256SUMS-R4042`. ZIP integrity and all four payload SHA-256 manifests PASS. Full source and tests are supplied in the downloadable conversation ZIP; this GitHub milestone commits **provenance and instructions only**. The local audit has not run on the user's stage; do not claim a two-scenario distinct-file union until it does.

The tool replays the independent R40.4.1 reviewer, verifies its original raw QEMU events, rehashes all 2,070 R26 staged entries and reconciles the original R40.1/R40.2 PDF crosswalk with a separately source-bound FileManager-only path set. It refuses a working directory claim if trace process/CWD mutators, symlinks or fd ambiguity make it unsafe. Successful opens are **observed accesses**, not a proven complete loader closure. Only counts-only public `R40.4.2-SUMMARY.json` should be uploaded; the private comparison, raw trace, event records and R26 inventory stay local.

Use the exact Mac commands inside the release ZIP's `README-R40.4.2.md`. To locate the successful R40.4.1 run use `find "$HOME/Downloads" -maxdepth 3 -type f -name R4041-REVIEW.json -print`, select the output containing the accompanying private trace and events, and supply that as `--r4041-output`. Never reuse an old failed preflight output directory. Refuse existing output JSON paths; do not relax pins or create any pruning list.

**Baseline:** 347 distinct regular stage files opened in one PDF scenario, 1,101 previously unobserved among 1,448 stage regular files. Two-scenario overlap and union are **PENDING**. The 976 historical `UNKNOWN_HOLD` entries remain protected; the optional puzzle pack is still `FUTURE_OPTIONAL_NOT_BUILT_NOT_TESTED_HOLD`.

**Immutable:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Research/education only.
