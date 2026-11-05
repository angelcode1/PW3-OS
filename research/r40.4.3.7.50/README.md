# R40.4.3.7.50 — Extended `.plt+0` 64-byte cohort (read-only)

**Research and educational purposes only. Immutable `NOT_BOOTABLE`.** No original R13 rootfs writes, guest mappings, symlinks, ELF/QEMU execution, relocation application, firmware modification, boot, or pruning.

## Why

The user-supplied R3749 Mac result found **18** weak PLT sites across **nine** requesting ARM ELF32 objects whose original slot words were numerically equal to `.plt+0`. All nine `.plt` entries had identical file-backed first 12 **and** first 16 bytes and a common coarse four-word A32 encoding-field sequence. The original slot words are **not proven runtime pointers**, and their bytes are **not proven valid instructions or a working dynamic linker**.

R3750 replays the **exact SHA256-pinned R3749 source** `d92242d77558c8eb075e18c0fe2d3d6670a930e82414ad238b311f499e86308b` and all older source pins, including historical R3745 failure HOLD. It requires the same 12-requester, six-provider, 18-site, nine-affected-object and identical 16-byte prefix baseline. Against the unchanged original R13 rootfs, it privately reads the first 64 bytes of each of the nine unique executable, file-backed `.plt` sections and reports only:

- **Distinct counts** for first-16, first-32, first-48, first-64 byte windows and four independent 16-byte chunks; counts of requesters sharing entire 64-byte prefixes.
- Coarse ARM A32 **encoding-field** categories for words 4–15 (condition, top-level format and one coarse subfield); not full instruction decoding or disassembly.
- Bounds/unique executable-file-backing checks, preserving an explicit HOLD for any changed, truncated, ambiguous or unexpected stage evidence.

Only aggregate numeric counts and stable category labels leave the process: **no original ELF bytes, fingerprints, guest paths, symbol names, version names, file basenames, raw addresses, instruction words or tracebacks**. An identical 64-byte prefix would strengthen a common linker-template hypothesis, **not validate runtime PLT resolution**, weak-symbol semantics or Linux 3.0.35 compatibility. Differences in later chunks would simply show that the first-16 cohort does not extend that far.

## Host tests and provenance

- **58 new synthetic tests** plus **444 inherited synthetic tests**: **502/502 PASS**, including pinned source checks and synthetic malformed ELF fixtures. All host tests operate on temporary mock ELFs, never the real stage.
- Full manifest and ZIP integrity are checked after packaging; all unchanged predecessor sources and tests are bundled.
- Mac-stage R3750 audit is **not yet run**. GitHub Actions status is **not verified**.

## Run on macOS without git or gh

Download `pw3-r3750-plt-extended-cohort-readonly.zip` into `~/Downloads`. Then:

```sh
mkdir -p "$HOME/Downloads/pw3-r3750"
cd "$HOME/Downloads/pw3-r3750"
unzip -o "$HOME/Downloads/pw3-r3750-plt-extended-cohort-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043750-PLT-EXTENDED-PREFIX-COHORT-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send the JSON values for `cohort_distinct_prefix_window_counts`, `cohort_distinct_16_byte_chunk_counts`, `objects_sharing_first_64_bytes_with_another`, and `suffix_a32_encoding_field_categories_by_position`. For a HOLD, send the `hold_category` unchanged, **not** a modified script or stage.

**Still blocked:** absent guest PT_INTERP pathname; unapplied future mapping; original R26 provenance and historical inventory hashes; real dynamic-linker search/weak resolution/interposition; ARM TLS, Linux/kernel ABI and recovery; all firmware, pruning and boot operations. OpenSSH, SFTP and rsync are deferred to a separately validated image. `NOT_BOOTABLE`.