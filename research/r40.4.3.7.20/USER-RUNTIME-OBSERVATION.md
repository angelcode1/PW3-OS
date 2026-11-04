# R40.4.3.7.20 — user-observed bounded single-scenario runtime opens

User reports the source-pinned **read-only** R3720 audit succeeded against the original R26 stage and verified R3718.1 ARM PASS report. R26 2,070-entry content PASS, `ALL_RECORDED_ENTRIES_MATCH_UNAUTHENTICATED`; R26 origin still not authenticated. R3718.1 original reviewer PIN and semantics PASS; QEMU guest exit zero.

Original QEMU raw-trace bounded parser statistics: 11,378 lines total; 4,487 open-like; 998 successful, 3,488 failed and 1 traversal/path hold; 0 undecoded; 66 successful external, 932 successful mapped to stage; 7 mapped successful nonregular, 0 symlink or missing success holds; 0 CWD changes and 0 process creations. **492 distinct unambiguous regular staged files** observed opened in this R3718.1 synthetic InkAway scenario. Of 1,448 stage regular files, **956 were not positively observed by this scenario**; this is not a safe-removal count. `MAPPING_CONFIDENCE=PARTIAL` explicitly retained.

Historical 347-file union from original R40.1/R40.2 experiments remains a **separate historically reported figure**, not independently recomputed because the original five path-level crosswalk inputs remain unavailable. The 492 and 347 **cannot be summed or compared path-by-path**. Historical 1,101 unobserved were specific to those earlier workloads, whereas 956 unobserved is specific to this single new workload. Historic 976 older UNKNOWN_HOLD entries are a distinct evidence population.

No static transitive ELF/Lua dependency closure established, no loader resolution guarantee, no physical PW3 I/O, input waitEvent, boot, firmware changes, rootfs pruning or device writes. Research/educational purposes only. **NOT_BOOTABLE.**
