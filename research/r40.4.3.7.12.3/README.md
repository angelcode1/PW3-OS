# R40.4.3.7.12.3 — original public-release-only prerequisite restoration

Research and educational purposes only. HOST TESTED; Mac restoration not yet performed. NOT_BOOTABLE.

User's R3712 all-prerequisite audit reports 3 of 13 public release directories valid (38 pinned files), with ten absent public releases (R3710, R378, R375, R3741, R373, R372, R37, R36, R353, R35), two original R376 collector outputs absent at their expected paths and the R13 staged rootfs absent at its expected path. The shell current working directory does not affect the audit (its default root is the user's Downloads). A missing canonical path does not imply the underlying data has been deleted or is absent from other offline locations.

Standalone conversation artifact: pw3-os-r40.4.3.7.12.3-public-prerequisites.zip; SHA-256 a922f43a9a3b6cae8244143d6fb66e341fde0b0d9640e31a9dce34cb39d597db; 432,369 bytes; 14 outer members (10 SHA256+member-pinned original public release ZIPs, independent pins, README, no-clobber restore script, checksum manifest). All ZIP CRC checks and original file pins passed.

After extracting into Downloads/pw3-os-r40.4.3.7.12.3-public-prerequisites: (1) run shasum -a 256 -c BUNDLE-SHA256SUMS; (2) run python3 -B RESTORE-PUBLIC-R3712.py to inspect only; (3) after inspecting its valid plan, optionally run python3 -B RESTORE-PUBLIC-R3712.py --apply. Restore creates only previously absent original public release directories and postchecks every member. It refuses incomplete, modified or symlinked existing releases and tampered nested archives. It never overwrites, moves, deletes or touches source stage or private collector files.

Verified in temporary clean test fixtures: dry run wrote nothing; all ten public releases restored and hashes rechecked; complete 13-release audit passed after restoring three already-present releases; the two separate original collector file digests matched when independently provided; repeat plan idempotent; tampered existing public release and symlink refused without overwrites; corrupted archive refused before writing.

The R376 private collector ZIP, its public audit JSON and the original R13 staged rootfs are NOT supplied by this public bundle. They must be restored separately from user-owned trusted offline originals at the exact canonical paths. Never fabricate the rootfs, use generic replacement source, run physical device reads, or bypass prior R35 2,070-inventory/authenticity checks. Full unchanged R3712 stage-check is still required; any audit PASS is not a QEMU PASS. The reported R3711 original TouchMenu INDEX_ERROR site remains unverified.

Historical observed stage regular-file open union 347 not recomputed; 1,101 unobserved stage files and 976 UNKNOWN_HOLD retained. QEMU decoder incomplete, R26 provenance unauthenticated, complete dependency closure unproven. No boot, hardware or firmware writes, file removal or pruning authorization. NOT_BOOTABLE.
