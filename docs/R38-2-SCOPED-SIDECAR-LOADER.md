# R38.2 — temporary single-path metadata loader under the pinned R25 deny gate

**2026-11-02 update:** Original R38.2 user-side ARM/QEMU **application workload completed** genuine per-book migration, temporary sidecar exact-file reload/token verification and loader restoration, with fresh R25/R32/R33 PASS. However the **original R38.2 strict reviewer returned FAIL**, because the container probe printed the stale `R38_1_TEMP_DOCSETTINGS_MIGRATION_ARM_GATE_PASS` marker instead of the required `R38_2_...` label. This failure must remain recorded. [R38.2.1](R38-2-1-GATE-MARKER-REPAIR.md) corrects only the release marker and supplies an optional pinned, read-only retrospective reviewer; user-side R38.2.1 validation is pending.

## User-supplied R38.2 evidence and release-gate issue

The user log showed, in sequence, `R38_GENUINE_DOCSETTINGS_MIGRATION_IN_MEMORY`, `R38_GENUINE_DOCSETTINGS_SIDECAR_FLUSHED_TO_TEMP`, `R38_2_SCOPED_TEMP_METADATA_LOADER_INSTALLED`, `R38_1_EXACT_TEMP_SIDECAR_DATA_PARSED`, `R38_1_RELOAD_SOURCE_CANDIDATE_MATCHED`, `R38_1_GENUINE_RELOAD_TOKEN_AND_DATA_MATCH`, `R38_2_SCOPED_TEMP_METADATA_LOADER_RESTORED`, `R38_GENUINE_DOCSETTINGS_SIDECAR_RELOADED_FROM_TEMP`, and normal synthetic UIManager shutdown. Three earlier strict reviewers PASS. The strict R38.2 reviewer *alone* returned `FAIL` with error `missing or duplicated marker: R38_2_TEMP_DOCSETTINGS_MIGRATION_ARM_GATE_PASS` because the emitted gate was labelled `R38_1_TEMP_DOCSETTINGS_MIGRATION_ARM_GATE_PASS` in the source script. No new guest execution or retrospective reconciliation has yet been reported for R38.2.1. Do not mislabel the original reviewer result PASS.

See [R38.2.1 marker repair](R38-2-1-GATE-MARKER-REPAIR.md).

## Root cause verified by the original pinned source

The original SHA-pinned `r25_3/loop_guard.lua` intentionally redefines `dofile` to allow only a small set of exact source and temporary global-settings paths. All other paths are rejected with `R23_DENIED_DOFILE`. The original R38/R38.1 probes created a new per-book temp sidecar at `/tmp/r25-ko-home/library/r33-original.sdr/metadata.epub.lua`, which is **not** in R25's source-only allowlist. R38.1 called `pcall(dofile,filename)`, caught the denial and failed with `R38.1 exact saved metadata could not be loaded from temp file`. Thus the prior log does **not** prove whether the generated metadata was valid, and the original failed results must not be relabeled PASS. The same gate affects genuine `DocSettings:open` when it tries to load that saved file.

## Correction and explicit security tradeoff

R38.2 changes **only the host-owned synthetic Lua overlay and its strict reviewer/tests**; the staged KOReader code, R25/R32/R33 guarded sources, original migration implementation and original EPUB/PDF fixtures remain unchanged. **Only after** genuine DocSettings migration and a successfully checked flush, it temporarily inserts an exact-file-only `dofile(path)` helper. For any path other than the literal expected temp sidecar, it calls the original R25 `dofile` guard, preserving its deny policy.

Before the helper runs, R38.2 requires `/tmp`, home, library and sidecar parents to be actual directories, not symlinks; the sidecar itself must be a non-symlink file; its contents must match the `-- <exact-filename>` / `return ` header produced by genuine KOReader `util.writeToFile`. Every checked load reopens the exact file and requires byte identity with the just-read serialized data; it uses Lua `loadfile` only for that one file. The protected verification runs (1) independent exact-file parse, (2) genuine fresh `DocSettings:open` with matching run-specific token and all migrated settings, and (3) exact `source_candidate` match. Exactly two literal-path loads are required. **The prior R25 `dofile` guard is unconditionally restored on success or failure** before completion or error.

This is a narrowly scoped, explicit exception for a known disposable per-book metadata Lua table. It is **not** an authorization to execute arbitrary user-side Lua files, relax the global security guard, or claim full metadata-path safety. All other `dofile` attempts still use the pinned R25 deny policy; an unexpected content change, symlink, non-matching path or value causes FAIL.

## Host validation and archive

Conversation artifact: `pw3-os-r38.2-scoped-sidecar-loader-fix.zip`. SHA-256 **`da9b7906070a3cf4fc6709495d5d4142abd0f635da4b6e042e529f305f41963f`**. ZIP test PASS, **12 internal SHA-256 payload hashes verified**. **60/60 synthetic host tests PASS** (original 45 + 15 new), Python syntax, POSIX shell syntax and both Lua files syntax checked. ARM/QEMU **not run**. No private staged rootfs, proprietary firmware, user books, or raw guest trace is included.

## Mac reproduction (new output directory, no overwrites)

```sh
cd ~/Downloads
unzip pw3-os-r38.2-scoped-sidecar-loader-fix.zip
cd pw3-os-r38.2-scoped-sidecar-loader-fix
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
  "$HOME/Downloads/pw3-os-r38.2-temporary-docsettings-first-run"

tail -n 150 "$HOME/Downloads/pw3-os-r38.2-temporary-docsettings-first-run/R38-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r38.2-temporary-docsettings-first-run/R38-R25-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r38.2-temporary-docsettings-first-run/R38-R32-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r38.2-temporary-docsettings-first-run/R38-R33-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r38.2-temporary-docsettings-first-run/R38-REVIEW.json"
```

Target **only after successful user-side ARM/QEMU replay:** `R38_2_TEMP_DOCSETTINGS_MIGRATION_ARM_PASS`, plus fresh R25/R32/R33 PASS. The R38.2 reviewer requires ordered proof of temporary helper install, exact sidecar parse, exact source-candidate selection, marker and migrated value reload, helper removal, genuine UIManager Close/exit, and unchanged no-device/no-boot holds. Any FAIL is retained with original error; old R38 and R38.1 directories are not touched.

**Immutable holds:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. The Docker application is networkless and read-only except disposable `/tmp` plus a new results mount. It does not create a rootfs, use physical Kindle interfaces, perform full ReaderUI initialization/navigation, run global startup migrations, establish complete dependency closure or authorize file removal.

See [R38 original](R38-TEMPORARY-DOCSETTINGS-MIGRATION.md), [R38.1 failure](R38-1-TEMP-SIDECAR-RELOAD-PROOF.md), and [R37 source boundary](R37-READERUI-BOUNDARY-PREFLIGHT.md).