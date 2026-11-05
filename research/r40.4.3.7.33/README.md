# R40.4.3.7.33 — read-only PT_INTERP exact guest-path layout

**Host-only, source-pinned analysis. NOT_BOOTABLE. No device access or stage writes.**

## Why this exists

The user-reported R3732 audit shows 12 requesting ELF objects and one alternative ELF with equal declared CPU/FP architecture numeric tags, but some values are undeclared. Numeric tag equality does not establish loader compatibility. Earlier R3727–R3729 already established one distinct missing PT_INTERP guest path, a present parent directory, and one ELF-header-compatible same-basename alternative **at another guest path**. Future-independent-image layout work needs the precise two guest paths to distinguish an ordinary missing alias/leaf from a more complex layout change. A kernel does not search by SONAME for PT_INTERP.

## What this tool does

- Verifies the exact unchanged R3726 and R3727 source SHA-256 values, imports them and independently replays their original read-only 83 ELF / 19 PT_INTERP / 7 direct / 12 absent source inventory, plus 335 rootfs symlinks.
- Rechecks that all 12 failed segments refer to the same missing path and exactly one other regular ELF-header-compatible same-basename alternative.
- By **default**, emits only guest directory-layout categories and counts, with **no guest paths**.
- With `--show-local-guest-paths`, deliberately prints the **two guest pathnames** on the user's own Mac terminal for human review. This option does not upload, store, open, or modify any source file. Only share those paths if comfortable. The flag does not print any other private stage filenames.
- Does not propose or create an alias, install a loader, copy/rename any file, execute an ELF, run QEMU, flash, boot or prune.

## Mac run with no git or gh

Download `pw3-r3733-interp-layout-readonly.zip` into `~/Downloads` and extract it. The earlier R3732 download already contains the exact required R3726 and R3727 parent scripts.

```sh
mkdir -p "$HOME/Downloads/pw3-r3733"
cd "$HOME/Downloads/pw3-r3733"
unzip -o "$HOME/Downloads/pw3-r3733-interp-layout-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -m unittest discover -s . -p 'test_r4043733.py' -v
python3 R4043733-INTERP-LAYOUT-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$HOME/Downloads/pw3-r3732"
```

Optionally rerun the same command with `--show-local-guest-paths` to see the requested interpreter guest path and alternate candidate guest path **only locally**. The local path strings can guide a **future independently constructed image** design, not any edits to the original R13 staged rootfs. If `HOLD` appears, retain the hold.

**Limitations:** does not reauthenticate original R26 source provenance, 2,070 historic inventory hashes, real kernel loader selection, CPU hardware features, floating-point calling convention, transitive dependencies, startup, independent image/recovery, or physical PW3. The separate future OpenSSH, SFTP and rsync requirements are unchanged. **NOT_BOOTABLE.**
