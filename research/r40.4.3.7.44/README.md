# R40.4.3.7.44 — weak ARM relocation-slot geometry and NOW/RELRO policy (read-only)

**Research and educational purposes only. Original PW3 R13 stage untouched. NOT_BOOTABLE.**

## Why the next static audit is needed

R3743.1 Mac output showed a 12-requester/six-provider inventory with four regular ELF files in both groups; all 69 other ARM dynamic ELF files parsed, with no further export-name candidates for 35 weak undefined relocation-referenced entries (33 local VERSYM=0 plus two unversioned weak references), representing five distinct symbol name literals. Neither this exhaustive **static subset** nor absence of names proves runtime loader namespace or weak-symbol binding behavior.

Earlier R3742 found **42** local-index-zero weak references used at **58** relocation sites (42 `R_ARM_GLOB_DAT`, 16 `R_ARM_JUMP_SLOT`) plus **two** extra unversioned weak references at **four** sites (two of each type), i.e. **62** targeted relocation sites. Nine of the local-index-zero weak entries have a direct staged provider *name* candidate and 33 do not. This audit checks the original relocation slot memory mapping, not the symbol value chosen at runtime.

## What this new tool does

- SHA-256 pins the **unchanged** R3743.1 script and inherits the original R3743 overlap HOLD, R3742 weak-relocation counts, R3741 local-index HOLD, and earlier stage baselines.
- Requires the same R3743.1 Mac evidence: four overlapping ELF group members, 69/69 extra dynamic ELFs parsed, 35 references with no extra staged match, five distinct names.
- Re-identifies exactly **44 weak referenced symbol entries** in three static groups: nine local VERSYM=0 with direct-provider name match, 33 local VERSYM=0 without such a match, and two unversioned without one.
- Reads ELF32 ARM program headers and bounded, file-backed `DT_REL`, `DT_RELA`, `DT_JMPREL` records. For the **62** targeted relocation sites, counts `r_offset` alignment, 32-bit word inclusion in a writable or nonwritable `PT_LOAD`, file-backed original word **zero/nonzero**, or zero-initialized `PT_LOAD` BSS; records GNU RELRO membership and unusual target-location categories separately.
- Counts source ELF objects advertising `DT_BIND_NOW`, `DF_BIND_NOW`, or `DF_1_NOW`, and source ELF objects containing `PT_GNU_RELRO`. These are *file metadata*, never proof of runtime linker policy.
- Exports only numbers and categories, no symbol names, file paths, guest paths, raw addresses, bytes, relocation values or version strings. The script never applies a weak zero substitution, relocation, symlink or loader lookup.

**Interpretation:** A weak undefined reference may be permitted to remain unsatisfied by an applicable ABI, but these stored relocation slots and version markers are **not** equivalent to a verified Linux 3.0.35 interpreter, Alpine dynamic-loader symbol lookup, binding-policy implementation, TLS, lib dependencies, kernel compatibility, recovery or boot. The staged guest interpreter path remains missing; future mapping is a lexical proposal only. The original R26 source provenance and historical inventory hashes remain unverified. OpenSSH, SFTP and rsync are planned only for a future independently validated image. **NOT_BOOTABLE**.

Authoritative background: [Arm ELF32 ABI, dynamic relocation types 21 and 22](https://github.com/ARM-software/abi-aa/blob/main/aaelf32/aaelf32.rst). Runtime implementation specifics have not been tested.

## Local synthetic verification

Expected **218** synthetic unit tests: **37** new R3744 tests plus **181** inherited unchanged predecessor tests. All tests use synthetic temporary input files, never the R13 rootfs. The packaged checksum manifest is verified before running against the real Mac stage.

## macOS runbook — no `git` or `gh`

Download `pw3-r3744-weak-slot-preflight-readonly.zip` into `~/Downloads`, then paste:

```bash
mkdir -p "$HOME/Downloads/pw3-r3744"
cd "$HOME/Downloads/pw3-r3744"
unzip -o "$HOME/Downloads/pw3-r3744-weak-slot-preflight-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043744-WEAK-RELOCATION-SLOT-PREFLIGHT-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Report `weak_reference_symbol_group_counts`, `weak_relocation_slot_categories_by_group`, `requester_now_policy_objects`, `requester_gnu_relro_objects`, and the milestone/result. If `HOLD`, send its category and do not change parent source checksums or R13 stage files. Even a static classification pass leaves the whole project **NOT_BOOTABLE**.
## User Mac static relocation-slot result

The user reported `WEAK_RELOCATION_SLOT_STORAGE_STATIC_ONLY` after replay of SHA-pinned R3743.1 and earlier source baselines. All **62 weak-targeted relocation sites** are writable and outside GNU RELRO: **44 `R_ARM_GLOB_DAT` REL sites contain zero original 32-bit words**, whereas **18 `R_ARM_JUMP_SLOT` PLT sites have nonzero original words**. By group, local VERSYM-index-zero nine name-candidate symbols contribute 18 sites (9 zero REL, 9 nonzero PLT); the 33 absent-name local-index symbols contribute 40 sites (33 zero REL, 7 nonzero PLT); and two unversioned absent-name weak symbols contribute four sites (two zero REL, two nonzero PLT). Twelve requesters have PT_GNU_RELRO, zero have NOW policy. These are static slot contents only, **not** runtime weak-symbol, GNU version, PLT resolver, interposition or guest interpreter behavior. Original R13 stage unmodified and previous R3741/R3743 holds preserved. See `USER-MAC-AUDIT-RESULT.json`. All source-provenance, historical hash, loader, ARM TLS, recovery, boot and pruning gates remain held. **NOT_BOOTABLE**.
