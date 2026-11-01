# R34.0 — genuine ReaderUI module import under the verified synthetic lifecycle

**2026-11-02:** **R34.0 genuine ReaderUI module import ARM/QEMU PASS (user-provided runtime log and four strict reviewers).** It reconfirmed R25, R32, R33 PASS in the same offline synthetic run. ReaderUI was not instantiated; document-settings migration and navigation were not executed; all boot/device/firmware protections remain false and `NOT_BOOTABLE`.

## User-side verified ARM/QEMU result

The user reported `R34_READERUI_IMPORT_ARM_GATE_PASS` and supplied the complete trace plus fresh independent R25, R32, R33, R34 reviewer JSON. The authentic `reader.lua` ran FileManager, real Ink Away menu/stroke/project reload, MuPDF PDF memory tile, CREEngine EPUB memory view, and then:

```text
R34_GENUINE_READERUI_MODULE_IMPORTED
R34_GENUINE_READERUI_ENTRYPOINTS_VERIFIED
R34_GENUINE_DOC_SETTINGS_MIGRATION_ENTRYPOINT_VERIFIED
R34_READERUI_INITIALIZATION_AND_MIGRATION_NOT_EXECUTED
R25_REAL_UIMANAGER_EVENT_LOOP_REACHED
R25_REAL_READER_SHUTDOWN_COMPLETED
R34_READERUI_IMPORT_R33_R32_R25_LIFECYCLE_PASS
R25_REAL_EVENT_LOOP_ARM_PASS
R32_INKAWAY_PERSISTENCE_ARM_PASS
R33_PDF_EPUB_OFFSCREEN_ARM_PASS
R34_READERUI_IMPORT_ARM_PASS
```

R34 reviewer `readerui_module_import_verified=true`, `readerui_method_source_anchors_verified=true`, `genuine_docsettings_migration_module_import_verified=true`, `r25_r32_r33_lifecycle_replayed=true`. Explicit false: `readerui_instance_created`, `full_reader_ui_document_open_verified`, `document_settings_migration_executed`, `page_navigation_verified`, `dependency_closure_proven`, `real_pw3_init`, all hardware/device/firmware/boot/removal permissions. As elsewhere, Docker image digest `sha256:e2459...` is not a release ZIP checksum.

This **does not** prove full ReaderUI startup. The source path through `FileManager:openFile` → `ReaderUI:showReader` → `UIManager:nextTick` is a separate scenario requiring controlled synthetic events and audited temporary-only document settings.

## Boundaries and motivation

Genuine KOReader v2026.07.2 `frontend/apps/filemanager/filemanager.lua` calls `ReaderUI:showReader` in `FileManager:openFile`; `ReaderUI:showReader` schedules `doShowReader` via `UIManager:nextTick`. `ReaderUI:init` invokes per-book `SettingsMigration:migrateSettings(self.doc_settings)` and uses further device/screen/input interfaces. The previously verified R25.3 synthetic input delivers only one `Close` event with FileManager active. Forcing ReaderUI transitions into that baseline would invalidate its explicit lifecycle assumptions without a new synthetic event contract. R34.0 therefore tests the necessary module import **without claiming the final workflow**.

The exact R34.0 overlay imports the unchanged pinned R33.1 document-workload source, R32 persistence source and R25.3 lifecycle source. After real Ink Away stroke/save/project reload and real MuPDF/CRE offscreen render methods, it imports genuine `apps/reader/readerui` and asserts that `showReader`, `showReaderCoroutine`, `doShowReader`, `init`, and `onClose` derive from `frontend/apps/reader/readerui.lua`. It imports genuine `ui/data/settings_migration` and confirms the migration entrypoint's source while deliberately **not invoking it**. No instance is created; FileManager remains the active UIManager widget. Then genuine UIManager run + synthetic Close + Generic:exit are verified again with fresh R25, R32, R33 and R34 strict reviewers.

## Safety and verification

The bundle pins SHA-256 hashes for six critical files in the earlier R33.1 source package and requires its user-supplied strict reviewer `R33_PDF_EPUB_OFFSCREEN_ARM_PASS` with all migration, device, boot and cleanup holds. It validates the same previously checked R13 stage sentinel `7eb0d027b2b407fe6963ea9b9a1fe7fee1db96ae66f9399ece179238939176ed`, plus source contract anchors and hashes for actual staged `readerui.lua`, `settings_migration.lua`, `filemanager.lua` and `docsettings.lua`. It also re-runs all five older source audits into non-overlapping output filenames.

The runtime container has `--network none`, `--read-only`, `--cap-drop ALL`, `--security-opt no-new-privileges`, a 96-process cap, 768 MiB RAM cap, one CPU, disposable 160 MiB `/tmp`, stage and source mounted read-only, and no physical Kindle device mounts. Docker **image build** may still need dependency downloads when uncached; the application execution has no network. All results are written only to a new host output folder. No firmware, real battery, hardware, EPDC, device access, boot, file removal or migration execution is permitted.

**Local authoring evidence:** 32/32 synthetic host regression tests PASS (including source pin tampering, stage sentinel mismatch, missing source anchors, symlink inputs, reviewer false claims, marker order/duplication, CLI overwrite rejection, and Docker safety assertions). Python and shell syntax PASS; both Lua files parse with texlua; ZIP integrity and 8 internal payload SHA-256 digests verified. **No Docker or ARM/QEMU run was available in the authoring environment**, so this is not evidence of ARM import success.

**Conversation ZIP:** `pw3-os-r34-readerui-import-preflight.zip` SHA-256 `24cc8f84510ce6a9c85680df546cdb250f8044a84dbc2cff2edd321eddff2160`.

## Mac reproduction

```sh
cd ~/Downloads
unzip pw3-os-r34-readerui-import-preflight.zip
cd pw3-os-r34-readerui-import-preflight
python3 -m unittest discover -s tests -v

./run-r34-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r32-inkaway-persistence" \
  "$HOME/Downloads/pw3-os-r32-inkaway-first-run/R32-RESULT-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r33.1-pdf-render-arguments-fix" \
  "$HOME/Downloads/pw3-os-r33.1-offscreen-first-run/R33-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r34-readerui-import-first-run"

tail -n 160 "$HOME/Downloads/pw3-os-r34-readerui-import-first-run/R34-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r34-readerui-import-first-run/R34-R25-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r34-readerui-import-first-run/R34-R32-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r34-readerui-import-first-run/R34-R33-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r34-readerui-import-first-run/R34-REVIEW.json"
```

**Only after a successful user ARM/QEMU run** is the target `R34_READERUI_IMPORT_ARM_PASS`. If an import-time dependency fails, preserve logs and fix exact source-grounded cause; do not lower the existing R25/R32/R33 reviewers. R34.0 cannot establish `full_reader_ui_document_open_verified`, `page_navigation_verified`, `document_settings_migration_executed`, dependency closure, real e-ink or independent boot.

The more ambitious future FileManager → ReaderUI → page turn → close workflow is separately described in [R34 design plan](R34-READERUI-WORKFLOW-PLAN.md), and needs a separately verified multi-event synthetic input/temporary DocSettings allowance.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.
