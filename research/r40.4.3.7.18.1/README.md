# R40.4.3.7.18.1 — original new drawing lifecycle corrective synthetic trial

Research and education only. `NOT_BOOTABLE` remains unchanged.

**Observed D1:** the user's R3718.D1 diagnostic returned `CANVAS_STATE_ASSERTION`, phase `PREMARKER_CANVAS_STATE`, QEMU exit 1, inherited third-view marker present and no new R3718 gesture marker. Earlier source and 2,070-entry R26 stage preflight passed. No R3718 ARM PASS occurred.

**Source-based hypothesis, not yet a runtime result:** original InkAway save calls `rememberDoc(path)` and stores `inkaway_last_doc`; the original `openStartDocument` reopens that project when the plugin opens again. R3718's strict empty-third-view test may therefore contradict the original persistent document lifecycle. It is not evidence of broken original drawing behavior.

New package `pw3-os-r40.4.3.7.18.1-original-new-drawing.zip`, SHA-256 `a47e9cc57e0d9b9e255e65a4af623746666f80cfe9228741d8419b936472050b` (50,110 bytes, 13 files), clean extracted 53/53 host tests PASS, full ZIP CRC, SHA256SUMS and sh syntax PASS. Both intentional parent-source and guest-source corruption were rejected by the exact delta verifier.

The only new guest source block is immediately after genuine Tools-menu selection opened a third original InkAway view. Before proceeding it requires that the third view has genuinely reopened the exact earlier saved one-stroke project, is clean, and is owned by the original UIManager. It verifies source provenance for original `newDrawing` and `beginDocument`, then calls **original `menuview:newDrawing()`** to create a distinct, fresh unsaved document in the isolated synthetic HOME. No method replacement, editing of the saved previous project or fake canvas data is permitted. It verifies the original previous document still exists, then continues into the **unchanged** R3718 canvas-freshness assertion, synthetic touch/pan/release, original `closeCanvas` save and `Project.load` checks.

Original R3718 source and reviewer files remain unchanged in the parent package. New source verifier hashes all original R3718 artifacts, reproduces one exact insertion, verifies its own manifest, and invokes original R3718 source verifier and inherited R3717 chain. The new reviewer invokes original R3718 *semantic* reviewer against the new guest trace and requires its PASS, original R3717 strict reviewer PASS, original QEMU zero exit and both additional new-drawing markers in order. An ARM PASS cannot be inferred from host tests or the source-based hypothesis.

Unmodified R35 preflight rechecks thirteen staged Lua source files and the exact 2,070-entry R26 stage. Offline Docker uses the pre-existing arm64 image, no network, all caps dropped, non-root, no-new-privileges and read-only stage mount. Output must be a fresh directory. Keep private traces/source and user files off public GitHub.

R26 provenance remains unauthenticated; historic 347 regular opens not recomputed, 1,101 unobserved regular files and 976 UNKNOWN_HOLD retained, QEMU decoder incomplete, no complete dependency closure. No physical PW3 access, touch, firmware write, deletion, pruning, boot or deployment authorized. **NOT_BOOTABLE**.
