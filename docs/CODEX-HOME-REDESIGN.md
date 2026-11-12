# Codex Home — static editorial layout

## Design

Codex Home is an e-ink-first front page, rather than a live dashboard. Reuse the large Cormorant serif font from the former time display for a **static day number** and **weekday**, with the month/year in italic, arranged in a **centered vertical portrait composition**, not in a side-by-side date column. Do not render hours or minutes.

### 1072 × 1448 portrait layout

- Status strip (y≈34): small CODEX wordmark, Wi-Fi and battery indicators. Values are sampled on natural redraws, not polled for new screen output.
- Static date hero (y≈70–420): TODAY, weekday, oversized day number and month/year stacked vertically and centered, with deliberate spacing.
- Rule (y=440): original line-and-diamond ornament.
- Primary reading apps (y=490–656 and 670–836): Bible and KOReader as two **full-width stacked horizontal rows**. Each has a line-art icon on the left and a large serif label on the right. The vertical sequence is suited to a portrait e-reader.
- Secondary apps (y=850–1050): Games, Wi-Fi and Settings in three compact portrait-oriented icon cells.
- Frontlight slider (y≈1125–1235): unchanged touch interaction, moved to its own lower band.
- Rule (y=1255) and five locally compiled wisdom verses (y≈1320–1420), wrapped to fit without clipping.
- No browser icon until physical Kindle display/input work is completed.

The five-app vertical reading-first arrangement applies when exactly five apps are configured. For any other count, fall back to a bounded 3-/4-column grid rather than assuming exactly five slots. Existing drag-to-reorder semantics are kept: the first two *positions* are full-width reading rows; a user can customize their occupants by reordering apps.

### Refresh and standby

The original Home redraws its clock once per minute using a timed input_wait and WF_GL16 header refresh. The redesigned Home blocks in input_wait(-1) and skips EV_NONE events. It draws the date on Home entry, return from an app and wake from power-button sleep. At midnight the date/verse may remain from the previous day until a natural redraw. That is intentional: **no midnight refresh timer**.

This eliminates periodic screen refreshes. It does not prove deep sleep, suspend, energy use or Kindle kernel power-management behaviour; those require attended measurements. The existing input_wait(-1) helper may internally wake its poll every 60 seconds, but no screen update follows.

### Testing and rollout

The build/pw3os/test_codex_frontpage.py regression checks the date renderer, portrait full-width stacked rows, five-cell layout, fallback grid, slider positions, absence of timed refresh, and fail-closed upstream matching. The Home executable is compiled from pinned MIT-licensed upstream UI sources and included in the small Codex overlay. Back up the existing Alpine /usr/local/bin/home before replacement. Do not deploy to stock firmware.

No on-device visual or power validation has been performed. Check long weekday/month names, touch targets, drag-to-reorder, app return and next-day update on a physical PW3. Preserve the known-good Home for rollback.

### Future refinements

- Confirm typography and touch targets at 300 dpi.
- Test with five, six, nine and sixteen apps, especially when Browser is added.
- Confirm Alpine local timezone. Both the date and the wisdom-verse rotation now use localtime; the footer changes only on a natural redraw, never with a midnight timer.
- Avoid animations, recurring refresh timers, online quote fetches or permanently active widgets.

### Portrait correction

The first editorial proposal put the two primary applications side by side, giving the interface a landscape-dashboard appearance despite using a portrait framebuffer. This has been replaced with a centered vertical date hero and vertically stacked full-width reading rows. These positions remain reorderable. The touch press target for full-width rows now highlights the left icon and avoids assuming a square icon cell. The conceptual reference should be shown in a **1072:1448 portrait frame**, not a wide responsive card.
