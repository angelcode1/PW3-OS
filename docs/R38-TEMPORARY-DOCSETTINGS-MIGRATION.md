# R38 — genuine per-book migration with disposable DocSettings sidecar

**2026-11-02 update:** **Original R38 user-side ARM/QEMU FAIL** at the post-flush `DocSettings:open()` source-candidate assertion. The test did reach genuine legacy per-book migration in memory and an observed successful temporary sidecar flush, but **did not verify a fresh settings reload or the full R25/R32/R33 replay**. The original 33/33 host tests PASS remain synthetic only. [R38.1](R38-1-TEMP-SIDECAR-RELOAD-PROOF.md) is a separate stricter host-tested retry (45 tests PASS; user-side ARM still pending).

## Original R38 user-side ARM failure (2026-11-02)

User terminal output: original source checks and R37 preflight PASS, then genuine `reader.lua`, Ink Away save/reload, MuPDF PDF tile, CREngine EPUB memory view, `R38_GENUINE_DOCSETTINGS_OPENED_TEMP_ONLY`, genuine migration of CRe margins (10/12/14/16) and space condensing (65), `R38_GENUINE_DOCSETTINGS_MIGRATION_IN_MEMORY`, and `R38_GENUINE_DOCSETTINGS_SIDECAR_FLUSHED_TO_TEMP`. Then:

```text
/r38/migrate_sidecar.lua:71: DocSettings read unexpected source candidate
R38_TEMP_DOCSETTINGS_MIGRATION_ARM_GATE_FAIL (exit=1)
```

All fresh R25/R32/R33/R38 strict reviewers returned FAIL because the failure prevented the original event loop from resuming. Earlier *separate* R25/R32/R33/R34/R35 successes remain valid. The exact `source_candidate` string and the actual reloaded settings were not logged, so do not attribute this conclusively to a nil field, a bad serialization, or a filesystem error. An existing physical Kindle or persistent rootfs was never accessed or modified.

R38.1 introduces independent exact-file validation and a unique fresh DocSettings roundtrip marker instead of removing the provenance check. See the separate [R38.1 host-tested retry](R38-1-TEMP-SIDECAR-RELOAD-PROOF.md). The first R38 output directory must remain unchanged.

## Why this gate

The full `ReaderUI:init` code in KOReader v2026.07.2 opens a genuine `DocSettings` object and invokes `SettingsMigration:migrateSettings`. Since migration can update data and `DocSettings:flush` can write per-book sidecars, R38 isolates **that one feature** using the same original non-copyright EPUB fixture already proven renderable in R33.1. We do **not** force real ReaderUI into the R25 one-Close event-loop guard, change native code, run on physical hardware or skip migration while claiming it was run.

## User-side R37 evidence

The user reported `R37_READERUI_BOUNDARY_SOURCE_PREFLIGHT_PASS; NO_PRUNING; NOT_BOOTABLE` with six source files checked, pinned R25 guard and R13 sentinel verified, R36's 472 positive-open staged regular files and 976 still `UNKNOWN_HOLD`. R37 itself retained `per_document_migrations_executed=false`, `migration_disk_effects_proven_safe=false`, `readerui_page_navigation_verified=false`, `real_readerui_instances_executed_by_r37=false`, and all boot/device/firmware/file-removal permissions false.

## R38 approach

Source-only conversation archive **`pw3-os-r38-temporary-docsettings-migration.zip`**, SHA-256 **`80cdf1e4607af2bc3b95312207bc155fb759ec499f085cef006abe520d384574`**, ZIP integrity and 8 payload hashes verified. **33/33 Python synthetic regression tests PASS**; Python and POSIX shell syntax checked. Real ARM/QEMU not run in this environment.

The runner checks SHA-pinned R33.1 source, R25 guard and six original staged KOReader files against the user's R37 hashes, validates previous R33 and R34 ARM reviewers and original R37 preflight, reruns existing R23/R23.4/R24/R25 source checks into a **new** directory, then replays genuine R32 Ink Away persistence and R33 PDF/EPUB offscreen engines under the original R25 single synthetic Close lifecycle. Its R38 Lua overlay:

1. Confirms the genuine FileManager is the only visible UI widget and original R33.1 ephemeral EPUB exists under `/tmp/r25-ko-home/library`; no ReaderUI instance is created.
2. Imports genuine staged DocSettings, SettingsMigration and ReaderUI modules; verifies the former two method source locations. Requires the default `doc` metadata mode and checks every relevant candidate sidecar/history directory is below the temporary home.
3. Opens a new per-book settings object, seeds legacy margin and space-condensing values in memory, calls the **real** `SettingsMigration:migrateSettings`, and verifies the migrated settings.
4. Calls genuine `DocSettings:flush(nil,true)` to persist metadata *only* in `/tmp/r25-ko-home/library/r33-original.sdr/metadata.epub.lua`, then reopens genuine DocSettings and verifies migrated settings survived reload.
5. Requires normal R25 loop/exit and three fresh R25/R32/R33 strict reviewer PASS results **plus a new R38 reviewer**. A failed QEMU render, unexpected path or invalid sidecar produces FAIL; earlier successful checkpoints remain intact.

The earlier reviewers' `migrations_executed=false` refers to their original **global/onetime startup migration** path, still skipped. R38 reports per-book settings migration separately. Even an R38 PASS leaves `all_migration_disk_effects_proven_safe=false`, `guest_file_access_trace_reconciled=false`, `full_reader_ui_document_open_verified=false` and `readerui_instance_created=false`. It does **not** establish full production ReaderUI settings behavior.

Application Docker runtime: `--network none --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 96 --memory 768m --cpus 1` and only 160MiB disposable `/tmp`. R13 stage, source mounts read-only. New result directory is the only host write mount. The **Docker image build** can require package downloads when uncached; application runtime cannot use the network.

## Mac run

```sh
cd ~/Downloads
unzip pw3-os-r38-temporary-docsettings-migration.zip
cd pw3-os-r38-temporary-docsettings-migration
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
  "$HOME/Downloads/pw3-os-r38-temporary-docsettings-first-run"

tail -n 140 "$HOME/Downloads/pw3-os-r38-temporary-docsettings-first-run/R38-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r38-temporary-docsettings-first-run/R38-R25-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r38-temporary-docsettings-first-run/R38-R32-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r38-temporary-docsettings-first-run/R38-R33-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r38-temporary-docsettings-first-run/R38-REVIEW.json"
```

Expected only **after** user-side ARM/QEMU execution: `R38_TEMP_DOCSETTINGS_MIGRATION_ARM_PASS`. Keep any failure logs for a targeted fix; never relax safety or real-migration checks to force a PASS.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. Neither successful synthetic sidecar writes nor lexical trace coverage authorize stage pruning or a boot image.

Upstream references: [DocSettings](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/docsettings.lua), [SettingsMigration](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/ui/data/settings_migration.lua), [ReaderUI](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/reader/readerui.lua).
