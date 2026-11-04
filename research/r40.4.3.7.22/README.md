# R40.4.3.7.22 — read-only ELF symlink and interpreter candidate classification

**Host-tested only; user Mac execution pending. Research/educational purposes only. NOT_BOOTABLE.**

The exact R3721.1 user-side read-only crosswalk PASS identified 83 staged ELF objects, 209 DT_NEEDED literal name edges (188 single regular basename candidates, 7 multiple candidates, 14 without direct regular basename candidate), 19 PT_INTERP segments, and 29 observed ELF objects with 76 dependency-name edges from the verified 492-file R3718.1 trace.

Package: `pw3-os-r40.4.3.7.22-elf-link-interpreter-candidates-readonly.zip`, exact ZIP SHA-256 `f991ee14c224300740fb6fcac30ac647958b5ddd1bff80033848682c7fe07f24`; 9,680 bytes, four archive entries. Tool `R4043722-ELF-LINK-INTERP-CANDIDATES-READONLY.py` SHA-256 `fcaa788b4d5fa1cdc73f90b6c927703615fa4df3fab8f5fbef67271efaaabb36`. Clean extracted 36/36 tests PASS, SHA256SUMS PASS, ZIP CRC PASS, Python CLI check PASS.

Tool pins original R3721.1 classifier SHA256 `c7a987b16ccfe119a0fac5388d20c28a4050bcd7bff5f4dad7d0b457a3c864b4`, uses its pinned R3720 source and original R403 R26 full 2070-entry content check, authenticates R3718.1 public result and QEMU zero exit and reconstructs the original 492-file set before analysis. Re-runs original static scanner and requires exact 83/209/19/29/76/492 parent statistics and 7/14 edge category counts.

The extra read-only step classifies staged direct/aliased SONAME basename candidates for no-direct and ambiguous DT_NEEDED names and the literal PT_INTERP pathname status, resolving only inventory symlink chains within a **modelled rootfs guest namespace**, with bounded cycles, symlink traversal, dangling aliases and paths leaving that modelled guest root held. This does not implement real loader RPATH/RUNPATH, LD_LIBRARY_PATH, native ABI checking, FFI or physical hardware; a symlink alias ending at an existing staged regular file is a STATIC CANDIDATE ONLY, not actual loader selection or bootability.

No private paths or raw trace exported. No QEMU rerun, network, stage changes, firmware writes, physical PW3, deletion or pruning. All 956 stage regular files not observed in R3720 remain protected, as do 976 separate older UNKNOWN_HOLD. Original R26 source provenance unauthenticated, dynamic dependency closure unproven, and previous historic 347-file crosswalk unavailable. **NOT_BOOTABLE**.
