# R40.4.3.7.27 — missing PT_INTERP basename alternatives, read-only

**Research and educational use only. Host synthetic tests: 15/15 PASS. Real Mac stage run: NOT YET EXECUTED. NOT_BOOTABLE.**

R4043726 found 19 interpreter segments and exact rootfs baseline (1,446 regular staged files, 83 ELF files, 9 strict and 10 padding-only interpreter strings), of which **7** resolved to matching ELF-header candidates and **12** returned `GUEST_ABSENT_HOLD`. The next task is to check whether those 12 failed *segments* share the same missing literal and whether same-basename files or symlink aliases already exist **elsewhere** in the stage. This cannot prove kernel selection or runtime loader suitability.

The R3727 script checks the unchanged R3726 parent's exact SHA-256 (`7068af571b0c57677793eb5722938b3a4f14abfd5ce33c6b4e4ce41040e117b3`) before importing it, replays the parent's 83/19/9/10/1446 source counts and 7/12 pathname classifications, then enumerates same-basename entries without following directory symlinks. It emits **only aggregate categories**, including unique missing guest paths/basenames; no filenames, guest path literals or link targets. The parent checks ELF class, endianness and machine, not complete loader ABI.

The tool **requires the existing R3726 script**, as previously downloaded to `~/Downloads/pw3-r3726/R4043726-INTERP-GUEST-RESOLVE-READONLY.py`. It does not silently fetch, replace or modify the parent. If it reports `HOLD`, inspect the category and do not weaken the parent pin.

## macOS commands without git or gh

Download the R3727 ZIP to `~/Downloads`, then run:

```sh
mkdir -p "$HOME/Downloads/pw3-r3727"
cd "$HOME/Downloads/pw3-r3727"
unzip -o "$HOME/Downloads/pw3-r3727-interp-absent-alternatives-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -m unittest discover -s . -p 'test_*.py' -v
python3 R4043727-INTERP-ABSENT-ALTERNATIVES-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-script "$HOME/Downloads/pw3-r3726/R4043726-INTERP-GUEST-RESOLVE-READONLY.py"
```

Expected successful classification: `ABSENT_INTERP_SAME_BASENAME_ALTERNATIVES_CLASSIFIED_ONLY`, with `absent_interp_segments: 12`. The parent counts must match exactly. The category table is **new and unknown** until the actual Mac stage audit is run. The tool may conclude that no same-basename entries exist, that same-basename entries exist but do not match ELF headers, or that one or multiple header-compatible alternatives are present. **Every alternative remains only a static candidate at its original separate path**. Missing guest paths remain missing; no copying, relinking, file pruning, ELF execution, QEMU runs, device access or boot is authorized.

This source-only check does not reauthenticate R26 source provenance, 2,070-file SHA inventory content, historical path membership, transitive ELF/Lua dependency closure, or physical PW3 input/display. All holds remain `NOT_BOOTABLE`.

## User Mac result

The user ran the pinned R3727 standalone diagnostic against the local rootfs and reported `ABSENT_INTERP_SAME_BASENAME_ALTERNATIVES_CLASSIFIED_ONLY`. The **12** absent interpreter *segments* use **one distinct absent guest path literal and one basename**; each segment sees **one regular same-basename ELF-header-compatible candidate** at another stage location. No same-basename symlink candidates were recorded. Parent R3726 source SHA and its 83/19/9/10/1446 inventory plus 7/12 path counts were rechecked by the script. This removes duplicated search categories but does **not** make the absent guest path exist, establish runtime kernel selection, authenticate R26 source provenance, or authorize file modifications. See `USER-MAC-AUDIT-RESULT.json`. **NOT_BOOTABLE**.
