# R37 — ReaderUI source and settings/event boundary preflight

**2026-11-02:** User reported **R36_EXPANDED_WORKLOAD_CATALOG_CORRELATED PASS**: 472 distinct staged regular files with positive guest-open evidence in the expanded R35 workload vs 341 from startup-only R27, **131 newly observed**, zero R27-only and **976 still UNKNOWN_HOLD**. The user's R36 summary verified the original R26 stage hashes and both private raw traces/observations, reported no rootfs mutation, and retained `NOT_BOOTABLE`. **R37 source-only candidate has 24/24 synthetic host tests PASS; user-side R37 source preflight NOT YET RUN.**

## Why R37 is scoped narrowly

A genuine ReaderUI document-opening test is materially different from R34 ReaderUI *module import*. Upstream KOReader v2026.07.2 uses `FileManager:openFile()` → `ReaderUI:showReader()` → `UIManager:nextTick()` → `ReaderUI:doShowReader()`. ReaderUI initialization calls `DocSettings:open(file)` and `SettingsMigration:migrateSettings(self.doc_settings)`. The migration can call `config:saveSetting` and `config:delSetting`, so temporarily-sandboxed document sidecar and migration effects must be audited rather than claiming migration skipped or safe based on import alone.

The original pinned R25 guard allows a **single** synthetic `Close` event while FileManager is active. That cannot honestly be reused to claim page navigation or ReaderUI close/return. The next true runtime test therefore needs a separate event choreography, safety review and strict reviewer; R37 does not pretend to execute it.

## Deliverable and checks

Source-only ZIP `pw3-os-r37-readerui-boundary-preflight.zip` SHA-256 **`c9fc996955f0bf5727f44fbdabbe7e0053fd143f22acfbf75e66a161b592c4b0`**, ZIP integrity plus all three internal file hashes verified, 24/24 synthetic Python host tests PASS. It includes only `README-R37.md`, `r37/audit.py`, `tests/test_audit.py`, and `SHA256SUMS`; no proprietary R13 stage, private user paths or firmware files.

The Python tool: validates user-reported R34 and R36 reviewer invariants; confirms the original R13 manifest sentinel; verifies original R25 synthetic event-loop guard SHA-256 and its one-Close contracts; reads and hashes **six staged KOReader source files** (ReaderUI, FileManager, DocSettings, settings migration, ReaderPaging, UIManager), checking their expected entrypoints and migration mutators. It creates one shareable JSON report with SHA hashes and explicit non-execution holds. It does **not** execute Lua, call QEMU/Docker, import ReaderUI, run migrations, open documents, modify stage/rootfs or authorize file removal. Static string anchors do not prove behavior or path safety, and the R36 summary does not prove a dependency closure.

## Mac reproduction (no Docker, QEMU, device or network)

```sh
cd ~/Downloads
unzip pw3-os-r37-readerui-boundary-preflight.zip
cd pw3-os-r37-readerui-boundary-preflight
python3 -m unittest discover -s tests -v

python3 r37/audit.py \
  --stage "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  --core "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  --r34-review "$HOME/Downloads/pw3-os-r34-readerui-import-first-run/R34-REVIEW.json" \
  --r36-summary "$HOME/Downloads/pw3-os-r36-catalog-first-run/R36-SUMMARY.json" \
  --out "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json"

cat "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json"
```

**Expected only after user-side success:** `R37_READERUI_BOUNDARY_SOURCE_PREFLIGHT_PASS`. The tool refuses existing result files and output within the stage/core tree. If an expected source anchor is absent, preserve it and review the difference; never force the source contract to PASS.

**Next:** a separate R38+ full ReaderUI application harness with deliberately synthesized input event sequence, ephemeral per-book settings migration and sidecar path containment, real `nextTick` coroutine, genuine page turn and close/return; all must have fresh fail-closed reviewers and guest-path trace. Current user-success milestones R25/R32/R33/R34/R35 and R36 correlation are preserved independently.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.
