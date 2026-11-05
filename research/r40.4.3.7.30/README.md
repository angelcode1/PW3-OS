# R40.4.3.7.30 — user-reported static EABI/float/SONAME classification

The user ran the read-only R4043730 standalone ZIP on their Mac and reported `INTERP_ABI_AND_SONAME_STATIC_CLASSIFICATION_ONLY`.

All **12** ELF references to the *single absent* `PT_INTERP` pathname have matching **ELF32 ARM EABI5/soft-float e_flags** relative to the single alternative candidate. **10** sources are ET_DYN and **2** are ET_EXEC. The alternate `ET_DYN` ELF's **DT_SONAME matches the missing basename**, its entrypoint is nonzero, its GNU stack is nonexecutable, and it has one executable and one writable PT_LOAD segment.

These findings strengthen *static* consistency but do not establish kernel loader selection, AAPCS/VFP argument ABI, relocation compatibility, runtime function, missing-path remediation, historical provenance or boot safety.

The parent R3726/R3727/R3728/R3729 SHA pins and replay were reported true. **The original rootfs was not modified.** The user-facing local ZIP has passed 10 synthetic tests; the source of that ZIP is **not in this commit**. This document records only user-supplied JSON, not an independently executed Mac stage audit. Full normalized stdout is in `USER-MAC-AUDIT-RESULT.json`.

**No source installs, symlink creation, boot, firmware writing, device access or pruning; NOT_BOOTABLE.**
