# R40.4.3.7.51 — Static .plt word variation and relocation target coverage

**Host-only research. Immutable NOT_BOOTABLE.** Original R13 staged rootfs and all SHA-pinned source scripts remain unchanged.

## Mac evidence motivating this release

R3750 reported **nine distinct 32-, 48-, and 64-byte prefixes** across nine requesting ELF32 ARM objects, despite **one common 16-byte .plt+0 prefix**. Each of the three 16-byte suffix chunks was distinct across the nine objects. That does not establish code execution, pointer validity, or runtime lazy binding.

R3751 SHA256-pins R3750 source `3d7b3639802341773b6db699375ba32215219a40f0f9b8138073304b57eeff6e`, replays R3750 and inherited evidence, and reads exactly 64 file-backed bytes of each of nine .plt sections with the pinned no-follow reader. It classifies for each of 16 word positions: number of distinct full 32-bit words, distinct upper 20 bits, distinct lower 12 bits and whether observed variation is confined to lower 12 bits. **This is an arithmetic bit split, not decoded ARM instructions or proven immediate fields.** ELF byte order is respected.

The same diagnostic boundedly reads DT_REL, DT_RELA and DT_JMPREL tables and counts **dynamic relocation target offsets that fall within the first 64 bytes of .plt**, including ARM relocation type numbers and misaligned/boundary-crossing targets. A lack of runtime relocation targets would **not** exclude link-time transformations or other adjustments. It never applies relocations, emulates ARM, resolves symbols, creates aliases, changes files, boots or prunes.

Only aggregate numbers and per-word category labels are printed; **no raw bytes, addresses, file paths, symbol names, version names or private hashes** are exported.

## Host verification

The conversation ZIP `pw3-r3751-plt-word-variation-readonly.zip` has **47 files**, with a 46-entry SHA256SUMS manifest. ZIP SHA256: `329deea48d8ce048adabe9270d5ad13bdc9d519ddc2b95b288d6248c0fc7c7d2`. Clean extraction passed checksum verification, ZIP integrity and **556/556 synthetic tests** (54 new + 502 inherited). The full tool, tests, unchanged pinned predecessors and workflow example are bundled in the ZIP. Standalone runnable source is **not** in this GitHub directory and **no R3751 GitHub Actions pass** is claimed.

## macOS runbook (no git or gh)

Download `pw3-r3751-plt-word-variation-readonly.zip` to Downloads:

```sh
mkdir -p "$HOME/Downloads/pw3-r3751"
cd "$HOME/Downloads/pw3-r3751"
unzip -o "$HOME/Downloads/pw3-r3751-plt-word-variation-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043751-PLT-WORD-VARIATION-RELOCATION-COVERAGE-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send the JSON, especially `word_variation_categories_by_position`, `word_variation_summary_categories`, `earliest_varying_word_index`, `first64_dynamic_relocation_target_sites`, `first64_dynamic_relocation_tables`, and `first64_dynamic_relocation_arm_types`. If HOLD, preserve the category. 

Original R26 source provenance, historic inventory hashes, absent guest PT_INTERP path, ARM TLS, full library namespace, kernel ABI, runtime loader behavior, recovery and boot remain unresolved. **NOT_BOOTABLE**.
