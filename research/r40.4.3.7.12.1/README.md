# R40.4.3.7.12.1 — source-only inherited preflight classifier

Research and educational only. NO_QEMU, NOT_BOOTABLE.

The user reported a generic source-preflight HOLD in R40.4.3.7.12 without a diagnostic category. This package runs the **unchanged** R3712 original verification code read-only, printing only a fixed allowlisted gate, method and refusal reason. It does not change original guest, reviewer, prior releases, source stage or Docker image. It does not launch QEMU, Docker, boot or access hardware.

Artifact: pw3-os-r40.4.3.7.12.1-preflight-doctor.zip, SHA-256 bff12d068e2233f8f5dce966f6d4c8448b0e95a00bf511399a08a1fa089086b3, 5,481 bytes, 5 members, 4 SHA-256 manifest payloads. ZIP CRC PASS and clean extraction 9/9 host tests PASS, shell wrapper syntax PASS.

Mac:
```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.12.1-preflight-doctor.zip -d pw3-os-r40.4.3.7.12.1-preflight-doctor
DIAG="$HOME/Downloads/pw3-os-r40.4.3.7.12.1-preflight-doctor"
sh "$DIAG/RUN-R4043712-PREFLIGHT-DOCTOR-MAC.sh" test
sh "$DIAG/RUN-R4043712-PREFLIGHT-DOCTOR-MAC.sh" diagnose
```

Send only the fixed classification line. Do not delete old results, replace original staged source, relax any verifier, or start QEMU until the hold is identified. Prior 347 observed stage regular opens not recomputed; 1,101 unobserved regular stage files and 976 historical UNKNOWN_HOLD records retained. No authenticated R26 provenance, complete dependency closure, physical touch, boot or firmware write. NOT_BOOTABLE.


## R3712.1 Mac original-verifier source failure classified (2026-11-04)

The user ran R3712.1 read-only doctor on Mac. Host doctor unit tests and four extracted file checks reported OK; the doctor returned **`R4043712_DOCTOR_HOLD GATE=R3710 METHOD=verify REASON=OTHER_REFUSAL; NO_QEMU; NOT_BOOTABLE`**. This locates a fixed R3710 source-verification refusal, not an R3712 ARM guest failure. The doctor omitted several original R3710 `Refusal` message literals from its reason map; therefore `OTHER_REFUSAL` is not a root cause and must not be interpreted as arbitrary execution failure. R3710's fixed branch possibilities at that stack frame include absent/symlinked original R378 directory, probe digest mismatch, changed native entry, or probe/source rewrite mismatch. The original distributed R378/R3710 ZIP pair was independently cross-checked locally: all five R378 public file pins, R3710 own guest/probe digest, exact source insertion, entry equality and probe rewrite PASS. Those local results **do not establish the Mac's extracted copies**. A separate **read-only, public-safe** `R4043710-LOCAL-PIN-DIAG.py` script was generated and verified with clean, missing-prior-directory and tampered-probe fixtures; it compares only the previously known public release files and prints a categorical outcome without source/paths or hashes. No prior gate has been weakened or altered; do not run QEMU until the Mac extracted-release condition is known. No private staged sources or traces committed. **NOT_BOOTABLE**.


## Mac local pin diagnostic identifies missing or symlinked R378 directory (2026-11-04)

The user executed the standalone read-only original R3710 public-pin checker and received `R4043710_LOCAL_PIN_DIAG=ORIGINAL_R378_DIRECTORY_ABSENT_OR_SYMLINK; NO_QEMU; NOT_BOOTABLE`. The check is specifically for the exact regular directory `~/Downloads/pw3-os-r40.4.3.7.8-menu-dofile-bridge`; it cannot determine from this result alone whether the path is absent or a symlink. The expected original release ZIP `pw3-os-r40.4.3.7.8-menu-dofile-bridge.zip` was independently SHA-256 verified: `23496a87c9dee3a3e298291d29141e3e2437d24a0e3c1aaf2127f91ec6b03dd0`. Safe recovery is to check for any existing path (including symlink), refuse overwrites, authenticate the downloaded ZIP with this SHA-256, then use `unzip -n` to extract into the **exact absent directory**. If the original path is a symlink, do not overwrite or follow it; inspect manually. Repeat the original read-only `R4043710-LOCAL-PIN-DIAG.py` afterward. This does not establish that every other source pin or inherited verifier will pass; no QEMU was started or boot/firmware/stage permissions changed. **NOT_BOOTABLE**.


