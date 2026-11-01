# R38.2.1 — gate-label repair; optional read-only retrospective reviewer

**2026-11-02 verified:** User ran **79/79 R38.2.1 host tests PASS** and the pinned retrospective reviewer returned **`R38_2_EXISTING_ARM_EVIDENCE_GATE_RECONCILED`** on the original R38.2 local evidence. Original R38.2 strict reviewer remains **FAIL** because the shipping runner printed the old `R38_1_...` marker. **No new ARM execution occurred.** The user's reconciliation confirmed the source hashes and one-marker-only substitution before applying unchanged strict R38.2 review logic in memory. Genuine temporary per-book settings migration/roundtrip is supported by the original ARM run and this independent retrospective gate; full ReaderUI remains unverified.

## Confirmed user-side reconciliation of the original ARM run

The user completed the new R38.2.1 host suite (`Ran 79 tests … OK`), then ran `r38/reconcile_existing.py` with the original R38.2 release, existing R38.2 results and a fresh output path. Actual verdict: **`R38_2_EXISTING_ARM_EVIDENCE_GATE_RECONCILED`**; `reconciliation_status=PASS`.

The resulting JSON explicitly records:

- `original_release_sources_sha256_revalidated=true`
- `original_runtime_log_sha256=d1c4ef49f0e576db959aaeec171060cf20e134b2219a361e992ac41ca38938ad`
- `original_user_side_r38_2_reviewer_verdict=FAIL` (historical, unchanged)
- `original_failure_was_pinned_release_gate_marker_mismatch=true`
- `exact_old_to_new_marker_substitution_in_memory_only=true`
- `corrected_r38_2_strict_reviewer_in_memory_pass=true`
- `genuine_per_book_migration_execution_supported=true`
- `exact_temp_sidecar_file_reloaded_supported=true`
- `loader_guard_restoration_supported=true`
- `fresh_r25_r32_r33_reviews_verified=true`
- `original_log_unchanged=true`, `new_arm_execution_performed=false`

All boot/device/firmware/file-removal flags remain false, `NOT_BOOTABLE`. In particular, `full_reader_ui_document_open_verified=false`, `page_navigation_verified=false`, `global_startup_migrations_executed=false` and `complete_dependency_closure_proven=false` are preserved. This resolves a **reviewer release-marker inconsistency**, not the separate, harder UI workflow and hardware questions.

## Evidenced R38.2 runtime facts

The provided log recorded genuine `DocSettings:open`, legacy CRe margin and space-condensing migration, successful temporary sidecar flush, scoped one-file metadata loader install, exact sidecar parse, exact `source_candidate`, unique token/data recovery through a fresh real `DocSettings:open`, scoped loader restoration, and normal R25 UIManager Close + Generic exit. All three original R25/R32/R33 fresh reviewer JSON files returned PASS. The original R38.2 reviewer reported `FAIL`, with sole error `missing or duplicated marker: R38_2_TEMP_DOCSETTINGS_MIGRATION_ARM_GATE_PASS`.

The bug is provable in the original package source: `r38/probe_in_container.sh` SHA-256 `9f6031213489babd982cd8804adb173768ba1e5d63aabc1ceec5802bf95963bd` prints the R38_1 label; the unchanged original `r38/review_r38.py` requires R38_2. The Docker image's printed `sha256:e245...` is not an archive SHA.

## Surgical source correction

R38.2.1 changes **only** the success and failure label strings in `r38/probe_in_container.sh` from `R38_1_TEMP_DOCSETTINGS_MIGRATION_ARM_GATE_` to `R38_2_TEMP_DOCSETTINGS_MIGRATION_ARM_GATE_`. Corrected script SHA-256 `d3b031a0cde08116b3b578eedc2e96c8aa507c6295bfc006cb29b495e66df3f5`. Genuine KOReader, the R25 guard, R32/R33 fixtures, the synthetic Lua migration/sidecar handler, source pins, source-audit scripts, Docker restrictions and all strict reviewers remain unchanged. New regression tests verify the marker contract and reject unrelated runtime failures.

Source ZIP: `pw3-os-r38.2.1-gate-marker-repair.zip`, SHA-256 **`4c9f122d3c4cc81162fbc5943c921a4ee7d9db6a0cdd74dba62e92de2e4a4b77`**. ZIP integrity and **15 internal SHA-256 payload hashes** checked; 79/79 host tests PASS, shell/Python syntax PASS. The source-only ZIP contains no actual Kindle firmware or rootfs.

## Preferred: retrospective verification on the unchanged existing R38.2 result

The new `r38/reconcile_existing.py` requires the **original R38.2 release** and **original R38.2 results**. It verifies the original payload SHA-256 manifest and release source hashes, the original R38 reviewer FAIL reason *exactly*, the old gate as the final and only such log line with no traceback/failure marker, and all three existing R25/R32/R33 reviewer PASS plus original source preflight. It then makes **one gate-label substitution in memory only** and calls the unchanged strict R38.2 reviewer on that volatile string. It emits a separate, aggregate-only JSON into a **new** path and leaves the original log and reviewer FAIL unchanged.

```sh
cd ~/Downloads
unzip pw3-os-r38.2.1-gate-marker-repair.zip
cd pw3-os-r38.2.1-gate-marker-repair
python3 -m unittest discover -s tests -v
python3 r38/reconcile_existing.py \
  --original-release "$HOME/Downloads/pw3-os-r38.2-scoped-sidecar-loader-fix" \
  --results "$HOME/Downloads/pw3-os-r38.2-temporary-docsettings-first-run" \
  --out "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json"
cat "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json"
```

**Expected only if the real local evidence matches:** `R38_2_EXISTING_ARM_EVIDENCE_GATE_RECONCILED`. This is a *retrospective review*, NOT a new ARM execution and NOT an alteration of the original R38.2 strict FAIL. No fake corrected-marker line is written to the original log. Failure to meet any pin, fresh reviewer, marker, data or safety invariant must return FAIL.

## Optional: independent corrected-run official gate

To see `R38_2_TEMP_DOCSETTINGS_MIGRATION_ARM_PASS` emitted by a real new guest run and accepted by the original strict R38.2 reviewer, rerun **this corrected package** with its original 9 arguments, and a **new** results directory (e.g. `$HOME/Downloads/pw3-os-r38.2.1-temporary-docsettings-first-run`). Full command is included in the archive's `README-R38.2.1.md`. Do not overwrite original R38, R38.1 or R38.2 evidence.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. Genuine full ReaderUI instance creation, page navigation, complete dependency closure, physical e-ink, boot and rootfs pruning remain unverified.