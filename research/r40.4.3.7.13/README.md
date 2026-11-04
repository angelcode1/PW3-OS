# R40.4.3.7.13 — original TouchMenu three-key input fixture ARM PASS

Research and educational purposes only. `NOT_BOOTABLE` remains immutable.

User-provided sanitized `R4043713-REVIEW.json` and `R4043713-SUMMARY.json` have matching exact bytes (SHA-256 `e792d2bc1294d7643db1d13573fabc182fd173caf39c6ba252d8843ee681042d`). Both give `R40_4_3_7_13_ORIGINAL_TOUCHMENU_THREE_KEY_GROUP_ARM_PASS`, `guest_zero_exit=true`, original menu show returned, synthetic key group COMPLETE, original R3712 marker order and strict reviewer PASS, and synthetic TouchMenu selection exercised. Original R3712 TouchMenu line-518 source error is no longer observed (`NOT_APPLICABLE`).

The standalone R3713 reviewer requires previous R3712 reviewer PASS, the original menu-show and three synthetic key-group markers, and a zero guest exit. It sets the synthetic selection flag only on strict PASS. The R3713 launcher copies the review bytes into summary on PASS, explaining the identical JSON outputs.

Limits: no physical keyboard/touch/stylus/menu tap, no PW3 boot or hardware testing; R26 provenance not authenticated, incomplete QEMU syscall decoder, historic 347 regular opens not recomputed, 1,101 unobserved regular files and 976 unknown holds retained. No safe pruning inference, writes to firmware, or change to the original KOReader stage, historical inventory, original reviewers, or safety gates.

Proposed successor is a separately source-bounded synthetic input-event dispatch experiment through an original KOReader handler, preserving all inherited verifier gates and never claiming physical input. This experiment has **not been built or run**.
