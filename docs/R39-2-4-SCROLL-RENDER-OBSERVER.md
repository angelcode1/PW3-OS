# R39.2.4 — genuine PDF scroll-layout paint and two-page input event

**Status 2026-11-02: HOST-TESTED ONLY (156/156 Python tests PASS); ARM/QEMU PENDING.** The user-side R39.2.3 diagnostic succeeded in identifying the missing observation branch; **its original strict page-navigation reviewer still FAILed** and the unchanged original R25 control PASS remains valid. No R39.2.4 guest run has been reported.

## What the genuine R39.2.3 diagnostic proved

The user ran the independent R25 baseline and the R39.2.3 guest trial, then executed the diagnostic analyzer. Result: `R39_2_3_PAINT_PATH_FAILURE_DIAGNOSTIC_CAPTURED`, with `page_navigation_verified=false` and unchanged strict `R39-REVIEW.json` FAIL. The actual guest log had four real UIManager repaint entries/returns and two real ReaderUI container/ReaderView paints. Both ReaderView paints logged `paging=true scroll=true page=1 bb=true`. Therefore the previous `drawSinglePage`-only callback was inapplicable to the active PDF **scroll layout**, though the diagnostic did not certify that actual MuPDF page drawing had finished.

Pinned KOReader v2026.07.2 `ReaderView:paintTo` selects `drawScrollPages` at source line 196 when `page_scroll=true`, instead of `drawSinglePage` at line 198. Genuine `drawScrollPages` loops over `self.page_states` and calls real `self.document:drawPage` once per entry using `state.page`. This is the correct completion boundary.

## Narrow release changes

The new fork modifies **only** the separate R39 synthetic `r39/loop_guard.lua`, its source-pin preflight, its strict R39 reviewer and host tests. It does not alter real KOReader source, the two-page original PDF, R25.3 or any earlier evidence. The wrapper:

1. Requires a genuine upstream `ReaderView:drawScrollPages` called by real `ReaderView:paintTo` **at pinned line 196**, with an actual ReaderUI instance, genuine ReaderPaging and open two-page temporary PDF. Requires memory blitbuffer and `page_scroll=true`.
2. Requires ReaderPaging and ReaderView to agree on selected page **1 before** the real UIManager `GotoPage(2)` event or page **2 after**. Requires selected page in the genuine bounded `page_states` and snapshots them, rejecting unexpected entries/replacement.
3. Invokes **the original unchanged `drawScrollPages` method**. Only after it returns normally, and after the page-state snapshot is reconfirmed, records a bounded completion for **the currently selected page only**. It never calls PDF `drawPage` itself, directly paints UI or assigns a page number. The earlier `drawSinglePage` observer stays installed but does not qualify this scroll-specific strict reviewer.
4. Requires source-pinned `R39_2_4_GENUINE_SCROLL_PAGE1_DRAW_RETURNED`, then the unchanged `R39_2_GOTOPAGE2_SENT_THROUGH_REAL_UIMANAGER_INPUT`, then `R39_2_4_GENUINE_SCROLL_PAGE2_DRAW_RETURNED`, with the original per-page MuPDF completion, ReaderPaging and ReaderView state gates, normal Close and genuine UIManager/Generic exit.
5. Requires a fresh independent unchanged R25 control strict PASS, previous user-confirmed R39.1 real ReaderUI activation PASS and R38.2.1 temporary settings reconciliation evidence. The previous bounded single repaint request per page is retained only as a fallback; no new poll budget or paint bypass.

A **future** strict `R39_2_READERUI_PAGE_TURN_ARM_PASS` would show real KOReader's synthetic input page 1→2 selection plus successful **in-memory original PDF scroll-layout drawing** after each selection. It does not prove physical e-ink pixels, hardware input, Home→FileManager, global migrations, full dependency closure or a bootable system.

## Source release and verification

Conversation archive: `pw3-os-r39.2.4-scroll-render-observer.zip`. SHA-256 **`d17d08026e93ca95ad068a566ac91b10749a101ce7a431388c0f4bf0351de1ff`**, ZIP integrity and **23 internal payload SHA-256 checks PASS**. **156/156 host tests PASS**, including new fail-closed rejection of missing/duplicated/out-of-order scroll-specific page completions, original R25 baseline mismatch, aborted coroutine and missing page-2. All Python files compile; POSIX shell syntax PASS; three Lua source files pass syntax-only Lua 5.4 `luaL_loadbufferx` parsing. User-side ARM/QEMU **not run**.

- New R39 forked synthetic guard SHA-256: `5830656126004b80bdf9004f0dd59216a083d813c8021ddd6c7bf57ce757c41c`
- New strict reviewer SHA-256: `2b514a92d02e48610d931a85496237744647ebdfe42586909bf1629ddd08dae9`
- Original R25.3 guard SHA-256: `7f5881a9c79da22c626bd0451a580fd13eae8af96330de811a13042cd98ed2b8`
- Original two-page fixture SHA-256: `17f2bf493433c9664457dd51f0e3e31e2f67b88b0480f97a3ed9dc2ade7170db`
- Pinned genuine upstream ReaderView Git blob: `3217d9d20ca3e593f44b465ef6322fb5e6058db5`

## Mac reproduction — fresh results directory

```sh
cd ~/Downloads
unzip pw3-os-r39.2.4-scroll-render-observer.zip
cd pw3-os-r39.2.4-scroll-render-observer
python3 -m unittest discover -s tests -v

./run-r39-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json" \
  "$PWD" \
  "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.2.4-scroll-first-run"

cat "$HOME/Downloads/pw3-os-r39.2.4-scroll-first-run/R39-R25-BASELINE-CONTROL.json"
tail -n 180 "$HOME/Downloads/pw3-os-r39.2.4-scroll-first-run/R39-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r39.2.4-scroll-first-run/R39-REVIEW.json"
```

If the ARM trial fails, preserve the exact failure and the separate R39.2.3 diagnostic; do not relax source pins or render/page-state requirements. R39.2.4 is a **new** trial, not a reinterpretation of the historical failed R39.2–2.3 strict reviewers.

**Immutable hold:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. Original R25 baseline remains unchanged; no rootfs prune, no Kindle hardware access. The 976 unobserved staged regular files remain `UNKNOWN_HOLD`.

References: [R39.2.3 user-confirmed paint-path diagnostic](R39-2-3-PAINT-PATH-DIAGNOSTIC.md), [R39.1 first ReaderUI activation ARM PASS](R39-1-READERUI-INPUT-LIFECYCLE-FIX.md), and upstream [ReaderView PDF scroll painting](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/reader/modules/readerview.lua#L185-L200) / [drawScrollPages](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/apps/reader/modules/readerview.lua#L372-L393).
