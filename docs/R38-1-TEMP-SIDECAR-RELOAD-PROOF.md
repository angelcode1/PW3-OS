# R38.1 — exact temporary sidecar and genuine fresh DocSettings reload proof

**2026-11-02 update:** **R38.1 USER ARM/QEMU FAIL** at `migrate_sidecar.lua:79: R38.1 exact saved metadata could not be loaded from temp file`. The log reached genuine per-book migration and temporary sidecar flush but did not prove valid saved metadata or reload. The pinned R25.3 `dofile` allowlist was found to deliberately reject this new sidecar path, and R38.1 caught that denial inside `pcall`. **R38.2** applies a time-limited, single-path temp metadata exception, restores the R25 guard, and has **60/60 host tests PASS; ARM/QEMU pending**. See [R38.2](R38-2-SCOPED-SIDECAR-LOADER.md).

## Actual user-side R38.1 failure

The user-supplied log showed genuine startup, Ink Away save/reload, MuPDF PDF and CREEngine EPUB memory rendering, `R38_GENUINE_DOCSETTINGS_OPENED_TEMP_ONLY`, genuine CRe margin/space-condensing migration, `R38_GENUINE_DOCSETTINGS_MIGRATION_IN_MEMORY` and `R38_GENUINE_DOCSETTINGS_SIDECAR_FLUSHED_TO_TEMP`. It then failed at:

```text
/r38/migrate_sidecar.lua:79: R38.1 exact saved metadata could not be loaded from temp file
R38_1_TEMP_DOCSETTINGS_MIGRATION_ARM_GATE_FAIL (exit=1)
```

All four fresh reviewer JSON files returned `FAIL` because R25's event-loop marker was never reached. Prior separate R25–R37 proof remains valid. The original R38 and R38.1 failed outputs are preserved separately.

Source analysis revealed a **harness incompatibility**, not proven metadata corruption: the SHA-pinned R25.3 `loop_guard.lua` defines its own `dofile` function with exact allowlisted sources, and all other paths go through `deny('DOFILE:'..path)`. The newly generated `/tmp/r25-ko-home/library/r33-original.sdr/metadata.epub.lua` is not allowlisted. Since R38.1 does `pcall(dofile,filename)`, the deny is caught and the original generic assertion fires. The later genuine `DocSettings:open` would hit the same gate. A corrected, narrowly-scoped temporary metadata loader is now documented in [R38.2](R38-2-SCOPED-SIDECAR-LOADER.md).

## Narrow correction

R38 had required the reopened DocSettings object's `source_candidate` diagnostic field to equal exactly `/tmp/r25-ko-home/library/r33-original.sdr/metadata.epub.lua`. The original trace did not print that field or show post-reload values. It proved the migration function ran and a sidecar file was written to disposable /tmp, but not that a new DocSettings object recovered the saved data.

The new overlay **retains the genuine** `DocSettings:open`, `SettingsMigration:migrateSettings`, `DocSettings:flush` and original R25/R32/R33 synthetic startup/exit gates, **without modifying any staged KOReader source or native renderer**. It makes the proof stronger:

1. Seed a per-instance `r38_1_temp_roundtrip_token` in genuine DocSettings just before temporary sidecar flush.
2. Read **only the exactly expected temporary sidecar path**, parse it with genuine Lua `dofile` and verify that same token and the original document path were serialized.
3. Reopen the EPUB with genuine `DocSettings:open`, require a new independent object with matching token, unchanged book path and migrated margin/word-spacing values.
4. `source_candidate` if **present** must equal exactly the expected temp file; if **absent**, report `R38_1_RELOAD_SOURCE_CANDIDATE_FIELD_ABSENT` and rely on independent exact-file plus token/value checks. Any nonempty unexpected source or mismatched saved values fails closed. The original field's actual value remains unknown until the retry.
5. New strict reviewer requires exactly one of the two diagnostic markers, plus `R38_1_EXACT_TEMP_SIDECAR_DATA_PARSED`, `R38_1_GENUINE_RELOAD_TOKEN_AND_DATA_MATCH`, the original margin/word-spacing reloaded marker, normal R25/R32/R33 exit and all three fresh strict reviewer passes.

**Release:** conversation attachment `pw3-os-r38.1-temp-sidecar-reload-proof.zip`. SHA-256 **`1e8a86939074f93abbac87bce1dcea177b7adcabc6c2ac6fdce2d2645a6347ff`**. ZIP integrity and **10 internal payload SHA-256 hashes verified**; **45/45 host tests PASS**, including 12 new negative/provenance regression checks; Python and shell syntax PASS. The package does not contain the private R13 stage or genuine firmware blobs. No user-side ARM run yet.

## Mac retry — new output directory

```sh
cd ~/Downloads
unzip pw3-os-r38.1-temp-sidecar-reload-proof.zip
cd pw3-os-r38.1-temp-sidecar-reload-proof
python3 -m unittest discover -s tests -v

./run-r38-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r32-inkaway-persistence" \
  "$HOME/Downloads/pw3-os-r32-inkaway-first-run/R32-RESULT-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r33.1-pdf-render-arguments-fix" \
  "$HOME/Downloads/pw3-os-r33.1-offscreen-first-run/R33-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r34-readerui-import-first-run/R34-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/pw3-os-r38.1-temporary-docsettings-first-run"

tail -n 150 "$HOME/Downloads/pw3-os-r38.1-temporary-docsettings-first-run/R38-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r38.1-temporary-docsettings-first-run/R38-R25-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r38.1-temporary-docsettings-first-run/R38-R32-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r38.1-temporary-docsettings-first-run/R38-R33-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r38.1-temporary-docsettings-first-run/R38-REVIEW.json"
```

Target verdict (not yet observed) **`R38_1_TEMP_DOCSETTINGS_MIGRATION_ARM_PASS`**. Any failure, unexpected `source_candidate`, missing token, different source sidecar or unsuccessful document-value reload is still FAIL, not an excuse to relax the check. Preserve both the original R38 FAIL and new R38.1 output.

**Safety:** The runner retains the previous networkless read-only Docker application runtime, pinned source/review checks, disposable `/tmp`, no device mounts, no real Kindle hardware, no firmware writes, no boot or rootfs pruning. Even an R38.1 PASS would verify *only* the narrow per-book synthetic settings roundtrip; full ReaderUI initialization, global migration safety, page navigation and device boot remain untested. `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.

Upstream sources: [DocSettings](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/docsettings.lua), [SettingsMigration](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/ui/data/settings_migration.lua), [Lua serialization](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/util.lua).
