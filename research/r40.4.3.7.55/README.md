# R40.4.3.7.55 — Interpreter DT_RELCOUNT prefix and referenced symbol geometry (read-only)

**Research only; immutable `NOT_BOOTABLE`.** The original R13 staged rootfs remains unchanged; no guest interpreter alias, actual relocation, ELF/QEMU execution, firmware write, boot or pruning.

## Mac evidence

User R3754 returned `ALTERNATE_INTERPRETER_STATIC_SELF_RELOCATION_AND_DYNSYM_REVIEW_ONLY` on the alternate ET_DYN ARM loader candidate: 21 regular REL relocation-table occurrences and six PLT table occurrences, representing 27 unique file-backed writable targets. ARM relocation types: 17 `R_ARM_RELATIVE` (23) with symbol index zero, four `R_ARM_GLOB_DAT` (21), six `R_ARM_JUMP_SLOT` (22). Ten targets are inside GNU RELRO and 17 outside. Ten symbol-indexed occurrences reference nine distinct dynsym entries, classified one defined-or-special global function, three defined-or-special global objects and five defined-or-special weak functions. `DT_RELCOUNT` **presence** was reported, not its numeric value or prefix correctness. See `research/r40.4.3.7.54/USER-MAC-AUDIT-RESULT.json`.

## R3755 diagnostic

Source SHA256 `eb1c7ef30f1a9d9a532a009589bbf5877ec19ec57f9e3200055f3ea989d934eb` pins the unchanged R3754 script SHA256 `7db26e7e5d42fbfeacdb0fea01922b3184e583ae041bb61ed00bcbb8a597bf5f` and replays the complete prior audit/HOLD chain. This independent *read-only* program:

- Reads the **numeric DT_RELCOUNT value** and tests whether the advertised first DT_REL records are symbol-index-zero `R_ARM_RELATIVE` relocations, also counting trailing relative records.
- Classifies the initial 32-bit addend words at the 17 relative relocation sites by zero/nonzero, low bit and numeric containment in the candidate's own PT_LOAD segments (no B + A relocation calculation or execution).
- Differentiates referenced dynsym entries with ordinary nonreserved section indexes, SHN_ABS, SHN_COMMON or unsupported special section indexes. Counts symbol type/binding, visibility, size zero/nonzero, function value low bit and numeric load-segment containment where appropriate.
- Cross-tabulates relocation ARM type with GNU RELRO target geometry and symbol metadata. Unique referenced symbols and relocation-record occurrences are never conflated.
- Returns HOLD for changed SHA pins, invalid descriptors, duplicate records, out-of-bounds symbol indexes, unexpected undefined entries or drift from the 27/9 Mac baseline.

**No raw ELF bytes, private file paths, symbol names, symbol values, addresses, version strings or ELF code are emitted.** Static geometry is *not proof* of a functioning runtime loader, PLT lazy binding, weak-symbol lookup, kernel ABI/TLS, dynamic namespace, historical source provenance, safe recovery or boot.

## Verification and distribution

**47 new and 703 inherited synthetic tests: 750/750 passed**, including an end-to-end synthetic call-chain regression. Verified from clean ZIP extraction: 54 SHA256 manifest entries and ZIP integrity passed. Distribution ZIP: `pw3-r3755-interpreter-relcount-symbol-geometry-readonly.zip` (55 files, SHA256 `3fdf1c3085be5851c420fe13c31c635069063da90e35796652462c9ce62aa3de`). The source and tests are included in the **conversation ZIP**, not published as standalone GitHub code, so no R3755 GitHub Actions PASS is claimed. **The user's real Mac R3755 stage audit has not run.**

## macOS runbook — no git or gh

Download that ZIP into `~/Downloads`:

```sh
mkdir -p "$HOME/Downloads/pw3-r3755"
cd "$HOME/Downloads/pw3-r3755"
unzip -o "$HOME/Downloads/pw3-r3755-interpreter-relcount-symbol-geometry-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043755-INTERPRETER-RELCOUNT-AND-SYMBOL-GEOMETRY-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Report `dt_relcount_prefix_categories`, `relative_original_addend_geometry_categories`, `relocation_target_storage_by_arm_type`, `referenced_unique_dynsym_section_and_value_categories`, `referenced_symbol_section_by_relocation_type`, and milestone/result. On HOLD, send `hold_category` and do not bypass source pins or write to the stage.

Original R26 provenance, historical file hashes, missing guest PT_INTERP path, weak-symbol runtime behavior, ARM TLS, full dependencies, recovery and boot remain unverified. OpenSSH/SFTP/rsync are deferred to a separately validated future image. **NOT_BOOTABLE**.
