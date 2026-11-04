# R40.4.3.7.24 — standalone PT_INTERP padding diagnostic

**Source-only host diagnostic; no Mac stage run recorded. NOT_BOOTABLE.**

R4043723 reported 19 PT_INTERP segments: nine strict literals and ten trailing-NUL-padding holds (five from the observed ELF set and five from unobserved ELF files). This tool independently reads regular staged files and classifies valid PT_INTERP literals into strict or padding-only candidates; it emits counts only, never stage paths or interpreter contents. In particular, a padding-only candidate is **not** proof that the runtime loader exists or can load the file.

Run host tests:

```sh
python3 -m unittest discover -s research/r40.4.3.7.24 -p 'test_*.py' -v
```

Optional user-side read-only diagnostic, only against the previously verified stage root:

```sh
python3 research/r40.4.3.7.24/R4043724-INTERP-PADDING-READONLY.py --stage-root /path/to/existing/stage/rootfs
```

Do not copy the placeholder path literally. This is a **standalone check, not a replacement for the original source-pinned R3723 audit**. It does not verify the original R26 2070-entry source provenance, the original 492 observed-file replay, the historical trace, the 5/5 observed split, staged interpreter path existence, aliases, interpreter ABI, dependency closure, or device behavior. It does not run the loader, QEMU or binaries, write to the stage, boot, flash, or prune. A passing aggregate match does not resolve these holds. No private filenames or raw interpreter values appear in output. **NOT_BOOTABLE.**
