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


## Audited private source capture and bounded new R40.4.3.5 release (2026-11-03)

The user provided `R40435-STAGED-UI-SOURCES-PRIVATE.zip`, with exactly 13 original staged Lua modules plus a private manifest. Its archive SHA-256 is `68caa882ab99c9fd83458b59a97efba011aa798ef1f9e76c540a93ed2ec5e29d`; all 13 archive members match their private manifest hashes. This is *not* a recheck of the physical Mac stage: the eventual preflight must again compare every archived digest against the real original read-only stage, and rehash all 2,070 original R26 entries through the old pinned auditor. No original Lua source or extracted private source map was committed.

Source inspection established the actual staged route: `UIManager:sendEvent(Event:new("Gesture", g))` delivers to `InputContainer:onGesture`, which uses the view's real `ges_events` and `GestureRange:match` to invoke original Ink Away handlers. In the staged view the `two_finger_pan` and `two_finger_pan_release` handlers manipulate transient pan state, without inherently committing a drawing. The proposed experimental run opens a genuine `inkaway_view` using the previous **R40.4.3.4** source-pinned FileManager guard, dispatches one pan and its release through the original KOReader event pipeline, checks `view.pan_last` transitions nil→synthetic coordinates→nil and that `view.canvas.ops` stays empty, then closes the view and FileManager using the pre-existing path. It does NOT call the InkAwayView handlers directly, replace widgets, or test physical pen/touch, project save, application menu event or full UI lifecycle.

**Release available in this conversation:** `pw3-os-r40.4.3.5-native-ui-gesture.zip`, SHA-256 `a329ac5993a1a517cb02f2a1e34f705c178afd0b2968700613cf99e043f570fc`, 38,464 bytes; 10 ZIP entries (9 SHA-256 manifest members), ZIP CRC PASS; **70 host tests PASS**, both shell scripts syntax checked. Full release, reviewer, code and exact Mac commands are supplied inside `README-R40.4.3.5.md`. Only provenance and hash manifest live in this public repository; private original Lua sources and QEMU traces remain local. The guest uses the existing Docker image without rebuild, original rootfs readonly, no network, no Docker capabilities, unprivileged user and disposable /tmp HOME. Strict reviewer checks ordered lifecycle/event markers, QEMU exit and decoded mutation confinement. QEMU Linux-user partial syscall decoding still limits safety claims.

**Status: ARM/QEMU R40.4.3.5 NOT YET RUN.** This host/tested source gate is not another runtime PASS. Existing R40.4.3.4 public view-only reviewer PASS remains historical and the raw trace is still unavailable for independent replay. No new staged-file union was computed (historic 347 only). All 1,101 unobserved stage regular files, 976 historic UNKNOWN_HOLD and future optional puzzle package are retained. **Research and educational only: NOT_BOOTABLE, NO_DEVICE_ACCESS, NO_FIRMWARE_WRITES, NO_BOOT, NO_PRUNING.**


## R40.4.3.5 uploaded public failure and private-trace-safe diagnosis (2026-11-03)

The user's actual new guest run produced the public **FAIL** review `R40435-REVIEW.json` with SHA-256 `d1ca44869a2327b9b0ff91b5daaf1a443a6e348bc6c80606d152127114450cc2`, `verdict=R40_4_3_5_GUEST_OR_REVIEW_FAIL`, `failure_class=genuine_view_lifecycle_or_trace_mutation_guard_failed`. This class is **generic by design**: original `r40435/review.py` catches exceptions and writes the same failure class for nonzero guest exit, missing/duplicated gesture/lifecycle marker, decoder rejection, pathless/unaudited mutations or invalid pinned sources. No privately held guest stdout, QEMU raw trace or exit status was uploaded, so the exact blocker **is not known**. The previous R40.4.3.4 view-only PASS is unchanged. The failed R40.4.3.5 run does **not** confer synthetic gesture/input PASS, stroke/save PASS, stage-file union change or boot/pruning permission.

A **new read-only failure diagnostic**, `pw3-os-r40.4.3.5-failure-diagnostic.zip` (ZIP SHA-256 `aa9d190f1a7501897b10917865e5731dbb075bd2850eb0edea6b8cb547917a25`; 4 entries; 18 host tests PASS), reads the **existing failed run's** private three trace artifacts on the user's Mac. It statically pins the original R40 decoder and R40.4.3.5 Python reviewer/preflight before classifying the first missing lifecycle marker, QEMU exit, split decoder validity and the first rejected mutation kind. It exports **no raw file paths, lines, exception text, or private stdout**, only named fixed markers and flags. Run the exact Mac command in `README-R40435-FAILURE-DIAGNOSTIC.md` included with the ZIP and upload only `R40435-FAILURE-DIAGNOSTIC-PUBLIC.json`. Preserve the failed output directory and don't rerun it or patch assertions to force PASS.

No inference of new observed stage opens: the historic 347-file baseline and 1,101 unobserved regular-file hold remain unchanged. The 976 historical UNKNOWN_HOLD records also remain protected. The real drawing stylus/stroke/save/return lifecycle stays `NOT_TESTED_HOLD`. **Research/education only; NOT_BOOTABLE; no device/firmware/hardware operations; no file pruning.**


## User redacted local diagnostic (2026-11-03)

The user's R40.4.3.5 read-only local diagnostic passed **18/18 host tests**, then reported **QEMU exit 1**, 9,155 syscall lines and 4,625 decoded path events, with the **decoded mutation guard PASS** and no first rejected mutation category. The last completed strict marker was `R40434_GENUINE_VIEW_ADDED_TO_UI_MANAGER`; the first missing marker was `R40435_NATIVE_UI_GESTURE_DISPATCH_READY`. This local report shows the failure happened *after genuine view creation but before native gesture readiness*, not at later event dispatch or view teardown. Decoder validity was false due to bad/unparsed QEMU stderr flags, which may include guest error output and is not evidence of an unsafe mutation. No runtime gesture PASS can be claimed.

Source inspection of the original released R40.4.3.5 guard reveals `reader.lua` is executed under `pcall` and an unrecognized inner exception is subsequently replaced by a generic FileManager shutdown assertion. Consequently the original failure data does **not** reveal which one of the original native event-source/handler/registration/geometry assertions failed. The staged `ink/view.lua` does register the two-finger gesture bindings conditionally on `Device:isTouchDevice()`; absent touch capability is only a **hypothesis**, not a verified cause.

A new **R40.4.3.5.1 diagnostic-only experimental release** reuses the exact original stage source pins and R26 preflight. It adds one fixed-category, private-path-safe classifier *after* the protected `reader.lua` call, retaining the original fail-closed assertion and all original KOReader/InkAway methods unchanged. **29 host tests PASS; ARM/QEMU diagnostic rerun pending.** The release must never be interpreted as an ARM gesture PASS or a correction. See [R40.4.3.5.1 release record](../r40.4.3.5.1/README.md).
