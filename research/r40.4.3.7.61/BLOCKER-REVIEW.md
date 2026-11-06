# R40.4.3.7.61 — Post-R3760 evidence boundary and next-gate review

**Research and educational use only.** This is a documentation review of source-backed results, **not** a new host or Mac-stage test. The original R13 stage remains unchanged. **NOT_BOOTABLE**. No guest path mapping, firmware writes, pruning, QEMU/guest ELF execution or boot is authorized.

## Positive static evidence (user-supplied Mac reports)

| Evidence | Result | Scope/limitation |
| --- | --- | --- |
| R3758 | All 2,070 R26 inventory records match current stage: 1,448 regular-file hashes, 335 symlink literals, 287 directories, 2,070 modes | Consistency with historical private inventory, not authenticated image origin |
| R3759 | R13 manifest located and its own bytes matched R26; no recognized source, signing, attestation or per-file hash collection | Manifest is **not an independent provenance anchor** |
| R3760 | Recovered original R26 tooling ZIP SHA matches PW3-OS documented release checkpoint; 5 file members intact, all 4 embedded SHA256SUMS records match | Repository-documented checksum, **not independently signed upstream provenance**. Initial missing-archive HOLD preserved; rerun pass separately recorded |
| R3753–R3757 | Alternate ET_DYN interpreter header matches all 12 requesters' EABI 5 and soft-float flags; entry in executable load segment; 27 static relocations; valid 17-entry DT_RELCOUNT prefix; nine self-referenced defined symbols with GNU version metadata; jointly present ARM file attributes equal | No loader execution or self-relocation, ARM TLS semantics, PLT/weak runtime lookup or kernel ABI confirmed |
| R3733–R3734 | One missing PT_INTERP guest pathname, one alternate same-basename ELF at a separate path; purely lexical relative mapping simulation reaches candidate | **Mapping was never applied or authorized**; still one missing PT_INTERP path in the existing stage |
| R3745 original | UNEXPECTED_STATIC_PARSER_HOLD preserved historically | Separate fixed pinned audit does not erase original result |

## Open blockers and their evidence requirements

| Priority | Unresolved question | What could resolve it | Current authorization |
| --- | --- | --- | --- |
| High | Independent R13 original image/source provenance | Authenticated upstream release, signed manifest with verified external trust root, or reproducible build trace tied to independently trusted source | No source anchor provided; do not infer authenticity from R26 internal hashes or GitHub docs |
| High | Requested PT_INTERP guest pathname remains absent | For a **separately built new image only**, design a loader placement strategy and validate its namespace independently; no edits to historical R13 stage | Not authorized to apply a mapping |
| High | Actual loader startup, relocation and symbol/version/weak lookup | Isolated, explicitly authorized future-image runtime trial with preserved logs and source hashes; static candidates are insufficient | Not authorized to execute guest code under present hold |
| High | ARM TLS and kernel ABI compatibility, including historical Linux 3.0.35 behavior | Versioned kernel features and appropriately controlled runtime validation | Not verified |
| High | Full dependency, runtime file, and recovery closure | Multi-scenario runtime observations, source/component licensing verification, future-image recovery and rollback exercises | Not verified; no pruning or boot permitted |

## Decision

1. **Do not generate a new numerical PLT/ELF-prefix audit to stand in for runtime proof.** The existing analyses have exhausted several static structural checks but cannot prove loading.
2. **Do not regenerate the R26 ZIP or overwrite its historical HOLD.** The R3760 follow-up confirmed the exact historical archive's consistency with the repository record; upstream origin remains unknown.
3. **Do not repeat R3734 mapping simulation.** Its lexical feasibility is already documented; it did not create or validate a functioning guest interpreter.
4. The next materially useful evidence must be **independent upstream provenance** or a **separately authorized isolated future-image test plan**, subject to explicit safety gates. Neither is supplied by the current R3760 audit.

## Source records

- `research/r40.4.3.7.60/USER-MAC-AUDIT-RERUN-RESULT.json` — successful R26 archive rerun.
- `research/r40.4.3.7.60/USER-MAC-AUDIT-RESULT.json` — historical missing-archive HOLD.
- `research/r40.4.3.7.58/USER-MAC-AUDIT-RESULT.json` — historical stage entry and hash agreement.
- `research/r40.4.3.7.59/USER-MAC-AUDIT-RESULT.json` — original R13 manifest categories.
- `research/r40.4.3.7.34/USER-MAC-AUDIT-RESULT.json` — earlier in-memory future mapping simulation.
- `research/r40.4.3.7.53/USER-MAC-AUDIT-RESULT.json` through R3757 — candidate interpreter ABI and static metadata.

No new source ZIP or CI success is claimed for this document-only review. All original and current immutable HOLDs remain preserved. **NOT_BOOTABLE.**
