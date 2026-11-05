# R40.4.3.7.41.1 — GNU local-index review, read-only

**Research and education only. NOT_BOOTABLE. No changes to R13 rootfs or any ELF.**

## Why R3741 stopped

On the Mac stage, the unchanged R3741 executable returned `HOLD` and
`UNDEFINED_LOCAL_VERSION_HOLD`. It rejects a relocation-referenced undefined
`.dynsym` record when the corresponding GNU `.gnu.version` entry has index
**0 (`VER_NDX_LOCAL`)**. The **index-0 marker is not the same as unversioned/global
index 1**, and it is not evidence of a valid runtime resolution. GNU binutils
and ELF linker implementations distinguish these reserved values.

The original R3741 source (`d598134e...e69`) and its HOLD result are preserved
unchanged. Do **not** modify the original script or original stage to force a
pass. R3741.1 is a separate, SHA-pinned diagnostic that:

1. Checks the exact, unmodified original R3741 script SHA-256 and inherits all
   R3740→R3726 SHA-pinned source checks.
2. Replays the 12-requester / six-provider / 632 undefined referenced entries
   / 369 distinct names / 517+80+35 name-only candidate baseline.
3. Reuses the original bounded ELF GNU VERSYM, VERNEED and VERDEF parsers.
4. Classifies every referenced undefined symbol with VERSYM index **zero** as an
   **unresolved local-version-index review**, with aggregate binding type,
   symbol type and hidden-bit counts, while classifying other symbols' GNU
   version-name candidates as in R3741.
5. Requires that at least one local-index review reproduces the original Mac
   HOLD, instead of silently making the input pass as an ordinary audit.

The output includes **only numerical counts and category names**, no ELF
paths, version labels, symbol names, DT_NEEDED literals or stage contents.

**Interpretation:** The category `GNU_VERSION_LOCAL_INDEX_REVIEW_STATIC_ONLY`
means successful *counting*, **not successful symbol version resolution**.
Index-0 records remain unresolved pending further investigation into their
bindings, relocation semantics and the dynamic loader's handling. Other
name/version candidate matches are still not runtime loader resolution,
interposition, TLS validation or complete dependency closure.

This audit never runs an ELF, creates a guest alias, executes QEMU, copies a
loader, writes firmware, boots a Kindle, installs packages or prunes files.
The single missing PT_INTERP guest pathname remains absent, and OpenSSH,
SFTP and rsync are deferred until independent-image validation. Original R26
provenance, 2070 historic file hashes, kernel ABI and recovery are still held.

## Mac commands (no git/gh)

Download `pw3-r3741-1-gnu-local-index-review-readonly.zip` to `~/Downloads`,
then run:

```sh
mkdir -p "$HOME/Downloads/pw3-r3741-1"
cd "$HOME/Downloads/pw3-r3741-1"
unzip -o "$HOME/Downloads/pw3-r3741-1-gnu-local-index-review-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r4043741_1.py' -v
python3 -B -m unittest discover -s . -p 'test_r4043741.py' -v
python3 -B -m unittest discover -s . -p 'test_r4043740.py' -v
python3 -B -m unittest discover -s . -p 'test_r4043739.py' -v
python3 -B R4043741-1-LOCAL-VERSION-REVIEW-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Share the resulting JSON (`local_version_index_review`,
`source_symbol_version_requirement_categories` and
`version_filtered_static_candidate_categories`) or only `hold_category` if
another HOLD is found. **Never change stage files, checksum pins or original
Python scripts to force a classification. NOT_BOOTABLE.**

## Reference

- GNU ELF version-index semantics: https://gnu.googlesource.com/binutils-gdb/+/1730ec6b1848f0f32154277f788fb29f88d8475b/include/elf/common.h
- LLVM LLD ELF version parsing: https://fuchsia.googlesource.com/third_party/llvm-project/+/c61ea75c026b80da141fcfec024faf896fd5c05a/lld/ELF/InputFiles.cpp
- Original R3741 historical HOLD: `../r40.4.3.7.41/USER-MAC-AUDIT-RESULT.json`

## User Mac corrected audit result

R3741.1 returned `GNU_VERSION_LOCAL_INDEX_REVIEW_STATIC_ONLY` on the unchanged Mac stage: 632 relocation-referenced undefined dynsym entries across 12 requesting ELFs, representing 369 distinct names. There are **588 explicit version requirements**, **42 VERSYM-index-zero local-version references**, and **two global/unversioned references**. All 42 index-zero entries are `STB_WEAK`, numeric symbol type 0 (`STT_NOTYPE`), nonempty named, with no hidden bit. They remain **unresolved review**, never a version match. For the remaining entries, static candidates are 508 one GNU version-name match, 80 multiple name matches, 2 no staged provider name match. The tool saw four distinct version requirement names. GNU version-name equality is not runtime resolution; ELF search order, weak and TLS relocation semantics, original R26 provenance, historical hashes, interpreter pathname, image boot and pruning remain unverified. The original R3741 HOLD remains unchanged. See `USER-MAC-AUDIT-RESULT.json`. **NOT_BOOTABLE**.
