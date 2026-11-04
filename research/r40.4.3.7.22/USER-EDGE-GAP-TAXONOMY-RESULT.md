# R40.4.3.7.22 — user-observed read-only ELF/Lua reference taxonomy

The user ran the standalone edge-gap taxonomy with all original source pins and audit controls matching: R3721.1 source, R3720 source, original R26 content of all 2,070 entries, original R3718.1 synthetic ARM PASS, and exact original 492-file replay. Result: `STATIC_REFERENCE_TAXONOMY_ONLY_NO_PRUNE_NO_BOOT`.

ELF from observed source objects: 76 `DT_NEEDED` edges = **74 unique regular basename candidates** (70 candidate target files also observed, four candidate targets not observed) + **2 multiple candidates**; no observed-source zero-direct candidate. From unobserved ELF sources: 14 none, 114 single (83 candidate targets observed, 31 not observed), five multiple. These are basename candidates, **not loader resolutions**.

Observed-source Lua: `require`: 2,859 no lexical candidate, 436 single (413 target observed, 23 target not observed), 269 multiple; `dofile`: 27 single (18 target observed, nine not observed). No proof these static expressions executed or that a no-candidate lexical match means a missing runtime module. Computed modules, FFI and lexical comment/string false positives remain unresolved. Unobserved-source Lua reference categories retain their separate counts in the user-supplied R3722 stdout.

The companion ELF symlink/PT_INTERP static audit package already exists (`pw3-os-r40.4.3.7.22-elf-link-interpreter-candidates-readonly.zip`, SHA-256 `f991ee14c224300740fb6fcac30ac647958b5ddd1bff80033848682c7fe07f24`). Clean-extraction SHA manifest, ZIP CRC and **36/36 host tests** were rechecked. **User Mac execution of the ELF companion audit is still pending.** It classifies the 14 no-direct and seven ambiguous ELF edges plus 19 PT_INTERP segments, without running the loader, QEMU or device interfaces.

All historic 347-file set overlaps are unverified without lost R401/R402 raw crosswalks. In the new scenario 956 of 1448 regular staged files not positively observed, with separate 976 old UNKNOWN_HOLD. No R26 source authentication, dependency closure, physical PW3 I/O, boot, firmware writing, file pruning or deletion; research/educational purposes only. **NOT_BOOTABLE**.
