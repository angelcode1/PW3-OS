# R40.4.3.7.29 — read-only alternative interpreter ELF dynamic/header audit

**Research/education only; host synthetic tests 11/11 PASS. Mac stage run: NOT EXECUTED. NOT_BOOTABLE.**

R3728's user-reported audit identified 12 PT_INTERP segments referencing one absent guest interpreter path. Its parent directory exists. Another regular same-basename ELF at a different guest pathname is ET_DYN with two PT_LOAD segments and zero PT_INTERP segments; that remains only a **static candidate**, not a selected or proven runtime loader.

This standalone source-only R3729 audit pins the exact unmodified R3726, R3727, and R3728 scripts; replays the original 83 ELF / 19 PT_INTERP / 7 matching / 12 absent baseline and original alternative's static topology; then reads **only** the already staged unique candidate's bounded ELF headers, ARM ELF e_flags and PT_DYNAMIC integer tags (DT_NEEDED count, DT_SONAME, DT_RPATH, DT_RUNPATH, DT_STRTAB, DT_STRSZ presence). It does not extract or print library or path strings, and it does not resolve needed libraries. Its EABI/float flags are **header-only hints**, not full float ABI verification: `.ARM.attributes`, loader startup and Linux 3.0.35 kernel compatibility are untested.

## Mac usage without git or gh

Download `pw3-r3729-elf-dynamic-readonly.zip` to `~/Downloads`, then:

```sh
mkdir -p "$HOME/Downloads/pw3-r3729"
cd "$HOME/Downloads/pw3-r3729"
unzip -o "$HOME/Downloads/pw3-r3729-elf-dynamic-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -m unittest discover -s . -p 'test_r4043729.py' -v
python3 R4043729-INTERP-ELF-DYNAMIC-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-r3726 "$PWD/R4043726-INTERP-GUEST-RESOLVE-READONLY.py" \
  --parent-r3727 "$PWD/R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py" \
  --parent-r3728 "$PWD/R4043728-INTERP-PATH-TOPOLOGY-READONLY.py"
```

The real stage result is **unknown** until run on the user's Mac. A successfully classified result would be `SINGLE_ALTERNATE_ELF_DYNAMIC_METADATA_CLASSIFIED_ONLY`, still under `NOT_BOOTABLE`, with non-sensitive aggregate fields. A `HOLD` result means stop and inspect the category; never weaken the source pins or change stage files to obtain a PASS.

All packages proposed for future OpenSSH, SFTP and rsync ebook transfers are a separate *post-validation image requirement* in `docs/PW3-REMOTE-TRANSFER-PLAN.md`. This R3729 tool does **not** install or enable any service, run QEMU or ELFs, connect to a physical device, create a symlink/alias, copy or remove staged files, flash firmware, boot, or authorize pruning. Original R26 provenance, historic file-hash membership, dynamic transitive dependency closure, kernel hardware and recovery remain held.
