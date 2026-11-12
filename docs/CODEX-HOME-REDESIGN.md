# Codex Home — original layout, static weekday and date

## Intent

Keep the current Home interface precisely as it exists: the original
three-column app grid, circular line-art icons, app order and drag/drop
behaviour, status bar, ornament, and frontlight slider. **Do not redesign
the application layout.**

Only replace the live HH:MM clock with a larger **weekday** and
calendar date, inside the exact same header rectangle (y=70..420).

## Typography

- The weekday (`%A`, e.g. Thursday) uses the **original time's
  Cormorant Bold font** (`f_serif_bold`). Start at 178 px and shrink only
  when necessary to fit the 1072-pixel screen width.
- Below it, use the existing Cormorant Italic font (`f_serif_italic`)
  for the day number and month, initially 118 px and fitted to the width.
- Underneath, retain a static 48 px italic year.
- Left-align the text to the same original clock margin. Keep the
  original app grid and all other Home coordinates unchanged.
- No hour or minute appears on the Home screen.

## Retained source geometry and actions

Original constants remain unchanged:

- `CLOCK_Y=70`, `RULE_Y=440`, `GRID_Y=490`,
  `GRID_BOTTOM=1262`, `CELL_H=250`, `SLIDER_Y=1290`.
- Original dynamic 3-/4-column app grid, `draw_app` and hit targets.
- Original frontlight slider and its existing tap/drag control.
- Existing Codex wordmark, battery/wireless status and five locally
  compiled wisdom quotations.

## Redraw and power

Remove the original timer-driven Home refresh every 60 seconds and use
`input_wait(-1)`. The weekday/date and rotating verse only change
when Home is redrawn naturally (for example on return from an app or
a power-button wake).

This avoids waking the display every minute. It does **not** prove
that the Kindle enters suspend or quantify battery life; independent
hardware power tests are required. A midnight date transition may
wait for the next natural redraw.

## Source and tests

The minimal patch lives in `build/pw3os/codex_frontpage.py`.
`test_codex_frontpage.py` asserts that the original grid, app renderer,
tap/drag behavior, slider position and ornament remain source-identical,
while the time display and timer are removed. The full build creates the
updated `home` executable inside both the image and the small overlay.

No physical screen verification has occurred; the PR remains a draft.
