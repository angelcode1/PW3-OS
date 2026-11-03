# R40.4.3.5 — source-bound original UI event dispatch and canvas input contract

**Status: STAGED-SOURCE INPUT REQUIRED, RUNTIME NOT TESTED. Research-only. NOT_BOOTABLE.**

R40.4.3.4 public review/summary were byte-identical and confirm the source-bound original view show/close trial PASS. Its reviewer-reported 9,907 QEMU syscall lines and 4,793 decoded path operations are **not** a new staged-file union. It did **not** dispatch an InkAwayView input event or save a stroke.

A genuine R40.4.3.5 event workload must first inspect the *actual staged* Ink Away view methods and KOReader event-dispatch definitions, not use current upstream assumptions or direct Canvas calls. Obtain a **local private read-only archive** of the six to nine relevant original staged Lua files with sha hashes from the preflight-verified rootfs. Suggested source set, all relative to `rootfs/opt/koreader-compat/app`:

- `plugins/ink-away.koplugin/main.lua`
- `plugins/ink-away.koplugin/ink/view.lua`
- `plugins/ink-away.koplugin/ink/view/input.lua`
- `plugins/ink-away.koplugin/ink/view/gestures.lua`
- `plugins/ink-away.koplugin/ink/view/stroke.lua`
- `frontend/ui/uimanager.lua`
- `frontend/ui/event.lua`
- `frontend/ui/widget/container/inputcontainer.lua`
- `frontend/ui/widget/container/widgetcontainer.lua`

**Runbook:** cross-check those files against the original R26 inventory and the prior R40.4.3.3 private UI source map; identify the exact event constructor, dispatch method, InputContainer event name, view registration, and an in-bounds disposable touch position. The first new guest should dispatch **one** original event via real `UIManager:sendEvent`, verify the original source-bound view handler actually ran, then close and restore FileManager. A marker printed before dispatch or a direct call to `Canvas:addPoint` cannot count as event proof. Defer actual pen, stroke, save/reload, multi-event gestures and physical hardware until event routing is confirmed; do not fabricate PASS or alter original stage.

Strict reviewer must replay raw QEMU stderr, guest stdout and exit, require original R40.4.3.4 lifecycle and a uniquely sourced real callback marker, detect any unsafe or unresolved mutating syscalls, and refuse accidental external writes, unlinks or out-of-home paths. Preserve `NOT_BOOTABLE`, 1,101 unobserved regular stage files, 976 old UNKNOWN_HOLD records, and optional puzzle-pack hold. **No boot, device access, hardware actions, firmware writes or pruning.**
