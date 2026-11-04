# R40.4.3.7.26 — independent read-only PT_INTERP guest-path/ELF-header audit

**Host-only, synthetic tests: 21/21 PASS. User Mac stage run: NOT YET EXECUTED.** Research and educational use only. **NOT_BOOTABLE**.

## Why this audit exists

The user supplied the corrected R3725 Mac output showing that the original **outer stage** has exactly 1,448 regular files, 287 directories, and 335 symlinks (2,070 total entries). The earlier 1,446-file count was of `stage-r13-fixed/rootfs` **alone**. This closes the *scope/count mismatch only*, not a historical hash or source-authentication gate.

R3724 had independently classified 19 PT_INTERP segments (9 strictly terminated pathname literals, 10 with only extra trailing NULs), but it did not inspect whether their guest interpreter pathnames resolved to staged ELF files. R3722.1 had suggested seven direct regular PT_INTERP candidates, two absent guest paths, and ten morphology holds. R3726 checks the guest path mapping independently, treating all 19 safely parsed literals as candidates. These are **not runtime loader results**.

## What R3726 actually checks

- Scans **only** the existing `rootfs` directory without following directory symlinks. Expects 1,446 regular files, 83 ELF objects and 19 PT_INTERP segments, split into 9 strict and 10 padding-only.
- Parses ELF32/ELF64 headers and bounded PT_INTERP segments; refuses unsupported/unsafe layouts.
- Models absolute guest paths relative to the supplied stage `rootfs` and follows symlink **literal targets in guest namespace**, with a 40-hop bound and rejection of guest-root traversal escape.
- Classifies the final target as absent, non-regular, non-ELF, ELF header incompatible, or **regular ELF header-compatible candidate** (matching EI_CLASS/EI_DATA/e_machine and ET_EXEC/ET_DYN).
- Prints fixed aggregate categories only; it does not export private paths, symlink strings, or file contents.

**Caveats:** Header compatibility is not loader ABI compatibility; interpreter file presence is not loader activation. This tool does not resolve real kernel binfmt behavior, library RPATH/RUNPATH, `DT_NEEDED` resolution, LD_LIBRARY_PATH, `dlopen`, Lua imports, dynamic tracing, source provenance, guest memory mapping, or physical Kindle I/O. No file hashes or source pins are reauthenticated by this standalone tool. All boot, flash, write and pruning holds remain. The `STATIC_INTERP_GUEST_PATH_CLASSIFICATION_ONLY` status means scan/baseline morphology completed, **not that all guest paths resolve**; read the `path_resolution_counts` breakdown.

## No Git or GitHub CLI needed on macOS

Download these files side by side into `~/Downloads/pw3-r3726` (or use the accompanying ZIP). The script and tests require only Python 3's standard library.

```sh
cd "$HOME/Downloads/pw3-r3726"
shasum -a 256 -c SHA256SUMS
python3 -m unittest discover -s . -p 'test_*.py' -v
python3 R4043726-INTERP-GUEST-RESOLVE-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --expected-rootfs-regular 1446
```

The output is a single JSON line. The proper completed audit result is `STATIC_INTERP_GUEST_PATH_CLASSIFICATION_ONLY`, which may include separate path-resolution holds. This is a source-only **candidate classification** under **NOT_BOOTABLE** regardless of the counts.

If this prints `HOLD_*` with exit code 2, retain the hold. Do not alter original stage files, modify symlinks, remove apparently unused libraries, execute a loader, boot, flash, or access the physical Kindle to force the result.
