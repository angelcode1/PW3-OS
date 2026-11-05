# R40.4.3.7.40 — Static symbol-name provider candidates and version-tag inventory

**Host-only research and education. `NOT_BOOTABLE`. No guest-path alias, staged-file writes, emulator, executable invocation, device access, firmware, boot or pruning.**

## Why this step is needed

User R3739 completed a basename/SONAME-only graph: 12 requesting ELFs, 19 direct dependencies and six unique regular provider candidates, each with a matching SONAME; seven provider DT_NEEDED edges had a candidate and there were zero cycles. That evidence does **not** show that the 632 relocation-referenced undefined dynamic-symbol entries can find a definition. Nor does it prove dynamic linker search rules, symbol versions, TLS, interposition or ABI compatibility.

## What this program actually does

- Requires an exact SHA256-pinned original R3739 Python source and replays R3739 (which pins R3738 and the earlier audited lineage) against the **unchanged** R13 stage. Fails closed if the expected 12-requester/19-edge/six-provider baseline changes.
- Re-identifies the six unique regular same-basename provider candidates without exporting filenames or strings.
- Reads bounded, file-backed ELF32 ARM `SHT_DYNSYM` and its linked `SHT_STRTAB`; verifies these agree with `DT_SYMTAB`, `DT_SYMENT`, `DT_STRTAB`, and `DT_STRSZ` inside `PT_DYNAMIC`.
- Reads the requesting ELF objects' REL/RELA/PLT relocation symbol indices and counts the **distinct relocation-referenced symbol entries per source ELF** that are undefined. Verifies the earlier observed **632 undefined / 145 defined-or-special** aggregate counts.
- Compares the *names only in memory* against exported global, weak or GNU-unique definitions in the six provider candidate files; outputs aggregate categories **no candidate**, **one name candidate**, **multiple candidates**. It never prints symbol names, strings, file paths or data.
- Counts only the **presence** of dynamic versioning tags (`DT_VERSYM`, `DT_VERNEED`, `DT_VERDEF`) and `DT_RPATH` / `DT_RUNPATH` in source/provider files. It does **not** inspect or validate version table payloads or search paths. Matching names **cannot** establish actual symbol resolution.

**Important strict limitation:** This audit intentionally requires file-backed ELF section headers (SHT_DYNSYM and linked SHT_STRTAB), rather than guessing dynamic symbol-table length. If a loader-safe stripped ELF lacks those sections, the program returns a named `HOLD` for follow-up; that is not evidence of a bad binary. A symbol with no name candidate among the *six* providers may still be satisfied elsewhere at runtime; no runtime search is implemented. Conversely, a same-name provider is not necessarily in the loader namespace or version-compatible. `NOT_BOOTABLE` regardless of counts.

The `PT_INTERP` guest path remains absent, the future relative mapping is not installed, and no files in the original rootfs are modified. Original R26 source provenance, historical hashes, Linux 3.0.35 kernel/runtime ABI, full transitive loader resolution, ARM TLS and recovery remain on hold. OpenSSH/SFTP/rsync installation remains deferred to a separately validated future image.

## Mac commands — no git or gh

Download `pw3-r3740-symbol-name-candidates-readonly.zip` to `~/Downloads`, then run:

```sh
mkdir -p "$HOME/Downloads/pw3-r3740"
cd "$HOME/Downloads/pw3-r3740"
unzip -o "$HOME/Downloads/pw3-r3740-symbol-name-candidates-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r4043740.py' -v
python3 -B -m unittest discover -s . -p 'test_r4043739.py' -v
python3 -B R4043740-SYMBOL-NAME-VERSION-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

The first suite should show **23 tests OK**, the pinned R3739 suite **18 tests OK**. These are synthetic host checks, **not** tests against the user Mac's rootfs. Send the new JSON fields `undefined_symbol_candidate_categories`, `distinct_referenced_undefined_symbol_names`, and `source_and_provider_dynamic_metadata_tag_counts`; if output is `HOLD`, send its `hold_category` and do not alter source pins, guest paths, or staged files to force success.

**`NOT_BOOTABLE`.**

## User Mac static candidate results

The user reported `STAGED_SYMBOL_NAME_CANDIDATES_AND_VERSION_TAGS_STATIC_ONLY`: **632** referenced undefined dynamic symbol entries representing **369 distinct name literals** across **12** requesting objects, matched by name against **six** staged regular-file provider candidates. Outcomes: **517** with one staged provider definition name candidate, **80** with multiple candidates and **35** with no candidate among these six providers. All twelve requesters have symbol-versioning metadata. Dynamic version tags: providers DT_VERDEF=6, DT_VERNEED=5, DT_VERSYM=6; sources DT_VERDEF=10, DT_VERNEED=12, DT_VERSYM=12, DT_RPATH=2. The version table contents were **not** parsed by R3740. Name-only matching cannot establish GNU version compatibility, search-path selection, symbol interposition, TLS, missing interpreter path resolution or runtime loader behavior. No staged modification, boot, firmware or pruning. See `USER-MAC-AUDIT-RESULT.json`. **NOT_BOOTABLE**.
