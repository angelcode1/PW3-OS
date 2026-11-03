# R40.4.2 — PDF vs FileManager-only staged-open comparison

**2026-11-03: Source-only host regression suite 46 PASS; user-side runtime set comparison PENDING. NOT_BOOTABLE.**

The user-supplied R40.4.1 final strict review PASS and R4041 counts-only summary are distinct from the earlier R40.0.2 PDF review PASS. The R40.4.1 summary has `guest_filemanager_only_reviewer_pass=false` intentionally set **before** the final strict reviewer; this is not a contradiction with the final review.

**Runnable release:** `pw3-os-r40.4.2-scenario-open-comparison.zip` SHA-256 `b34fa8a311089379f590bd844f21342ac1457fea6202aa50d76e580839a2107a`, containing `r4042/compare.py`, `tests/test_r4042.py`, `SCENARIO-MATRIX-R4042.json`, `README-R40.4.2.md`, and `SHA256SUMS-R4042`. ZIP integrity and all four payload SHA-256 manifests PASS. Full source and tests are supplied in the downloadable conversation ZIP; this GitHub milestone commits **provenance and instructions only**. The local audit has not run on the user's stage; do not claim a two-scenario distinct-file union until it does.

The tool replays the independent R40.4.1 reviewer, verifies its original raw QEMU events, rehashes all 2,070 R26 staged entries and reconciles the original R40.1/R40.2 PDF crosswalk with a separately source-bound FileManager-only path set. It refuses a working directory claim if trace process/CWD mutators, symlinks or fd ambiguity make it unsafe. Successful opens are **observed accesses**, not a proven complete loader closure. Only counts-only public `R40.4.2-SUMMARY.json` should be uploaded; the private comparison, raw trace, event records and R26 inventory stay local.

Use the exact Mac commands inside the release ZIP's `README-R40.4.2.md`. To locate the successful R40.4.1 run use `find "$HOME/Downloads" -maxdepth 3 -type f -name R4041-REVIEW.json -print`, select the output containing the accompanying private trace and events, and supply that as `--r4041-output`. Never reuse an old failed preflight output directory. Refuse existing output JSON paths; do not relax pins or create any pruning list.

**Baseline:** 347 distinct regular stage files opened in one PDF scenario, 1,101 previously unobserved among 1,448 stage regular files. Two-scenario overlap and union are **PENDING**. The 976 historical `UNKNOWN_HOLD` entries remain protected; the optional puzzle pack is still `FUTURE_OPTIONAL_NOT_BUILT_NOT_TESTED_HOLD`.

**Immutable:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Research/education only.

## User-side R40.4.2 two-scenario result (2026-11-03)

The user uploaded `R40.4.2-SUMMARY.json` (SHA-256 `58707ea78858dbab3fc0763adceee20bd83d9fa2e587fdeb3bf3711ba1cc3416`) together with the private comparison. Their exact set arithmetic and safety flags were locally validated without republishing any private path. The original R40.4.1 independent reviewer remains `R40_4_1_FILEMANAGER_ONLY_TRACED_ARM_PASS`; 2,407 path events reverified with one PID and no observed cwd mutators. Stage hashes revalidated for all 2,070 original R26 entries.

**Results:** PDF synthetic reopen observed **347** distinct regular staged files opened; FileManager-only synthetic startup/Close observed **338**; **338** in both; **9** PDF-scenario-exclusive; **0** FileManager-only-exclusive; **347** in two-scenario union; **1,101** of 1,448 staged regular files not observed opened in either scenario and all retained. In the private comparison the 9 scenario-exclusive entries are 7 Lua and 2 SVG assets; these **must not** be called exclusively PDF-engine dependencies because the scenarios have different plugin/UI lifecycles. The public summary key `filemanager_only_observed_open_regular=0` is *exclusive-set size*; it does not contradict `filemanager_only_r4041_distinct_stage_regular_opened=338`.

The previous `local_execution=PENDING` remains a historical checkpoint; the user-supplied local result supersedes it only for R40.4.2 post-processing. Replaying actual underlying private raw traces from the assistant environment is not claimed; the local comparison was source-bound to the original independent reviewer. `R40_4_2_TWO_SCENARIO_STAGE_OPEN_OBSERVATION_NOT_CLOSED` is the unchanged verdict. Decoder incomplete; no runtime-load completeness, deletion list, stage modification, firmware/boot access or independent hardware test.

**Next research gate:** choose a third *independent* offline scenario that exercises additional plugin behavior (Ink Away canvas/stroke/save/return), starting with exact local plugin API/source pinning and an audited UIManager path. Source mapping and test design do not themselves confer ARM PASS. EPUB/plain-text and missing-font/locale fallback remain `NOT_TESTED_HOLD`; optional puzzle package remains `NOT_BUILT_NOT_TESTED_HOLD`.
