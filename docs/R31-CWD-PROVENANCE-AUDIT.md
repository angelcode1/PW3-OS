# R31 — conditional launch-CWD provenance audit, not guest-CWD proof

**2026-11-01:** R30 user-side PASS, and **R31 user-side PASS** (`R31_CWD_CONDITIONAL_CANDIDATES_AUDITED`; 21 host regression tests PASS). The seven successful `AT_FDCWD` open calls yielded seven conditional staged-directory candidates. No real CWD lineage, symlink resolution, dependency closure, rootfs creation or pruning was proven.

## R31 verified local result — user-supplied 2026-11-01

The user ran 21 host tests (`Ran 21 tests ... OK`) and the offline `r31/audit_cwd.py` program against original R26–R30 private evidence. Verdict `R31_CWD_CONDITIONAL_CANDIDATES_AUDITED`.

| User-supplied metric | Value |
|---|---:|
| Successful ambiguous `AT_FDCWD` calls examined | 7 |
| Conditional `stage_catalog_dir` candidates | 7 |
| Captured successful guest CWD-change syscalls | 0 |
| Unparsed CWD-change events | 0 |
| Original path attempts rechecked | 2,262 |
| Pinned published runner source hash matched | yes |
| R30 summary independently recomputed and matched | yes |

The original runner's pinned SHA-256 is `0614ac65cb2a2786eb5a8b11b536fe5aa320aace49f03c7c65f3c07eba227ca0`; R26 stage sentinel and R27 raw trace hashes match previous supplied evidence. **All seven are staged-directory lexical candidates, not proof that a directory FD was opened or the target path resolved.** The reviewer says `conditional_mapping_only_not_fd_target_proof=true`, `runner_executed_identity_proven=false`, `guest_cwd_lineage_complete_proven=false`, `symlink_resolution_proven=false`, `dependency_closure_proven=false`, `safe_to_delete_inferred=false`, `new_rootfs_created=false`, and `immutable_hold=NOT_BOOTABLE`.

Next: [R32 Ink Away project persistence probe](R32-INKAWAY-PERSISTENCE.md), a separate ARM/QEMU workload designed to exercise more real application paths; it does not change the original R31 inference or authorizations.

## Motivation and limits

The exact R27 runner released in `pw3-os-r27-dynamic-file-trace.zip` declares `APP="$ROOT/opt/koreader-compat/app"`, changes directory via `cd "$APP"`, and then runs QEMU with `QEMU_STRACE=1`. Published source SHA-256 for this script is `0614ac65cb2a2786eb5a8b11b536fe5aa320aace49f03c7c65f3c07eba227ca0`. The Linux `AT_FDCWD` sentinel refers to the calling process's current working directory instead of a numeric directory FD.

R31 verifies a locally supplied R27 runner against that byte-for-byte SHA-256 and checksum manifest, replays the R30 full raw-trace/observation checks, validates R26's catalog and stage sentinel against R27–R30, then scans all captured syscalls for `chdir` and `fchdir` returns. Only when there is **no captured successful or unparseable guest CWD-changing syscall** does it emit **conditional lexical candidate** paths based on the runner's declared pre-QEMU `cd`. If any such CWD-changing call is seen, all seven paths remain `held_due_cwd_mutation_or_unknown` and are not matched to the stage.

This **cannot** prove the exact original runner was executed, that QEMU guest tracing captured all CWD operations, actual guest process CWD lineage, symlink resolution, runtime loader resolution or the complete dependency set. Even zero visible guest `chdir` calls does not establish there were none. All `UNKNOWN_HOLD` files stay on hold; no deletions or rootfs construction.

The new deliverable: `pw3-os-r31-cwd-provenance-audit.zip`, SHA-256 **`f99a38d9b8b10179f00a340aea62836a95e5683ae2b2a569e96720dc95c0ef89`**, ZIP integrity and all five payload SHA-256 entries verified. 21 host-only regression tests PASS, including forged runner/manifest, reordered events, altered trace, inconsistent R30 counters, duplicate catalog entries, unsafe guest paths, output overlaps, and presence/absence of guest CWD-change events. Package includes a pinned copy of the **R30 reference audit parser** for independent consistency checks. The package does not include any proprietary binaries or private traces.

## User-side Mac command — no Docker, no stage execution

```sh
cd ~/Downloads
unzip pw3-os-r31-cwd-provenance-audit.zip
cd pw3-os-r31-cwd-provenance-audit
python3 -m unittest discover -s tests -p 'test*.py' -v

python3 r31/audit_cwd.py \
  --r26-inventory "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-INVENTORY.json" \
  --r26-summary "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-SUMMARY.json" \
  --r27-trace "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-QEMU-GUEST-SYSCALLS.PRIVATE.log" \
  --r27-summary "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-SUMMARY.json" \
  --r27-runner "$HOME/Downloads/pw3-os-r27-dynamic-file-trace/run-r27-docker.sh" \
  --r27-runner-hashes "$HOME/Downloads/pw3-os-r27-dynamic-file-trace/SHA256SUMS" \
  --r28-private "$HOME/Downloads/pw3-os-r28-correlation-first-run/R28-CORRELATION.PRIVATE.json" \
  --r28-summary "$HOME/Downloads/pw3-os-r28-correlation-first-run/R28-SUMMARY.json" \
  --r28-hashes "$HOME/Downloads/pw3-os-r28-correlation-first-run/R28-SHA256SUMS" \
  --r29-summary "$HOME/Downloads/pw3-os-r29-triage-first-run/R29-SUMMARY.json" \
  --r30-summary "$HOME/Downloads/pw3-os-r30-lookup-audit-first-run/R30-SUMMARY.json" \
  --out "$HOME/Downloads/pw3-os-r31-cwd-audit-first-run"

cat "$HOME/Downloads/pw3-os-r31-cwd-audit-first-run/R31-SUMMARY.json"
```

Expected verdict **only after user execution**: `R31_CWD_CONDITIONAL_CANDIDATES_AUDITED`. Share **only** `R31-SUMMARY.json`; `R31-CWD-CANDIDATES.PRIVATE.json` contains path strings and remains local. The tool never executes binaries, runs Docker, reads the staged filesystem, accesses any device/network, or writes inside prior evidence directories. It rejects existing output paths.

## Upcoming priority

Rather than endless reductions based on a single startup trace, gather **additional offline application scenarios**: real KOReader EPUB/PDF paths, Ink Away save/reopen, fonts and locale selection, and optional browser rendering to a purely synthetic surface. Hardware/firmware paths remain separate research and are **not** implicitly authorized by R31.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.
