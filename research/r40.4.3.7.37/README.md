# R40.4.3.7.37 — ARM relocation numeric type / dynsym index preflight

**Research-only read-only stage audit. NOT_BOOTABLE. Local host synthetic tests: 15/15 PASS. User Mac rootfs run: not yet performed.**

R3736 user Mac output established the alternative loader's 21 REL, 6 PLT entries, and the 12 requesters' combined 2,924 REL, 575 PLT entries. All reported relocation targets were contained in PT_LOAD memory, but neither the numeric ARM type IDs nor dynamic symbol-index references were investigated. The one required guest interpreter path remains absent and the proposed future alias has not been applied.

The independently developed R3737 diagnostic SHA-256 pins the unchanged R3736 source `48189e67421d5aaebfa3dfdc1bfd64cd8b383c347d09a0fc58fa8bbdb38fb447`, then replays all original source baseline and hold categories. It reports aggregate **numeric ARM relocation type IDs**, nonzero/zero `r_info` symbol indices and the count of unique referenced dynamic symbols whose fixed 16-byte `Elf32_Sym` headers fall in file-backed PT_LOAD bytes. It aggregates defined/undefined and weak/nonweak indicators **without reading symbol names**.

The ARM ABI permits `R_ARM_RELATIVE` with zero or nonzero referenced symbol IDs; both are counted, not automatically rejected. Unknown relocation code IDs, missing `DT_SYMTAB`/`DT_SYMENT`, or unfetchable dynamic-symbol records receive explicit **review holds**. Even a bounded symbol record is not a resolved symbol or proof of runtime loader support. Official reference: https://github.com/ARM-software/abi-aa/blob/main/aaelf32/aaelf32.rst

The offline ZIP `pw3-r3737-arm-relocation-symbol-readonly.zip` has SHA-256 `7f9870d90727b29ddeb706d17564062eca04edb33856caa00afb090e21cbc238` and 11 members, including SHA-pinned parents, script, 15-test suite, instructions and checksum manifest. Source SHA256 `27ac20c24670424623ecc8f6bd52e80b6b5835935a403d62548c734b11104c77`; test SHA256 `0951f24a436becedda15015693af1492d5460e3503270d07d7cccf167bfa4bb5`. The actual code/test sources are in the conversation ZIP; this commit records release metadata and checksums but **does not claim publication of the Python sources, CI PASS, or Mac-stage success**.

## macOS commands without git or gh

Download the ZIP to `~/Downloads` and run:

```sh
mkdir -p "$HOME/Downloads/pw3-r3737"
cd "$HOME/Downloads/pw3-r3737"
unzip -o "$HOME/Downloads/pw3-r3737-arm-relocation-symbol-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r4043737.py' -v
python3 -B R4043737-ARM-RELOCATION-SYMBOL-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Read `candidate.category` and `requesting_elf_categories`. A top-level classification does not mean all ELF entries passed. If `HOLD` appears, send `hold_category` and do not loosen checks or change stage files.

No linker/ELF execution, QEMU, original R13 rootfs mutation, symlink creation, physical PW3 action, firmware write, boot or pruning. Original R26 provenance and historical path/hash reauthentication remain held. The separately recorded future-image OpenSSH/SFTP/rsync requirement is unchanged. **NOT_BOOTABLE**.
