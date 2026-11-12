# Codex Home — static editorial layout

## Design

Codex Home is an e-ink-first front page, rather than a live dashboard. Reuse the large Cormorant serif font from the former time display for a **static day number** and **weekday**, with the month/year in italic. Do not render hours or minutes.

### 1072 × 1448 portrait layout

- Status strip (y≈34): small CODEX wordmark, Wi-Fi and battery indicators. Values are sampled on natural redraws, not polled for new screen output.
- Static date hero (y≈70–420): a large non-zero-padded day number on the left, TODAY/weekday/month and year on the right.
- Rule (y=440): original line-and-diamond ornament.
- Hero apps (y=490–782): Bible and KOReader in two prominent, lightly framed cells.
- Secondary apps (y=804–1036): Games, Wi-Fi and Settings in three compact cells.
- Frontlight slider (y≈1125–1235): unchanged touch interaction, moved to its own lower band.
- Rule (y=1255) and five locally compiled wisdom verses (y≈1320–1420), wrapped to fit without clipping.
- No browser icon until physical Kindle display/input work is completed.

The five-app asymmetric arrangement applies when exactly five apps are configured. For any other count, fall back to a bounded 3-/4-column grid rather than assuming exactly five slots. Existing drag-to-reorder semantics are kept: the first two *positions* are larger reading slots; a user can customize their occupants by reordering apps.

### Refresh and standby

The original Home redraws its clock once per minute using a timed input_wait and WF_GL16 header refresh. The redesigned Home blocks in input_wait(-1) and skips EV_NONE events. It draws the date on Home entry, return from an app and wake from power-button sleep. At midnight the date/verse may remain from the previous day until a natural redraw. That is intentional: **no midnight refresh timer**.

This eliminates periodic screen refreshes. It does not prove deep sleep, suspend, energy use or Kindle kernel power-management behaviour; those require attended measurements. The existing input_wait(-1) helper may internally wake its poll every 60 seconds, but no screen update follows.

### Testing and rollout

The build/pw3os/test_codex_frontpage.py regression checks the date renderer, five-cell layout, fallback grid, slider positions, absence of timed refresh, and fail-closed upstream matching. The Home executable is compiled from pinned MIT-licensed upstream UI sources and included in the small Codex overlay. Back up the existing Alpine /usr/local/bin/home before replacement. Do not deploy to stock firmware.

No on-device visual or power validation has been performed. Check long weekday/month names, touch targets, drag-to-reorder, app return and next-day update on a physical PW3. Preserve the known-good Home for rollback.

### Future refinements

- Confirm typography and touch targets at 300 dpi.
- Test with five, six, nine and sixteen apps, especially when Browser is added.
- Confirm Alpine local timezone. Both the date and the wisdom-verse rotation now use localtime; the footer changes only on a natural redraw, never with a midnight timer.
- Avoid animations, recurring refresh timers, online quote fetches or permanently active widgets.
