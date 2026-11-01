# R28 — offline static/dynamic dependency correlation

**2026-11-01:** R25.3 verified synthetic ARM/QEMU lifecycle PASS; R26 user-generated catalog PASS (2,070 staged entries, 83 ELF objects); R27 guest syscall trace PASS (2,262 path attempts, 697 successful guest opens). **R28: 26/26 local host tests PASS and user-side static/dynamic correlation PASS** (`R28_STATIC_DYNAMIC_CORRELATED`; details below).

## R28 user-side result — verified by supplied output, 2026-11-01

The user completed 26 host regression tests (`Ran 26 tests ... OK`) and ran `r28/correlate.py` against their private R26/R27 files and immutable local R13 stage. Its output was `R28_STATIC_DYNAMIC_CORRELATED; NO_PRUNING; NOT_BOOTABLE`, with reviewer verdict `R28_STATIC_DYNAMIC_CORRELATED`. Crucial measured aggregate evidence:

| Class / metric | Result |
|---|---:|
| Staged R26 catalog entries revalidated | **2,070**, hashes revalidated |
| Guest path attempts | 2,262 |
| Guest open/openat attempts | 2,051 |
| Successful guest open calls | 697 |
| Successful calls lexically mapped to staged files | 665 (calls, not distinct files) |
| Distinct staged regular files with successful-open evidence | **341** |
| Staged catalog entries without successful-open evidence in this single trace | **1,729**, including directories and symlinks |
| Stage lexical paths absent from catalog | **646 attempts**, no corresponding successful-open evidence reported |
| Ambiguous FD-relative paths | **7 attempts**, mapping unproven |
| Test-harness attempts | 774 |
| Staged catalog path attempts (file+dir) | 743 |

The 1,729 not evidenced includes the R26 catalog's 287 directories and 335 symlinks; by subtraction, 1,107 of the 1,448 regular staged files have **no direct successful-open evidence in this scenario**. This is **not** a safe-to-delete list. `stage_catalog_entries_not_evidenced_as_opened_in_this_one_trace` counts object paths, not unused file bytes or proof of which files are needed.

Source R27 raw guest trace hash `d02193b9b800fdc59cd7b7bf6367c7e2835e0afcfe0e1663ff0f6faa7e6ef49a`, stage sentinel hash `7eb0d027b2b407fe6963ea9b9a1fe7fee1db96ae66f9399ece179238939176ed`; previous trace and stage evidence matched. The summary reports `complete_file_dependency_closure_proven=false`, `safe_to_delete_inferred=false`, `openat_relative_dirfd_mapping_proven=false`, `symlink_resolution_proven=false`, `new_rootfs_created=false`, and all boot/device/firmware authorizations false.

**Next investigation:** Analyze the 646 absent lexical attempts and seven ambiguous dirfd-relative attempts **locally**, where private paths are available; do not paste the private R28 full correlation JSON into chat. A subsequent classification may generate conservative dependency risk/hold categories, not removals.

## Objective and no-pruning boundary

R28 joins the **PRIVATE** R26 static catalog with the **PRIVATE** R27 guest path observations from the R25.3 synthetic lifecycle. It does not execute stage binaries, run Docker/QEMU, touch the Kindle, build an image, remove files, or infer that missing opens make a file unnecessary. The full path correlation is PRIVATE; share only aggregate counts in `R28-SUMMARY.json`.

- Stage must match every R26 catalog entry by pathname, mode, type, symlink target and file SHA-256, **without following symlinks**. Refuse missing/new/changed files, changed stage sentinel, and any special file.
- Validate R26/R27 scope and matching `R13-MANIFEST.json` sentinel SHA-256 `7eb0d027b2b407fe6963ea9b9a1fe7fee1db96ae66f9399ece179238939176ed`.
- Verify original raw guest trace hash against R27 summary and independently parse its event records/counters to ensure `R27-OBSERVATIONS.PRIVATE.json` actually came from the same trace.
- Lexically map ordinary guest relative paths against the known R27 QEMU working directory `/stage/rootfs/opt/koreader-compat/app`; absolute `/stage/*` paths map directly to R26's catalog. **Relative `openat` and related fd-based calls are ambiguous** unless dirfds are resolved by a later trace version. Do not claim symlink resolution, real successful loader resolution, or complete dependency closure.
- Count **successful opens** separately from failed probes and successful `stat`/metadata calls. Every stage entry not evidenced as opened in this one scenario has PRIVATE category `UNKNOWN_HOLD`, **never** `UNUSED` or `SAFE_TO_DELETE`.
- Reject existing results directories; create a new 0700 directory with 0600 JSON reports. No writes inside the staged rootfs or prior result directories.

## Source-only deliverable

Cumulative source-only archive, available in the ChatGPT conversation:

`pw3-os-r28-static-dynamic-correlation.zip` — SHA-256 **`0c8caa804bdffaaf299ca7323d7e81e80933490125ac2ed74073524b85016e58`**. Includes `r28/correlate.py`, `tests/test_correlate.py`, `README-R28.md`, and per-file `SHA256SUMS`. Archive ZIP integrity, internal 3 payload SHA-256 digests and **26/26 synthetic host tests PASS**. Tests cover original trace/observations consistency, stage mutation detection, source-summary mismatches, escaped paths, unsafe relative paths, relative `openat` ambiguity, metadata vs actual opens, output collisions and all immutable hold flags.

**No R28 result has been verified on the user's actual stage.** No proprietary stage content, raw file paths, Amazon firmware or Kindle device captures have been uploaded to GitHub.

## Run on the user's Mac (no Docker required)

```sh
cd ~/Downloads
unzip pw3-os-r28-static-dynamic-correlation.zip
cd pw3-os-r28-static-dynamic-correlation
python3 -m unittest discover -s tests -v

python3 r28/correlate.py \
  --stage "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  --r26-inventory "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-INVENTORY.json" \
  --r26-summary "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-SUMMARY.json" \
  --r27-observations "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-OBSERVATIONS.PRIVATE.json" \
  --r27-summary "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-SUMMARY.json" \
  --r27-trace "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-QEMU-GUEST-SYSCALLS.PRIVATE.log" \
  --out "$HOME/Downloads/pw3-os-r28-correlation-first-run"

cat "$HOME/Downloads/pw3-os-r28-correlation-first-run/R28-SUMMARY.json"
```

Expected success verdict **only after the user's run**: `R28_STATIC_DYNAMIC_CORRELATED`. `R28-CORRELATION.PRIVATE.json` is potentially sensitive and should **remain local**. If R28 rejects input, do not edit the original stage, inventory or trace to force a PASS; keep evidence for root-cause diagnosis.

## How this informs a smaller Alpine OS

R27 is a **single synthetic program lifecycle**, so it cannot classify unobserved files as removable. Additional offline scenarios should cover EPUB/PDF, Ink Away save/reopen, fonts/languages, battery/charging/frontlight, suspend/wake, Wi-Fi and NetSurf if included; hardware-specific scenarios must remain simulations under the current hold. The eventual reduced Alpine rootfs must be built **from scratch** from reviewed/licensed inputs and dependencies, with a protected stock system and validated rollback path. Do not delete Amazon firmware in place.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.
