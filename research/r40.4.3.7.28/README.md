# R40.4.3.7.28 — independent PT_INTERP guest-path topology and static ELF candidate structure

**Read-only, host-only, research/education. NOT_BOOTABLE.**

R3727's user Mac run found **12 absent PT_INTERP segments referencing one distinct missing guest path**, and **one regular same-basename ELF-header-compatible alternate** at a *different* path. The R3727 and R3726 parent sources remain SHA-256 pinned and unchanged. The alternative is **not** an automatically selected or working runtime interpreter.

## What this stage checks

- Refuses modified parent R3727 and R3726 Python source files by exact SHA-256, then reruns the parent baseline, interpreter and alternate-name classifications against the local staged rootfs.
- Requires 1,446 staged regular files, 83 ELF objects, 19 PT_INTERP segments (9 strict and 10 padding-only), 7 direct matching guest path candidates and 12 guest absent-path holds.
- Checks that all 12 absent segments refer to **one unique guest pathname**, and that the same *single* compatible regular alternative is found for each source. Reports fixed counts only.
- Checks whether the **expected guest pathname's parent directory** exists, is an absent component, a symlink chain, or a non-directory/escape hold, without printing its text.
- Examines that one existing alternative's ELF type and the static presence and in-file bounds of PT_LOAD segments. No ELF is executed and no runtime loader is selected.

The potential interpretation is a *different directory layout or missing alias*, but **no change to rootfs is authorized**. Even `PARENT_DIRECTORY_PRESENT` and `ET_DYN` with PT_LOAD are only static evidence. Some loader-specific segments/relocations, kernel compatibility, RPATH/RUNPATH and runtime dependencies remain unchecked.

## Local macOS run (no git or gh)

Download `pw3-r3728-interp-path-topology-readonly.zip` into `~/Downloads`; the archive contains the tool, **both exact pinned parent source files**, the test suite and the checksum manifest. Run:

```sh
mkdir -p "$HOME/Downloads/pw3-r3728"
cd "$HOME/Downloads/pw3-r3728"
unzip -o "$HOME/Downloads/pw3-r3728-interp-path-topology-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -m unittest discover -s . -p 'test_*.py' -v
python3 R4043728-INTERP-PATH-TOPOLOGY-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-r3727 "$HOME/Downloads/pw3-r3728/R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py" \
  --parent-r3726 "$HOME/Downloads/pw3-r3728/R4043726-INTERP-GUEST-RESOLVE-READONLY.py"
```

The test suite should report **17 tests, OK**. The stage audit result, if prior evidence remains unchanged, is `INTERP_SINGLE_PATH_TOPOLOGY_CLASSIFIED_ONLY`, with the new `missing_parent_directory_categories` and `candidate_elf_structure` classifications. A `HOLD` is not an instruction to loosen checks or alter stage files.

The script's stdout is aggregate-only and does not export any guest or host source paths or symlink contents. It does not reauthenticate original R26 source provenance or historical 2,070-entry hash membership; parent SHA checks certify **tool script bytes only**, not firmware provenance. It does not establish actual kernel interpreter selection, loader ABI or transitive dependency closure, inspect the physical PW3, run QEMU/ELFs, modify stage files, create aliases, boot, flash, prune, or authorize file removal. All holds remain **NOT_BOOTABLE**.