## Mac original R378 release directory restored: source-only pin PASS (2026-11-04)

After the SHA-256-authenticated original R378 ZIP was restored under the expected release directory, the user reran the original R3710 read-only local checker. Exact terminal result: `R4043710_LOCAL_PIN_DIAG=SOURCE_ONLY_PIN_CONTRACT_PASS; NO_QEMU; NOT_BOOTABLE`. This validates only the public R3710/R378 local release-file relationships, **not** every inherited original source-stage gate or an ARM execution. Next step is rerun the unchanged `sh "$SRC/RUN-R4043712-MAC.sh" stage-check` from the existing extracted R3712 release. Only if this full preflight and existing Docker doctor PASS should the unchanged R3712 offline diagnostic be run into a new output directory. The original TouchMenu INDEX_ERROR source line is not yet captured. Previous R375 public synthetic drawing/save/native event PASS remains historical. No original stage edits, source pin bypass, firmware write, boot, removal or pruning; **NOT_BOOTABLE**.


## User Mac R378 inherited `verify()` HOLD after restoring R378 (2026-11-04)

The unchanged R3712.1 read-only doctor now reports `R4043712_DOCTOR_HOLD GATE=R378 METHOD=verify REASON=OTHER_REFUSAL; NO_QEMU; NOT_BOOTABLE`, progressing from the earlier R3710 refusal. The exact failure is unknown. Inspection of the original R378 verifier isolates **three direct Refusal messages omitted from the doctor's reason map**: `original R377 missing` (missing or symlinked R377 extraction), `guest patch not exact` (bounded original R377 bridge reconstruction mismatch), and `entry modified` (original native menu entry mismatch). All R377/R378 ZIP public file pins, exact R378 guest bridge insertion, entry and probe comparison pass under an independent clean local extraction, but the user's Mac copies are not verified. The next diagnostic is the unchanged read-only doctor with only those three fixed reason labels added in memory at runtime—no patch to a verifier or stage, no Docker or QEMU. No original menu widget selection or complete ARM PASS is inferred. **NOT_BOOTABLE**.


## Mac R3712/read missing required public file (2026-11-04)

The user ran an unchanged-source verifier classifier that now reports `R377_DIRECTORY=PRESENT` and `R4043712_DOCTOR_HOLD GATE=R3712 METHOD=read REASON=REQUIRED_FILE_NOT_FOUND; NO_QEMU; NOT_BOOTABLE`. In original R3712 `verify()`, after manifest/reference validation, five original R3711 public files are read directly from `~/Downloads/pw3-os-r40.4.3.7.11-touchmenu-show-boundary/r4043711/`: `loop_guard.lua`, `review.py`, `verify.py`, `01_gesture_dispatch.lua`, `probe_in_container.sh`. The exact missing file is not disclosed by the doctor and is not established. The original R3711 release ZIP has SHA-256 `e5ff56759e8db12b69752ff5f913abe0b48a9e5b224ac03d7f546de947782afb`, and local archive inspection verified all five original source files exist as regular entries with no symlinks. The next step is a **read-only** directory/file presence check on the Mac, followed (only if the exact target is absent) by SHA-256 verification and no-overwrite extraction into the expected path. Do not replace a partial, existing or symlinked source directory automatically, and do not bypass original pins. No QEMU or hardware operation; TouchMenu INDEX_ERROR site still unknown, **NOT_BOOTABLE**.
