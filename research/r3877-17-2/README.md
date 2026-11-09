# R3877.17.2 — ELF SHT_NOBITS fix and GNU symbol-version evidence

Research and education only. **NOT_BOOTABLE**. No firmware modification or Kindle boot authorized.

## Verified user-reported run (Mac, not CI)
The R3877.17.1 single-SSH audit successfully transferred the designated KOReader/application and stock system-library ELF bytes, then failed in the local GNU version parser at `koreader/libs/libcrypto.so.57` with `SECTION_DATA_OUT_OF_BOUNDS`. The original parser required all sections to fit in file-backed byte extents, incorrectly including `SHT_NOBITS` (type 8). `SHT_NOBITS` has no file payload, even when `sh_size` declares a nonzero memory extent. The corrected parser exempts **only** this section type; it still enforces bounds on every file-backed section and GNU version/string tables.

The subsequent user-reported R3877.17.2 run returned `PASS_VERSION_NAMES_METADATA_ONLY`: 38 app ARM ELF files, 7 stock providers, 174 requirements, 44 versioned requesting files, zero absent required version names, 48 `SHT_NOBITS` sections, and 10 files with non-file-backed extents. These findings confirm the cause hypothesis, but **do not** prove symbol exports/relocations, runtime dependency resolution, atomic source snapshots, Alpine syscall compatibility, original R13 provenance or recovery.

## Reproduction
The complete independently delivered local ZIP is `pw3-r3877-17-2-nobits-fix.zip`. The minimal patch below applies to the prior `r3877_17_version_parser.py` and contains a fail-closed regression. Run complete ZIP tests locally before trusting the result. The patch in this repository is source-only; GitHub CI does not access Colima, Kindle SSH or private binaries.

The original soft-float glibc KOReader environment must not be combined in-process with the hard-float musl Alpine candidate. Never replace interpreter symlinks or install candidate binaries onto the PW3 on the basis of these metadata-only results.
