# R40.4.3.7.43.1 — overlap-aware additional weak export survey

**Research-only read-only diagnostic. NOT_BOOTABLE.** No physical Kindle,
firmware, staged-rootfs write, symlink, QEMU, ELF execution or boot.

## Preserved original R3743 HOLD

The user ran the original R3743 on Mac and received
`HOLD` / `SOURCE_PROVIDER_OVERLAP_HOLD`. The original script rejects any
file listed both among the **12 PT_INTERP-requesting binaries** and the
**six direct DT_NEEDED provider candidate files**. These groups are not
necessarily disjoint: a shared library can request an interpreter and
be a direct provider candidate for another file. This overlap is not itself
ELF corruption or runtime failure.

R3743.1 **does not change the original R3743 script**. It requires the exact
original source SHA256 `be4ec4c3557073ece8016fdf395a6142687a32876cd680cd0ff71559e13cc34a`.
It replays the original SHA-pinned R3742 and earlier source-chain baseline;
reproduces the original overlap hold by requiring at least one shared file;
counts the shared files; and scans only the other, regular stage files after
excluding the **union** of the source and provider files. A shared source/provider
file is never double counted or treated as an additional export candidate.
All candidate names and file paths remain in memory and never appear in output.

The target population remains the 35 weak undefined references without an
export-name candidate among the original six direct providers: 33 local-index
zero references and two unversioned weak references. The output distinguishes
additional staged ELF name candidates, exports in requesting objects, and
unsupported ELF parse refusals. **An export-name match is not runtime symbol
resolution, DT_NEEDED loader selection, ELF version matching, TLS compatibility,
or valid weak unresolved-relocation semantics.** The missing exact PT_INTERP
path, 2070 historical hashes, original R26 provenance, independent-image recovery
and boot remain unverified. OpenSSH/SFTP/rsync remain deferred until final-image
validation.

## No-git/no-gh Mac commands

Download `pw3-r3743-1-overlap-aware-weak-export-readonly.zip` into Downloads:

```sh
mkdir -p "$HOME/Downloads/pw3-r3743-1"
cd "$HOME/Downloads/pw3-r3743-1"
unzip -o "$HOME/Downloads/pw3-r3743-1-overlap-aware-weak-export-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043743-1-OVERLAP-AWARE-EXPORT-SURVEY-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

The original source and pinned parents are included as exact byte copies.
Do not modify them to force a result. Send output JSON, especially
`source_provider_overlap_regular_files`, `additional_name_candidate_categories`,
`additional_name_candidate_categories_by_target_group`, and
`additional_scan_counters`. If the audit returns a new `HOLD`, retain it.

**NOT_BOOTABLE.** No guest mapping applied; no runtime loader or symbol
resolution verified. No firmware, pruning or boot authorization.

## User Mac stage result — recorded

The user reported `OVERLAP_AWARE_ADDITIONAL_WEAK_EXPORT_NAME_REVIEW_ONLY` with four files overlapping the 12 missing-PT_INTERP requesters and six initial direct-provider candidates (14 unique excluded). All **69** additional ARM ELF dynamic files were parsed successfully from 1,432 other regular staged files. None exported a matching name for the **35** weak undefined references previously unmatched among the six providers: 33 local VERSYM-index-zero references and two unversioned weak entries, covering **five distinct symbol name literals** in memory. `NO_NAME_CANDIDATE_IN_PARSED_ADDITIONAL_FILES`: 35; no additional regular-file matches. The output preserves original R3743 `SOURCE_PROVIDER_OVERLAP_HOLD` without modifying source. This static name inventory does **not** prove the missing names are absent from an actual runtime namespace or that the dynamic linker accepts unresolved weak relocations. No rootfs write or alias; source provenance, kernel ABI, TLS, symbol semantics, historical hashes, boot and pruning remain held. See `USER-MAC-AUDIT-RESULT.json`. **NOT_BOOTABLE**.
