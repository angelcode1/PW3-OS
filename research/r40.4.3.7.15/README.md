# R40.4.3.7.15 — source-bounded synthetic UIManager KeyPress trial

Research and educational purposes only. Immutable `NOT_BOOTABLE`.

The user-supplied R3714 report and summary both returned `R40_4_3_7_14_ORIGINAL_KEYPRESS_WIDGET_DISPATCH_ARM_PASS`, SHA-256 `643e921b7c59248e75c691c17afe844ab9c87ea9f0cf389f40f196e15a736030`. The original widget-level KeyPress, negative key, next-page and previous-page and original TouchMenu selection were observed; **UIManager-wide synthetic KeyPress was not**.

The next package `pw3-os-r40.4.3.7.15-uimanager-keypress.zip` was built in this research conversation and has SHA-256 `ed4bfa2236513cfddeca5b96cf1541651e202bcad18d5e38537973f59d41a980`, 46,052 bytes, 13 members, **49/49 local host tests PASS**, verified archive manifest and ZIP CRC, and shell syntax PASS. No ARM/QEMU trial for R3715 has been run.

The exact pinned one-site guest insertion is after successful original R3714 widget-level key roundtrip and before the unchanged original TouchMenu selection. The original `UIManager:sendEvent(Event:new("KeyPress", key))` is used three times (unmapped, next-page, previous-page). Source-provenance checks demand the original UIManager, Event, WidgetContainer, FocusManager and TouchMenu methods; window-stack ownership and original page state must remain consistent. Negative event must not change state, page next/previous must roundtrip through original UIManager delivery. A sanitized PASS requires the original R3714/R3713/R3712 and inherited strict reviewers, all six exact marker positions in order, zero guest exit, and original R35 full staged-source/R26 2,070-entry preflight. Inherited core, plugins, stage and security gates are unmodified.

This is **application-level UIManager delivery**. It does not exercise a physical key or touch event, the kernel/OS input driver, `UIManager:handleInputEvent` or the device input poll loop. An ARM PASS would not imply physical PW3 compatibility, boot authorization, firmware write authorization, safe file pruning or complete dependency closure.

Historical retains: R26 unauthenticated provenance, incomplete QEMU syscall decoder, 347 regular opens not recomputed, 1,101 unobserved staged regular files, 976 unknown holds. Private source/evidence and raw logs stay local; only sanitized status recorded on public GitHub.
