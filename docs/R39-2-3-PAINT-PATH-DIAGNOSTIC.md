# R39.2.3 — diagnostic trace of genuine UIManager → ReaderUI → ReaderView PDF paint

**2026-11-02 status:** Previous R39.2.2 user-side ARM/QEMU **FAIL**, with independently rerun unchanged original R25 PASS. R39.2.2's bounded `UIManager:setDirty(reader,'full')` was requested, but its **next synthetic input poll still observed no successful original PDF page-1 draw**. No page-turn event was sent. R39.2.3 is **source-only/host-tested: 131/131 regression tests PASS, ARM/QEMU pending.** The successful R39.1 genuine ReaderUI activation evidence remains valid.

## Precise outstanding question

KOReader's actual `UIManager:_repaint` iterates the window stack and invokes `widget:paintTo` **only when that widget is dirty or one underneath it has been repainted**. The actual `InputContainer:paintTo` normally forwards to the first child unless the widget is missing, `skip_paint` is set, or another condition prevents the container painting. The real `ReaderView:paintTo` invokes PDF `drawSinglePage`; the latter's *successful return* is the established R39.2.1 completion requirement. The last R39.2.2 user log contains the `setDirty` request but does **not** show where this chain stopped. Do not assume a MuPDF failure, a bad original PDF, or a renderer success from a missing completion marker alone.

## New diagnostic overlay and unchanged strict release gate

This package forks only the separate R39.2.2 synthetic test, **not the original SHA-pinned R25 baseline or staged KOReader source**. It wraps, logs bounded aggregate state, and invokes the **original unchanged**:

- `UIManager:_repaint`: reader dirty flag, actual top widget, ReaderUI's real first-child view, skip-paint bit; log before and after original call (up to five observed entry/returns)
- `InputContainer:paintTo`: log **only for the genuine ReaderUI instance**, then call the original (up to six observations)
- `ReaderView:paintTo`: log **only for that actual reader's view**, then call the original (up to six observations)
- Existing genuine `ReaderView:drawSinglePage` original completion counter: unchanged from R39.2.2
- Synthetic input polling: log bounded observer counts and aggregate page phase

**No fake draw, no direct paint, no alternate PDF engine, no page-state assignment, no extra repaint request and no change to the four-input-poll/two-event upper bounds.** The original two-page PDF, source hashes, real ReaderUI coroutine and independent R25 control are preserved. The original R39.2.2 strict `R39-REVIEW.json` still controls whether page navigation passes; the diagnostic script does not certify navigation.

A new offline `r39/analyze_paint_trace.py` reads only a fresh R39.2.3 guest log and writes a separate aggregate-only JSON file. When the expected failed trial has diagnostic evidence, it emits `R39_2_3_PAINT_PATH_FAILURE_DIAGNOSTIC_CAPTURED`, **explicitly with `page_navigation_verified=false`**. This is a *diagnostic-only* verdict, not an ARM page-navigation PASS or a resolution of the root cause. If the trace is missing or malformed, it fails closed.

## Release validation

Conversation archive: `pw3-os-r39.2.3-paint-path-diagnostic.zip`.

- SHA-256: `b0b56bcdbf8b37b3d5ef8191c6f6f712bc761258d7b83f4db532b0127bedfd09`
- **131/131 Python host tests PASS**: 116 inherited plus 15 new diagnostic/source/reviewer checks
- Python compile PASS, POSIX shell syntax PASS, all three Lua files syntax-parsed against system Lua 5.4 library PASS
- ZIP integrity PASS; **21 internal payload SHA-256 entries verified**
- New separate R39 guard SHA-256: `89d02ed050d87ab182b5dac7f69ae63e2eef77e76466753c95edda971ee31bad`
- **User-side ARM/QEMU result pending**. A successful host test does not prove a complete PDF paint.

## Mac run — new output directory

```sh
cd ~/Downloads
unzip pw3-os-r39.2.3-paint-path-diagnostic.zip
cd pw3-os-r39.2.3-paint-path-diagnostic
python3 -m unittest discover -s tests -v

./run-r39-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json" \
  "$PWD" \
  "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.2.3-paint-diagnostic-first-run"

tail -n 180 "$HOME/Downloads/pw3-os-r39.2.3-paint-diagnostic-first-run/R39-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r39.2.3-paint-diagnostic-first-run/R39-R25-BASELINE-CONTROL.json"
cat "$HOME/Downloads/pw3-os-r39.2.3-paint-diagnostic-first-run/R39-REVIEW.json"

python3 r39/analyze_paint_trace.py \
  --log "$HOME/Downloads/pw3-os-r39.2.3-paint-diagnostic-first-run/R39-EMULATION.log" \
  --out "$HOME/Downloads/R39.2.3-PAINT-DIAGNOSTIC.json"
cat "$HOME/Downloads/R39.2.3-PAINT-DIAGNOSTIC.json"
```

A nonzero guest exit is expected if page painting remains blocked; do not ignore it or relabel the historical failure. The next correction should follow **the first unobserved genuine paint boundary**, not add repeated empty polls without evidence. If a source/interface mismatch appears, inspect before changing allowlists.

**Immutable holds:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. No rootfs pruning; R36's 976 unobserved regular files remain `UNKNOWN_HOLD`. Docker application runtime is networkless with source/stage mounted read-only and disposable `/tmp`.

References: [R39.2.2 actual ARM failure](R39-2-2-BOUNDED-REPAINT-PROOF.md), [R39.1 real ReaderUI activation PASS](R39-1-READERUI-INPUT-LIFECYCLE-FIX.md), and upstream [UIManager repaint](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/ui/uimanager.lua#L1220-L1275), [InputContainer paint](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/ui/widget/container/inputcontainer.lua#L66-L91), and [ReaderView paint](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/reader/modules/readerview.lua#L185-L204).
