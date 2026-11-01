# R38.2.1 — gate-label repair; optional read-only retrospective reviewer

**2026-11-02:** User's original R38.2 ARM/QEMU runtime completed all expected genuine application checkpoints and its fresh R25/R32/R33 reviewers PASS. The original strict R38.2 reviewer **FAILed** solely because the shipping container probe printed `R38_1_TEMP_DOCSETTINGS_MIGRATION_ARM_GATE_PASS`, whereas the reviewer required `R38_2_TEMP_DOCSETTINGS_MIGRATION_ARM_GATE_PASS`. **Original review remains FAIL.** The separate repaired source-only R38.2.1 package passed **79/79 host tests** (includes the 60 original R38.2 tests and 19 new gate/reconciliation regressions); R38.2.1 has NOT run on user's ARM/QEMU yet.

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