# R40.4.3.0 — source-bound Ink Away canvas API reconnaissance (host only)

**2026-11-03: 38/38 host regressions PASS; original staged R13 source inspection on the user's Mac PENDING. The separate Ink Away canvas/stroke/save/return synthetic ARM/QEMU scenario remains NOT_TESTED_HOLD. NOT_BOOTABLE.**

## Prerequisite and actual reason for this gate

The user's R40.4.2 private/public two-scenario comparison was verified without exporting private source filenames: PDF observed-open set **347** staged regular files, FileManager-only **338**, common **338**, PDF-only **9**, FM-only **0**, union **347**. The prior R26 record matches 2,070 staged entries including 1,448 regular SHA-256 digests, 335 symlink targets and 287 directories; this does **not authenticate R26 provenance** or complete dependency closure.

The nine PDF-scenario-exclusive paths correspond to 7 Lua and 2 SVG files in the user's private comparison, but are not necessarily PDF-engine requirements because of different UI/plugin lifecycles. To learn anything new, a third independently traced workload must exercise **actual Ink Away canvas behavior**, not another FileManager startup.

## Standalone release artifact and provenance

Runnable artifact: `pw3-os-r40.4.3.0-inkaway-source-gate.zip`, SHA-256 `c6b2e8d111e418d7ed7853a5a553f6cba829c1dd3812ed00948a8561331ea9b0`. It contains `r4043/inkaway_source_gate.py`, `r4043/__init__.py`, `tests/test_r4043.py`, `README-R40.4.3.0.md`, `SCENARIO-MATRIX-R4043.json` and `SHA256SUMS-R4043`. Six archive entries and five manifest member hashes pass; ZIP CRC PASS and **38 host regression tests PASS**. The complete executable is supplied as the conversation ZIP; this GitHub entry is the release provenance/status documentation, not a claim that the Python source has been committed into GitHub.

The script requires the exact SHA-256 of the **user-verified R40.4.2 public JSON** `58707ea78858dbab3fc0763adceee20bd83d9fa2e587fdeb3bf3711ba1cc3416`, the source-pinned original R40.3 verifier `7f750452a520807bca6dd6084bf410e226c7bcb8e9f5fb227c4ee8ed72c4900c`, the original local R26 inventory, and a read-only R13 stage. It rehashes all 2,070 original records before examining four staged Lua source files in Ink Away: `main.lua`, `_meta.lua`, `ink/canvas.lua`, `ink/storage.lua`. It reports static function declarations, literal module references and lexical write-call hints. Static markers are **not** runtime call edge proofs; an unknown local plugin API stays on hold. No Lua execution, ELF loading, Docker, network, physical device, file modifications, stage writes, boot, deletion or firmware access.

Run the ZIP's `README-R40.4.3.0.md` locally. Share **only** `R40.4.3.0-SUMMARY.json`, not `R40.4.3.0-PRIVATE-SOURCE-MAP.json`, original R26 inventory, private QEMU events, or plugin source text. Source-contract result remains provisional until locally run, and no new Ink Away canvas ARM test has been performed.

The 1,101 unobserved stage regular files, original 976 UNKNOWN_HOLD entries, and future puzzles hold remain unchanged. No file-removal inference: `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Research/educational purposes only.
