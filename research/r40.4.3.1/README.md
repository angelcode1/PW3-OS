# R40.4.3.1 — source-pinned Ink Away view/stroke/storage route inspection

**Date:** 2026-11-03. **HOST PASS: 45 Python tests. MAC STAGE AUDIT: PENDING. ARM/QEMU NEW CANVAS SCENARIO: NOT_TESTED_HOLD. NOT_BOOTABLE.**

This follows the user's successful R40.4.3.0 source-contract scan, which confirmed original menu/openCanvas/canvas-stroke declarations but did not execute a canvas. The source-chain gate reads another five *original staged* files, rehashes the original R26 inventory (2,070 entries) using pinned R40.3 code, and rechecks all four earlier R40.4.3.0 source records against the private original. It accepts only original unchanged code. No staged source is patched, executed or bundled into the public results.

Five additional source roles: `ink/view.lua`, `ink/view/document.lua`, `ink/view/stroke.lua`, `ink/view/input.lua`, `ink/project.lua`. It examines lexical method definitions and call-site strings for the prospective route from plugin openCanvas→InkAwayView→UIManager input→Canvas stroke commit→saveDocument→Project.save→Storage.writeAtomic. These strings do **not** establish a semantic Lua call graph, runtime execution or write-path isolation. Missing/renamed signals result in `SOURCE_ROUTE_INCOMPLETE_HOLD`, not an inferred API.

**Important prospective storage safety issue:** the upstream Ink Away `Storage.writeAtomic` implementation contains a fallback `os.remove(path)` before retrying a failed rename; presence in the user's staged copy is not yet established. A later new offline synthetic QEMU workload must use a newly isolated disposable synthetic HOME and independently ensure every write, rename and unlink occurs inside that disposable location. Do not open a real device or save to staged directories.

[Download source release](https://github.com/angelcode1/PW3-OS) — the **versioned conversation ZIP** `pw3-os-r40.4.3.1-view-storage-contract.zip` has SHA-256 `0fe6e461bc4f2f0602cdef485544e393bea60dd81068ee09c81bd63feb480286`, six entries, five member checksums; 45 unit tests PASS. All runnable source/test files are included in the ZIP; this GitHub entry stores the release manifest and reproducible command reference, not private source files. Run `README-R40.4.3.1.md` in the ZIP to obtain `R40.4.3.1-SUMMARY.json` and `R40.4.3.1-PRIVATE-VIEW-STORAGE.json`. **Share summary only.**

The original R40.4.2 observed file-open union remains 347; all 1,101 unobserved regular entries and previous 976 UNKNOWN_HOLD retained, not additive. Future optional puzzles unbuilt.

**Research only:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`.
