# R30 — offline failed lookup and openat dirfd syntax audit

**2026-11-01:** User has verified `R29_DEPENDENCY_EVIDENCE_TRIAGED` on R26–R28 private evidence (26 host tests PASS); 1,448 staged regular files, 341 with direct guest open evidence, 1,107 without open evidence (`UNKNOWN_HOLD`), 20 ELF DT_NEEDED candidate paths without open evidence (six from observed ELF objects), 475 unobserved Lua literal-source files, 646 unsuccessful stage-looking path attempts (595 unique), and seven successful `openat` calls whose directory-FD base is ambiguous.

**R30 user-side VERIFIED (2026-11-01):** 27 host tests PASS and real private trace audit verdict `R30_NEGATIVE_LOOKUPS_AND_DIRFD_SYNTAX_TRIAGED`. The user-supplied summary confirms 646 negative lookups and all seven ambiguous-successful openat calls have printed `AT_FDCWD` (see observations below). No FD-target or cwd lineage proven.

**R30 has now been executed successfully against the user's actual R27–R29 private files, with 27 host tests PASS.** This is not an OS build, syscall FD lineage proof, dependency-completeness claim or rootfs deletion gate.

## User-supplied R30 result

```text
Ran 27 tests ... OK
R30_NEGATIVE_LOOKUPS_AND_DIRFD_SYNTAX_TRIAGED; NO_PRUNING; NOT_BOOTABLE
```

Verified aggregate counters: **2,262** path attempts rechecked; **646** stage-lexical missing lookup attempts and **595** distinct missing-path strings; all 646 reported raw QEMU return value **-1**. Avoid interpreting the raw return as a specific errno without inspecting the exact guest syscall semantics. Filename-pattern classes:

| Heuristic class | Calls | Unique names |
|---|---:|---:|
| Lua-like | 439 | 427 |
| ELF SONAME/library-like | 111 | 99 |
| Font-like | 14 | 5 |
| Other/no extension | 82 | 64 |
| **Total** | **646** | **595** |

The **seven** ambiguous `openat` paths all had successful opens and all used **`AT_FDCWD`** as the first argument (rather than an unknown numeric directory FD). This **narrows** resolution to the process's current working directory; it does not establish a path without validating CWD provenance and any intervening guest `chdir`/`fchdir`. The R30 tool correctly reports `openat_dirfd_target_paths_resolved=false`. There is no evidence of a rootfs being created or any safe file deletion.

The R26 sentinel `7eb0d027b2b407fe6963ea9b9a1fe7fee1db96ae66f9399ece179238939176ed` and R27 raw trace SHA `d02193b9b800fdc59cd7b7bf6367c7e2835e0afcfe0e1663ff0f6faa7e6ef49a` match prior user evidence. Full trace and path tables stay private.

## Scope and source artifact

`pw3-os-r30-openat-and-negative-path-evidence.zip` — SHA-256 **`ba690edcfe6477489bbc01100559edbd5b83d75672008ce359a58916061e436c`**. The package contains Python stdlib-only `r30/audit.py`, `tests/test_audit.py`, `README-R30.md` and a payload `SHA256SUMS` manifest. Verified ZIP integrity, all three payload hashes and 27 host tests. It contains no R13 stage, private trace, stock Kindle firmware or proprietary application bytes. The archive is available as a conversation download; it is not a complete source-rootfs release.

R30 rechecks the **original, already saved R27 QEMU guest trace** SHA-256 and every R28 private path-event ordering against the trace, validates R28's checksum manifest and R29's safety/counter invariants, then emits aggregate counts only:

- For the 646 stage-looking lexical paths absent from R26 catalog, record negative return numbers (as raw QEMU values; do **not** guess their errno meaning) and filename-extension heuristic classes such as ELF `.so.N`, Lua, font, locale, image and configuration. Provide both call and distinct-name counts; these do **not** determine necessity or whether the lookup was optional.
- For the seven successful relative `openat` events, classify only the first argument **as text printed by QEMU**: `AT_FDCWD_token_only`, `numeric_dirfd_token_unresolved`, `other_or_unknown_dirfd_token`, or `unparsed_dirfd_token`. **Do not infer actual FD target, current working directory, or symlink resolution**. A future, separately verified trace including chdir/fchdir/open/dup/close lineage would be necessary for reliable context.
- Emit `R30-SUMMARY.json` (shareable aggregates, hashes and immutable hold flags) and `R30-AUDIT.PRIVATE.json` (no path list; keep local for consistency). Reject malformed/private-symlink evidence, mismatched stages/traces, counter forgeries, unexpected positive opens in the absent-catalog class, or output overwrites.
- **Never** execute stage binaries, access Kindle hardware, use a network, modify original evidence, touch stage files, create an Alpine rootfs or mark an unobserved file safe to remove.

## Exact offline Mac commands

```sh
cd ~/Downloads
unzip pw3-os-r30-openat-and-negative-path-evidence.zip
cd pw3-os-r30-openat-and-negative-path-evidence
python3 -m unittest discover -s tests -v

python3 r30/audit.py \
  --r27-trace "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-QEMU-GUEST-SYSCALLS.PRIVATE.log" \
  --r27-summary "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-SUMMARY.json" \
  --r28-private "$HOME/Downloads/pw3-os-r28-correlation-first-run/R28-CORRELATION.PRIVATE.json" \
  --r28-summary "$HOME/Downloads/pw3-os-r28-correlation-first-run/R28-SUMMARY.json" \
  --r28-hashes "$HOME/Downloads/pw3-os-r28-correlation-first-run/R28-SHA256SUMS" \
  --r29-summary "$HOME/Downloads/pw3-os-r29-triage-first-run/R29-SUMMARY.json" \
  --out "$HOME/Downloads/pw3-os-r30-lookup-audit-first-run"

cat "$HOME/Downloads/pw3-os-r30-lookup-audit-first-run/R30-SUMMARY.json"
```

Expected verdict (only if the user runs it successfully): `R30_NEGATIVE_LOOKUPS_AND_DIRFD_SYNTAX_TRIAGED`. If it fails, it emits only `R30_OFFLINE_EVIDENCE_FAIL` to avoid leaking raw paths. Preserve original input data and select a fresh output path for retries.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. No migration execution, independent OS boot, real EPDC, battery, charging, suspend, Wi-Fi or firmware interactions are proven.
