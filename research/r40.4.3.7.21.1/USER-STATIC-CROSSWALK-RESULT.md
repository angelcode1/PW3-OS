# R40.4.3.7.21.1 — user-observed static ELF/Lua crosswalk result

User Mac executed the exact-source-pinned read-only R3721.1. Its source delta, original R3720 hash, R26 2,070-entry content, R3718.1 synthetic ARM PASS, R3720 492-set replay and corrected enclosing-stage membership **all passed**.

Observed this one synthetic scenario: 492 distinct staged regular files: **29 ELF objects, 379 Lua files and 84 other regular files**. The full stage has 1,448 regular files; 956 not positively observed in this scenario, all retained.

ELF all-stage: 83 ARM ELF objects, 19 PT_INTERP segments, 209 DT_NEEDED name edges, 188 single direct regular basename candidates (153 candidate targets observed), 7 multiple candidate edges and 14 no-direct-regular basename candidate edges. The 29 observed ELF objects produced 76 DT_NEEDED name edges.

Lua all-stage: 823 Lua files and 6,306 lexical reference edges: 1,256 single regular name candidates (826 observed), 461 multiple, 4,589 with no lexical staged candidate. The 379 observed Lua files produced 3,591 literal reference edges. These are lexical candidates, NOT actual runtime package.path/FFI resolution.

No R26 source provenance authentication, dynamic loader resolution or transitive dependency closure. The 492 set and historic 347-file observed-open set are not path-comparable without lost original R401/402 path evidence; no safe prune inference. Previous 976 historical UNKNOWN_HOLD retained. The QEMU decoder remains incomplete. No physical PW3 device input/display, boot, firmware writes or deletion. Research and education only. **NOT_BOOTABLE**.
