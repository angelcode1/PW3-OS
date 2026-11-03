# R39.4.7 — two source-bound PDF metadata reads in one genuine reopen

**Status:** Host-tested only; **462/462 Python tests PASS**. ARM/QEMU **PENDING**. **NOT_BOOTABLE**.

## Why the original R39.4.6 ARM guest failed

User-side evidence `R39.4.6-ARM-EVIDENCE.zip` passed ZIP CRC. Independent R25 control and experimental source preflight PASS. The original R39.4 strict reviewer and separate R39.4.6 reviewer **FAIL**; the original log and failures must remain unchanged.

The first, source-bound `DocSettings:open` read during `FileManager:openFile` passed in cycle 2:

```
R39_4_5_SIDECAR_GATE exact=true c_pcall=true docsettings=true fresh_write=true regular_file=true cycle2=true
R39_4_5_GENUINE_DOCSETTINGS_SIDECAR_LOADED_FROM_FIRST_CYCLE
```

After the async original `ReaderUI:init`, a *second* `DocSettings:open(file)` at the upstream source-pinned `frontend/apps/reader/readerui.lua:131` attempted the **same** sidecar. Its `r3945_sidecar_loads==0` expectation made the second gate false, incrementing `stats.denied=1`, while the genuine second PDF still rendered and closed. The second Home's genuine, source-pinned metadata **write-open** also succeeded. The strict second returned FileManager assertion failed solely because a denial had been recorded, so final Close did not execute. This is a harness lifecycle/count mismatch, not a demonstrated production KOReader defect.

## R39.4.7 bounded correction

Only the isolated experimental `r394/loop_guard.lua`, its preflight source pin, **one inherited host assertion** updated to demand two audited reads rather than one, and a separate `review_r3947.py` / 20 new host tests change. Original production KOReader, R25, R39.4, R39.4.5 and R39.4.6 strict reviewers are **unchanged**.

The precise ordinary metadata file `.../r39-original-two-pages.sdr/metadata.pdf.lua` is allowed to execute through the *original* built-in `pcall` -> `DocSettings:open` line 276 path **at most twice**, with no additional `dofile` targets:

1. The first original `FileManager:openFile` call after the first Home: one first-cycle-generated `io.open('wb')` provenance; first document closed, raw PDF engine slot nil, inherited `false`, no `DocumentRegistry` ref, genuine returned FileManager previously active.
2. The second original `ReaderUI:init` at source-pinned line 131, verified by **function identity and exact line** in the Lua call chain, only after the genuine second `Input:inhibitInput(true)` lifecycle and while that Input cycle is active. The first reader/document remains released, the previous successful read count is one, the exact generated file is still regular, FileManager has been closed before ReaderUI initialization, the second PDF is not yet drawn, second Home has not been sent, and no denial was recorded. Here a new reader may already have a `DocumentRegistry` reference, so the first phase's global zero-refcount check is intentionally not reused; first archived document closure is still checked.

Both phases verify original `DocSettings:open` function identity and source call site, built-in C `pcall`, exact target path, regular non-symlink sidecar file/directory, fresh first metadata write, synthetic lifecycle counters and `stats.denied==0`. Both original metadata writes (one per Home close) remain confined to the exact file, original writer function, source line 1147 and `wb` mode. Final shutdown requires **exactly two reads, exactly two writes** and zero denied operations. There is no fallback authorization, arbitrary Lua execution, migration, hardware access or pruning.

New markers:

```
R39_4_7_READERUI_SIDECAR_GATE exact=true c_pcall=true docsettings=true readerui_init=true fresh_write=true regular_file=true phase2=true
R39_4_7_GENUINE_READERUI_DOCSETTINGS_SIDECAR_RELOADED
```

New independent strict reviewer `r394/review_r3947.py` can PASS only after original R39.4, R39.4.5 and R39.4.6 reviewers have **independently PASSed**. It requires two exact target observations, unique and correctly ordered old/new read gates/loaded markers, two genuine ReaderUI input lifecycles, original second PDF scroll draw, second Home metadata write, clean returned FileManager stack, genuine final Close, original R25 control, no denial/exception and all source pins. It never upgrades a FAIL.

## Run on Mac — isolated source and sibling output

**Use fresh paths; do not extract directly into `~/Downloads`**. Prerequisites are the same independent source stage, core, R37, R38 and prior actual R39.1/R39.2.4/R39.3.3 reviews as in R39.4.6.

```sh
cd "$HOME/Downloads"
SRC="$HOME/Downloads/pw3-os-r39.4.7-isolated"
mkdir -p "$SRC"
unzip -q pw3-os-r39.4.7-two-source-bound-sidecar-reads-arm-trial.zip -d "$SRC"
cd "$SRC"
shasum -a 256 -c SHA256SUMS-R3947
python3 -m unittest discover -s tests -q

./run-r394-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json" \
  "$PWD" \
  "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.2.4-scroll-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.3.3-home-first-run/R39.3.3-SENTINEL-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.4.7-two-reads-first-run"
```

### After guest execution (run even if original strict gate FAILs)

```sh
cd "$HOME/Downloads/pw3-os-r39.4.7-isolated"
python3 r394/review_r3947.py \
  --log "$HOME/Downloads/pw3-os-r39.4.7-two-reads-first-run/R394-EMULATION.log" \
  --baseline "$HOME/Downloads/pw3-os-r39.4.7-two-reads-first-run/R394-R25-BASELINE-CONTROL.json" \
  --preflight "$HOME/Downloads/pw3-os-r39.4.7-two-reads-first-run/R394-SOURCE-PREFLIGHT.json" \
  --previous-r39-3-3 "$HOME/Downloads/pw3-os-r39.3.3-home-first-run/R39.3.3-SENTINEL-REVIEW.json" \
  --strict-review "$HOME/Downloads/pw3-os-r39.4.7-two-reads-first-run/R394-REVIEW.json" \
  --out "$HOME/Downloads/R39.4.7-TWO-READS-REVIEW.json"

cd "$HOME/Downloads"
zip -j R39.4.7-ARM-EVIDENCE.zip \
  pw3-os-r39.4.7-two-reads-first-run/R394-EMULATION.log \
  pw3-os-r39.4.7-two-reads-first-run/R394-R25-BASELINE-CONTROL.json \
  pw3-os-r39.4.7-two-reads-first-run/R394-SOURCE-PREFLIGHT.json \
  pw3-os-r39.4.7-two-reads-first-run/R394-REVIEW.json \
  R39.4.7-TWO-READS-REVIEW.json
```

If files are missing after a failure, package just the created log/review files and the terminal error. **Do not overwrite or alter any R39.4.6 evidence**.

Target only if genuinely earned: `R25_REAL_EVENT_LOOP_ARM_PASS`, `R39_4_REOPEN_ARM_GATE_PASS`, `R39_4_SAME_SESSION_REOPEN_ARM_PASS`, `R39_4_7_TWO_SOURCE_BOUND_READS_ARM_PASS`.

**NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE.** All 976 `UNKNOWN_HOLD` staged entries remain retained. No physical PW3 operation, independent boot, global migrations or full dependency closure is verified. Research and educational purposes only.
