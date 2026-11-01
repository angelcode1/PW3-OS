# R26 — offline static dependency inventory after R25.3 ARM PASS

**2026-11-01. Verified checkpoint:** User-supplied `R25_REAL_EVENT_LOOP_ARM_PASS` with genuine KOReader v2026.07.2 `reader.lua`, real FileManager and Ink Away plugin ownership, genuine UIManager event loop, synthetic Close event, Generic:exit and clean shutdown (exit code 0). See [R24/R25 result history](R24.3-R25.3-STATUS.md). The reviewer still recorded `r23_full_arm_startup_verified=false`, `migrations_executed=false`, `real_pw3_init=false`, and all boot/device/firmware/hardware-write authorizations `false`.

**R26 is a new source-only offline host tool, not an ARM runtime proof.** Its role is to catalog the *local, immutable R13 stage* for the future minimal Alpine rootfs. It records file paths/types/modes/SHA-256, symlink targets and risk, ELF32/ELF64 machine/ABI, PT_INTERP, DT_NEEDED, SONAME, RPATH/RUNPATH, potential dependency candidates in the stage, and approximate Lua literal references (regex-based). Static references are not the same as loaded files. Dynamic `dlopen`/Lua-computed paths, kernel firmware requests, optional scripts and missing fallback paths require later runtime studies.

## R26 actual user-side result — 2026-11-01

The user ran the R26 host suite and stage catalog. Its terminal reported `Ran 15 tests in 0.032s — OK (skipped=1)`, meaning **14 executed successfully and one skipped**, not 15 unskipped PASS. The real local R13 stage inventory then printed `R26_STATIC_CATALOG_CREATED; NO_DYNAMIC_TRACE; NOT_BOOTABLE`.

Exact reported, shareable summary:

| Metric | Observed |
|---|---:|
| Stage entries | 2,070 |
| Regular files | 1,448 |
| Directories | 287 |
| Symlinks | 335 |
| ELF objects | 83 |
| ELF parse errors | 0 |
| Lua files with literal-pattern matches | 722 |
| ELF DT_NEEDED names with no staged candidate | 0 |
| R25.3 lifecycle evidence checked | yes |

Stage sentinel SHA-256: `7eb0d027b2b407fe6963ea9b9a1fe7fee1db96ae66f9399ece179238939176ed`. Full inventory stays local; only aggregated counts were provided.

Crucial scope values: `files_observed_during_runtime=false`, `safe_to_delete_inferred=false`, `boot_authorized=false`, `device_access_authorized=false`, `firmware_write_authorized=false`, `immutable_hold=NOT_BOOTABLE`. These values are **not** evidence of dynamic execution or a safely removable-file set. No missing DT_NEEDED candidates is a filename/SONAME matching result, not a guarantee that the loader resolves all dependencies.

The proposed R27 next phase is documented at [R27 source-only guest trace](R27-GUEST-SYSCALL-TRACE.md). It replays the existing synthetic R25.3 test while counting guest file access syscalls. **No R27 ARM/QEMU run has been reported**.

## R26 source-only deliverable

`pw3-os-r26-static-dependency-inventory.zip` is provided in the current conversation, SHA-256 **`3084db2fe0ec7d13618eaee609bf42083a834bba096f0a0c657287e4a4c0fa0c`**, four internally hashed payload files plus checksum manifest. Pure Python stdlib: `r26/inventory.py`, `r26/elfscan.py`, `tests/test_inventory.py`, `README-R26.md`. ZIP integrity/hash verification PASS, **15/15 synthetic host regression tests PASS** (not a test against the proprietary user's R13 stage, which is not present here).

The source tree is shipped in the conversation archive, not publicly committed as the full proprietary stage; the code itself is intentionally portable and contains no device captures. Reports are generated locally and must not be uploaded by default. Only the small **`R26-SUMMARY.json`** is intended for sharing after review.

The inventory source refuses to overwrite an existing output, refuses output inside stage, refuses special files and cross-filesystem directory mounts, never follows symlinks, records symlink escape risk, uses no network/host device mounts, never executes stage ELFs or `ldd`, and makes no deletions. The `R13-MANIFEST.json` is existence-checked and hashed but not authenticated as a signed image.

## Run on the user's Mac

```sh
cd ~/Downloads
unzip pw3-os-r26-static-dependency-inventory.zip
cd pw3-os-r26-static-dependency-inventory
python3 -m unittest discover -s tests -v

python3 r26/inventory.py \
  --stage "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  --out "$HOME/Downloads/pw3-os-r26-static-results-first-run" \
  --r25-log "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core/results-r25.3-first-run/R25.3-EMULATION.log" \
  --r25-review "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core/results-r25.3-first-run/R25.3-RESULT-REVIEW.json"

cat "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-SUMMARY.json"
```

`R26-INVENTORY.json` contains the potentially sensitive full file list, ELF/Lua details and hashes; **keep it local**. `R26-SUMMARY.json` contains aggregate counts only. The optional R25 log/reviewer pair proves only the lifecycle gate, not which files were dynamically opened.

## Interpretation, limits, next steps

1. **R26 static evidence:** classify known staged objects and find unresolved *candidate* DT_NEEDED matches. A path never referenced by static strings is only `UNKNOWN_HOLD`, never authorized for deletion.
2. **R27 dynamic evidence (proposed, not implemented):** offline QEMU syscall file-opening/exec/mmap tracing across multiple application scenarios, paired to exact build/run, preserving missing-path lookups, interpreter and driver exceptions. Never interpret a one-scenario trace as complete coverage.
3. **R28+ separate minimal Alpine rootfs reconstruction:** build a **new** rootfs from an audited allowlist of licensed inputs and transitive dependencies; never prune, delete or overwrite existing stock Kindle userspace in place. Test isolated glibc compatibility, Linux 3.0.35 ABI, power/EPDC components and recovery separately before contemplating any independent boot scope.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. No physical Kindle access, no boot actions, no firmware changes.
