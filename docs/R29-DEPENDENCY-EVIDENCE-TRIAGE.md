# R29 — host-side dependency evidence triage after verified R28 PASS

**2026-11-01:** User-reported R28 `R28_STATIC_DYNAMIC_CORRELATED` **PASS** after running 26/26 tests and correlating the verified R26 static stage with R27/QEMU private guest file attempts. **R29 is host-tested against synthetic fixtures only (26/26 tests PASS), and has NOT been run on the user's local R26–R28 evidence.** No rootfs was created or modified.

## Facts from the user's R28 summary

The R26 stage had **2,070 catalog entries**: 1,448 regular files, 335 symlinks, and 287 directories. R28 tied **665 successful guest-open calls** to staged catalog files, representing **341 distinct regular staged files**. The remaining **1,107 regular staged files** and **622 other catalog entries** lack successful-open evidence in this *one synthetic lifecycle*. All **1,729** remain `UNKNOWN_HOLD`; none are proven unused.

R28 observed **646** stage-looking lexical path attempts without a matching R26 catalog entry and **seven** ambiguous directory-FD-relative attempts. Its aggregate positive-open mapping has no `stage_lexical_path_not_in_catalog` category, but path-level outcomes and the unique attempted names must be checked locally. The 646 attempts could include failed dynamic-loader searches, absent optional files, or path-normalization artefacts; no specific cause or errno is proven without the private trace. R28 expressly did not establish symlink resolution, dirfd resolution, kernel firmware requirements, host-QEMU file access, or complete dependency closure.

R28 stage sentinel SHA-256 `7eb0d027b2b407fe6963ea9b9a1fe7fee1db96ae66f9399ece179238939176ed` and R27 raw trace SHA-256 `d02193b9b800fdc59cd7b7bf6367c7e2835e0afcfe0e1663ff0f6faa7e6ef49a` matched the supplied summaries. **No files are inferred safe to delete**, and the program is **NOT_BOOTABLE**.

## R29 narrow deliverable

Source-only ZIP `pw3-os-r29-dependency-evidence.zip`, SHA-256 **`a538b4f07659369e94e8f45b00bc7c0f9c5bc3a53d3c96bb3928c896404cfd39`** (3 payload files and SHA256SUMS; complete ZIP/manifest validation). Python stdlib-only. Local synthetic host suite **26/26 tests PASS**, including negative checks for forged counters, unverified stage hashes, invalid catalog paths, path-to-stage mismatches, altered original R28 input checksums, private path leaks in the summary, missing UNKNOWN_HOLD records, and output overwrite refusal.

The tool verifies R28's output hash manifest and the cross-R26/R27/R28 stage and trace hash relationships; reconciles private R28 path events with summary counters; checks exact catalog positive-open/UNKNOWN_HOLD partition; and counts additional review-only cohorts:

- Distinct staged regular files opened vs not opened;
- Staged ELF `DT_NEEDED` candidate filenames without guest successful-open evidence (including candidates referenced by ELFs that *were* opened);
- Lua files with static literal references but no guest successful-open evidence;
- Symlinks marked with lexical escape risks;
- Unique lexical stage-looking paths absent from the catalog (with failed/successful counts), and ambiguous dirfd-relative attempts.

**These cohorts overlap and are not a removal allowlist**. A `DT_NEEDED` candidate filename is not proven to resolve at runtime; a Lua string literal is not proof of module import; an absent catalog lookup is not necessarily a missing required file. All unobserved objects remain on hold.

Source-only ZIP is provided as a conversation download; no proprietary runtime, R26 inventory, private R28 correlation, Amazon firmware, or Kindle captures are committed.

## Mac commands — no Docker, no stage execution, no device access

```sh
cd ~/Downloads
unzip pw3-os-r29-dependency-evidence.zip
cd pw3-os-r29-dependency-evidence
python3 -m unittest discover -s tests -v

python3 r29/analyze.py \
  --r26-inventory "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-INVENTORY.json" \
  --r26-summary "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-SUMMARY.json" \
  --r27-summary "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-SUMMARY.json" \
  --r28-private "$HOME/Downloads/pw3-os-r28-correlation-first-run/R28-CORRELATION.PRIVATE.json" \
  --r28-summary "$HOME/Downloads/pw3-os-r28-correlation-first-run/R28-SUMMARY.json" \
  --r28-hashes "$HOME/Downloads/pw3-os-r28-correlation-first-run/R28-SHA256SUMS" \
  --out "$HOME/Downloads/pw3-os-r29-triage-first-run"

cat "$HOME/Downloads/pw3-os-r29-triage-first-run/R29-SUMMARY.json"
```

**Share only `R29-SUMMARY.json`.** Keep `R29-REVIEW-HOLDS.PRIVATE.json` on the Mac. The runner fails closed, refuses existing output directories, and never operates on stage contents. Target verdict is `R29_DEPENDENCY_EVIDENCE_TRIAGED`; it is not an ARM runtime gate or proof of a bootable OS.

## Next research direction

Add independent offline workload traces for EPUB/PDF/Ink Away save-reopen and font/locale paths, then improve QEMU syscall path tracing to retain dirfd context. Work toward a **new** Alpine rootfs assembled from pinned and licensed inputs only after reviewing ABI/loader/ELF and test-scenario coverage. Never delete, prune, or overwrite the Kindle's stock userspace or existing R13 stage.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.
