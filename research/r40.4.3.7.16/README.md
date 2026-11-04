# R40.4.3.7.16 — original input-event default dispatch, synthetic only

Research and educational purposes only. **NOT_BOOTABLE.**

User uploaded byte-identical R3715 REVIEW and SUMMARY (SHA-256 `1f475fab584c0b31db5811bd2d2bb16fb063a7d90fb8831ccc2590b0bc90e99c`) and terminal `R40_4_3_7_15_ORIGINAL_UIMANAGER_KEYPRESS_DELIVERY_ARM_PASS`. Guest exit 0; original R3714 strict reviewer PASS; original UIManager:sendEvent boundary authenticated; unmapped key rejected; next/previous original TouchMenu page roundtrip and InkAway menu selection exercised.

The local R3716 package `pw3-os-r40.4.3.7.16-input-event-default-dispatch.zip` (SHA-256 `a9df04d0ca79d043d92ead84c7a5b8180e5647f7f358576924fd020d515d4bc4`, 46,487 bytes, 13 members) was built from the verified R3715 source tree. **51/51 host tests PASS**, SHA256SUMS and ZIP CRC PASS, shell syntax PASS, and parent SHA/source pins + exact one-site insertion verification PASS in local test mode. **No R3716 ARM/QEMU run has occurred.**

The one new source-bounded injection runs immediately after original R3715 `UIManager:sendEvent` key roundtrip. It checks original source provenance for `UIManager:handleInputEvent`, original `UIManager:sendEvent`, and original `event_handlers.__default__`, validates that input Event objects use `onKeyPress` and no specialized handler overrides them, and sends three synthetic KeyPress events to the *original* `real_ui:handleInputEvent`: an unmapped key leaving the menu unchanged, next-page (`RPgFwd`), and previous-page (`RPgBack`) restoring page and menu ownership. The unchanged original InkAway TouchMenu selection must still succeed. Strict marker ordering and inherited R3715/R3714/R3713/R3712 reviewers are required, as is original R35 complete staged-source and 2070-entry R26 inventory preflight before offline Docker.

**Scope:** this uses direct synthetic injection into the original input event dispatcher; it does NOT invoke the device waitEvent polling loop, evdev, physical key/touch/stylus, or a real PW3. Even ARM PASS would not prove physical input or device bootability. Preserve existing offline image, no network, read-only stage bind, no new capabilities. All private logs and source evidence remain local.

Historic limits remain: 347 regular opens not recomputed, 1,101 unobserved regular files, 976 UNKNOWN_HOLD, incomplete QEMU decoder, unauthenticated R26 inventory provenance. No boot, firmware write, hardware access, deletion or pruning authority; NOT_BOOTABLE.
