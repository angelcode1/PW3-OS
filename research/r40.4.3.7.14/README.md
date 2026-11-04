# R40.4.3.7.14 — synthetic original TouchMenu widget KeyPress dispatch

Research/educational only. `NOT_BOOTABLE` retained.

The user's R3713 ARM reports passed the original TouchMenu show/selection chain with the three synthetic key groups completed. This proposed successor tests **widget-level synthetic KeyPress handling**: an unmapped original Key object, an original next-page key `RPgFwd`, then original previous-page `RPgBack`, verifying menu page roundtrip and continuing into the original TouchMenu selection. It calls the original KOReader `FocusManager:onKeyPress` inherited by TouchMenu; **it does not deliver an event through UIManager or claim a physical button/keyboard/tap**.

The standalone ZIP `pw3-os-r40.4.3.7.14-original-keypress-widget.zip` has SHA-256 `74a3e41911dad4f5c1b60a91b39f5d3479268a7b748d88e73a674f7c03c2a2c5`, 13 members and 42/42 local host tests PASS. Shell syntax, member checksums and archive integrity passed in the research container. It is **not** an ARM PASS: no R3714 guest execution has occurred.

The source verifier SHA-pins the entire original R3713 guest, verifier, reviewer, entry, probe and reference, and rejects anything but one exact guest diagnostic insertion. The unchanged strict R3713/R3712 reviewer chain and R35 original staged-source / R26 2,070-entry preflight must pass. No modification to original input implementations, TouchMenu, R13 stage or earlier source gates.

The user can extract ZIP into an absent, non-symlinked `~/Downloads/pw3-os-r40.4.3.7.14-original-keypress-widget`, check `SHA256SUMS-R4043714`, run `RUN-R4043714-MAC.sh test`, `stage-check`, then existing offline Docker doctor before running `trial` in a new output directory. Send sanitized `R4043714-REVIEW.json`; retain raw guest/QEMU traces locally.

Historical unknowns remain unchanged: unauthenticated R26 provenance, incomplete syscall decoder, 347 previous regular opens not recomputed, 1,101 unobserved regular staged files, 976 UNKNOWN_HOLD. No physical device or firmware validation. No dependency closure, deletion, pruning or boot authorization. `NOT_BOOTABLE`.
