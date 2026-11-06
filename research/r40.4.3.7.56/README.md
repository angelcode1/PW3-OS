# R40.4.3.7.56 — alternative ARM loader GNU version-definition preflight

**Research and educational purposes only. `NOT_BOOTABLE`.** This program performs read-only static inspection of the unchanged R13 staged rootfs. It must not run ARM ELF code, modify a guest loader mapping, apply a relocation, create a symlink, install a package, access the physical Kindle, flash, boot or prune.

## Why this test matters

The user-reported R3755 Mac audit verified that the alternative ET_DYN ARM interpreter candidate has 27 relocation sites: a valid `DT_RELCOUNT=17` prefix of `R_ARM_RELATIVE`, four `R_ARM_GLOB_DAT` and six `R_ARM_JUMP_SLOT` sites. All 17 RELATIVE addend words numerically fell in the candidate's own load segments; the ten symbol-based relocation occurrences reference nine *ordinary-section-defined* dynamic symbols, including five weak functions, four global bindings, and no undefined referenced symbols. This remains a **static inventory only**; actual self-relocation or weak binding has not been demonstrated.

The earlier candidate metadata showed `DT_VERSYM`, `DT_VERDEF`, SysV/GNU hashes and `DT_SONAME`, with no `DT_VERNEED` or direct `DT_NEEDED`. R3756 checks the integrity and relationships of those metadata structures, rather than performing more speculative PLT instruction-bit arithmetic.

## R3756 scope and holds

The new Python audit pins the **unchanged R3755 script by SHA-256** (`eb1c7ef30f1a9d9a532a009589bbf5877ec19ec57f9e3200055f3ea989d934eb`), replays its verified 17/27/9-symbol stage baseline and all inherited SHA-pinned historical holds including the original R3745 `UNEXPECTED_STATIC_PARSER_HOLD`. It inspects only the same unique same-basename, regular-file ELF32 ARM alternative candidate:

- Checks `DT_SONAME` as a bounded string and reports whether it equals the candidate's filename. It does **not** report either string or claim the absent requested guest path exists.
- Parses bounded `DT_VERDEF` and `DT_VERDEFNUM` entries, version indexes and their `Verdaux` chains, validating SysV ELF name hashes and string-table bounds. Reports **aggregate counts** of definition flags and records. The absence of `DT_VERNEED` and zero `DT_NEEDED` are preserved baselines.
- For the nine self-relocation-referenced, ordinary-section-defined dynamic symbols, reads their bounded `DT_VERSYM` entries. Classifies local/global/mapped-version index, hidden-bit flag and string-name emptiness. A version index requiring a missing `VERDEF` record produces a fail-closed `HOLD`.
- Reports only aggregate category counts and booleans. **No stage paths, candidate filename, SONAME literal, symbol name, GNU version string, raw ELF flags, addresses, numeric values, raw bytes or private hashes are exported.** The program never executes a guest ELF or attempts an actual lookup.

`DT_SONAME` equivalence and well-formed `VERDEF`/`VERSYM` only establish static metadata consistency. They **do not** establish symbol-version lookup semantics, binary portability, operational dynamic loader behavior, self-relocation, weak symbol semantics, ARM TLS runtime compatibility, transitive dependency closure or boot readiness. The guest PT_INTERP path still does not exist. Original R26 provenance, historical file hashes, kernel ABI, recovery and firmware gates remain held.

## Synthetic checks

The package contains **54 new R3756 synthetic tests + 750 inherited regression tests = 804 tests**, all passing on the host. Tests use synthetic temporary ELF fixtures and do not read the real staged rootfs. The ZIP also carries the unchanged SHA-pinned predecessor scripts, a file-by-file `SHA256SUMS` manifest and an optional GitHub Actions sample. A host synthetic PASS is not a real stage audit.

## Mac runbook (no git or gh)

Download `pw3-r3756-interpreter-gnu-version-selfsymbols-readonly.zip` into `~/Downloads`:

```sh
mkdir -p "$HOME/Downloads/pw3-r3756"
cd "$HOME/Downloads/pw3-r3756"
unzip -o "$HOME/Downloads/pw3-r3756-interpreter-gnu-version-selfsymbols-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043756-INTERPRETER-SELF-GNU-VERSION-METADATA-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send the JSON, especially `candidate_soname_basename_relation`, `candidate_verdef_record_categories`, `self_relocated_symbol_versym_categories`, `self_relocated_symbol_name_categories` and `result`. If it returns `HOLD`, send `hold_category` without altering any stage file or source pin.

**`NOT_BOOTABLE` is immutable. No alias, stage modifications, firmware write, boot or pruning is authorized.**