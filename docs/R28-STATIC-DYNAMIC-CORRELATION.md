# R28 — offline static/dynamic dependency correlation

**2026-11-01:** R25.3 verified synthetic ARM/QEMU lifecycle PASS; R26 user-generated catalog PASS (2,070 staged entries, 83 ELF objects); R27 user-generated guest syscall trace PASS (2,262 path attempts, 697 successful guest opens). **R28: 26/26 local synthetic host tests PASS; R28 on user's real staged R26/R27 inputs NOT YET RUN.**

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
