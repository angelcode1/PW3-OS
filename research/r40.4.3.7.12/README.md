# R40.4.3.7.12 — read-only original TouchMenu INDEX_ERROR site classifier

**2026-11-04. Host tested; ARM/QEMU pending; NOT_BOOTABLE. Research and educational purposes only.**

The user's public R3711 reviewer reports original `FileManagerMenu:onShowMenu()` started and then raised `INDEX_ERROR`, before returning the native TouchMenu. No actual menu widget selection/new third view PASS; earlier R375 historical synthetic draw/save/native HandlerSandbox event PASS remains separately valid.

Original KOReader v2026.07.2 `frontend/ui/widget/touchmenu.lua` reads `Device.input.group.Back` and `.PgFwd/.PgBack` at lines 518/523/524. The previous R17 synthetic input construction did not make that field a requirement. **It may or may not be the actual cause.** R3712 is an exact one-line source-pinned insertion around the **unchanged original** `pcall(fm_menu.onShowMenu,fm_menu,tab_idx)`: a read-only `R4043712_SYNTHETIC_INPUT_GROUP_{ABSENT|INCOMPLETE|COMPLETE}` state and an error-site category `R4043712_TOUCHMENU_ERROR_SITE_{TOUCHMENU_LINE_n|FILEMANAGERMENU_LINE_n|INPUTCONTAINER_LINE_n|TOUCHMENUITEM_LINE_n|OTHER|NOT_APPLICABLE}`. The source-line number is bounded by the known upstream Lua file line count; arbitrary private error text, paths or tracebacks are never included in public JSON. On error the original R3711 exception handling still fails closed. No `Device.input.group` modification, mock event, original widget override, original source change or altered internal filename is performed.

The entire original **R3711→R3710→R378→R377→R375→R373→R372→R37→R36→R353→R35** strict reviewer chain and R26/13-Lua source preflights remain required. The R3710 synthetic DPI and 18 original source/line `dofile` allowances remain identical. A new marker is **diagnostic only** and cannot turn a nonzero guest into PASS. No physical tap/stylus or real screen interaction is claimed.

**Versioned standalone conversation ZIP** `pw3-os-r40.4.3.7.12-touchmenu-index-site.zip`, SHA-256 `7eb007f17a52d8706b43b17ff2dab552177042541415ad8418e3b4ba70c8c1b3`, 43,664 bytes, 13 archive members (12 checksummed payloads). Clean-extraction CRC and every manifest SHA-256 PASS, **44/44 host tests PASS** twice after clean extraction, Mac-style `test` wrapper PASS; four shell syntax checks PASS. Tests include original guard exact rebuild, no input mutation, original reviewer chaining, manifest and extra-source tamper refusal, output overwrite refusal, generated cache metadata, malformed/duplicate diagnostic markers, nonzero exit and prior strict-reviewer refusal. None of the original staged private Lua files or raw logs is committed to GitHub.

Mac commands:

```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.12-touchmenu-index-site.zip -d pw3-os-r40.4.3.7.12-touchmenu-index-site
SRC="$HOME/Downloads/pw3-os-r40.4.3.7.12-touchmenu-index-site"
sh "$SRC/RUN-R4043712-MAC.sh" test
sh "$SRC/RUN-R4043712-MAC.sh" stage-check
sh "$SRC/CHECK-R404374-DOCKER.sh"
# only when all checks pass; use a fresh, nonexisting output directory
sh "$SRC/RUN-R4043712-MAC.sh" trial
```

Default run directory `~/Downloads/pw3-os-r40.4.3.7.12-touchmenu-index-first-run`; if it exists, supply a new output path as the second argument to `trial`, never delete or overwrite existing runs. Share only `R4043712-REVIEW.json`, optionally `R4043712-SUMMARY.json` if full strict PASS. Retain private QEMU raw trace, original source-stage inventory and original 9-file menu archive off GitHub. Offline Docker image `pw3-r394-reopen-trial` is required, with network disabled, original stage/release read-only, dropped privileges, non-root UID, disposable tmpfs HOME.

No recomputed observed regular stage-file union (historical **347** only); retain **1,101** unobserved regular staged files, **976** historical UNKNOWN_HOLD records. Decoder incomplete, complete dependency closure and authenticated R26 provenance unproven. No boot, hardware/firmware writes, physical device access, file deletion or pruning. **NOT_BOOTABLE**.


## R3712 reported source-preflight HOLD, before QEMU (2026-11-04)

User Mac reported the generic source-preflight refusal marker. The original verifier catches all exceptions with a single message, so the first failing gate is unknown. No QEMU was run. The original R3712 guest/reviewers and earlier R375 historical pass remain unchanged. Independent local verification of the R3712 package's own manifest, original R3711 pins and exact guest insertion passed against the distributed releases, but this does not establish whether the Mac's inherited checks passed.

R40.4.3.7.12.1 is a standalone read-only doctor that runs the unchanged R3712 original verifier and emits only predefined failing gate/method/error category, never raw error text, private source paths or trace. It does not run Docker/QEMU or modify the stage. No bypass of a source integrity failure. NOT_BOOTABLE.


## Repeated R3712 source-preflight HOLD: consolidated read-only audit (2026-11-04)

The user again reported R3712 own manifest SHA checks OK, followed by `R4043712_EXACT_ORIGINAL_MENU_ERROR_SITE_OR_PRIOR_SOURCE_HOLD; NO_QEMU; NOT_BOOTABLE`. This is not a new QEMU error. Earlier diagnostic identified `R3712 / read / REQUIRED_FILE_NOT_FOUND` involving the original R3711 source read, but the new generic refusal does **not** establish whether that prerequisite is now resolved or which file fails next. Avoid another blind trial.

To prevent serial one-file-at-a-time repair, a standalone read-only script `R4043712-ALL-PREREQUISITES-READONLY.py` was generated, SHA-256 `b8cc5981845745fd5913480539dc7e18ead43b70a29d44c71e33cde36efe0fdc`, 26,319 bytes. Its expectations derive from checksum-validated original conversation release ZIPs: all 13 relevant public release directories, 160 member SHA-256 pins (including each manifest itself), both collector-file digests and all 18 R378-pinned original KOReader v2026.07.2 menu-source Git blob IDs. Fixed allowlisted labels report every missing/altered file, symlink or unknown extra without exporting arbitrary paths, source content, or private records. Local fixture testing PASS: all 13 clean extracted public releases and collector hashes; missing original R3711 source; modified SHA member; two simultaneously missing releases; unknown extra redaction and symlink refusal. The 18 stage-source Git SHA checks are included but **not independently tested against the user's real stage**. The original R3712 verifier and stage were not changed, and the script cannot certify entire inherited source/semantic gates; full existing `stage-check` is still mandatory after any fixes. No Docker/QEMU/device/firmware/boot/delete/prune. **NOT_BOOTABLE**.


## User reports corrected full preflight PASS (2026-11-04)

The user ran the corrected R3712 public-and-stage audit: **13/13 public release directories, 160/160 SHA-256 file pins and 0 problems**, including all 18 original staged KOReader menu Git blob hashes after correcting the standalone auditor's mistaken stage-root prefix. The user then ran the **unchanged original `RUN-R4043712-MAC.sh stage-check`**, with own archive SHA member checks OK, and received `R4043712_ORIGINAL_SOURCE_AND_PREVIOUS_STRICT_GATES_PASS; NOT_BOOTABLE`. This resolves earlier missing-prerequisite and false-path audit HOLDs, and establishes that all original R3712 source gates passed in that Mac run. It does **not** claim that the forthcoming trial's separate original R35 R26 2,070-entry inventory/13 private staged-source preflight or offline Docker guest has run yet. Next safe action: check the existing offline Docker image and run `sh "$SRC/RUN-R4043712-MAC.sh" trial "$OUT"` with a fresh, non-symlinked and nonexisting output path. That launcher re-runs checks, authenticates original R26 inventory/source captures, and invokes only pre-existing isolated offline ARM image; if a check fails it refuses. Upload only the sanitized `R4043712-REVIEW.json` (and summary only if PASS), retain private stdout/raw QEMU trace locally. The original TouchMenu INDEX_ERROR module/line remains unknown until the guest executes. No real touch, device/firmware writes, deletion, boot or pruning; **NOT_BOOTABLE**.

## User ARM attempt blocked by original R35 directory guard (2026-11-04)

The user reports `CHECK-R404374-DOCKER.sh: OK`, full R3712 archive hash checks OK, 44 host tests PASS and `R4043712_ORIGINAL_SOURCE_AND_PREVIOUS_STRICT_GATES_PASS; NOT_BOOTABLE`; the later trial stopped with `R40435_PREFLIGHT_REFUSED: ValueError: stage/source path missing or aliased; NOT_BOOTABLE`, so QEMU never ran.

Exact source inspection of original shipped R35 `r40435/preflight.py` locates this refusal at `verify()` lines 103–107, where it checks nine original input directories as non-symlink real directories: stage, R403 source, R40431 source, R4002 source, R40432 source, R40433 source, R40411 source, R40434 source and the R35 release itself (`Path(__file__).resolve().parent.parent`). These earlier source directories were not covered by the newer R3712 13-release manifest audit; consequently 13/13 release PASS does not establish this guard. The script reports one generic message without identifying which input is absent.

The R3712 original Mac `trial` launcher also requires eight earlier evidence files: R26 inventory JSON; R40431 private and public summary; R40432 public review; R40433 private and public summary; R40434 prior passing review; R40435 private staged UI source capture ZIP. Check all source directories and those evidence files in one *read-only fixed-label* inventory before considering any restoration. Do not fabricate evidence, weaken old R35 verifier, rerun QEMU, touch the original stage or publish private files. No QEMU was started; TouchMenu original INDEX_ERROR line not yet tested. Immutable NOT_BOOTABLE.

## Seven R35 source directories and eight evidence files absent from canonical paths (2026-11-04)

The user's read-only original R35 preflight input inventory reports `R40435_INPUT_SUMMARY DIRS=2/9 EVIDENCE=0/8; NO_QEMU; NOT_BOOTABLE`. The present directories are the R13 stage and the R35 release itself. Missing original historical source directories at expected Downloads paths: R403, R40431, R4002, R40432, R40433, R40411, R40434. Missing evidence filenames: R26 inventory, R40431 private and public summary, R40432 review, R40433 private and public summary, R40434 review, R40435 private source capture ZIP. This proves only the paths are missing, not that all copies have been erased from Trash/offline archives. Original R35 preflight refused at the nine-directory guard; it has **not** rerun the R26 2,070-inventory or 13 original Lua source comparisons and **no QEMU execution has begun**.

The conversation's original recoverable artifacts were checked locally: original R40432 public release ZIP SHA-256 `2c7970087295b2c89baf19b3343e9dab8755805e5d3e35253980b0bec96d2c23` (10 manifest entries PASS); R40434 release ZIP `a8c3d218704fdca53fdff86fff1eab62ffd3416dc1bce5117adf94206932033c` (9 manifest entries PASS); original R40435 private capture ZIP `68caa882ab99c9fd83458b59a97efba011aa798ef1f9e76c540a93ed2ec5e29d`, exactly matching `PIN_PRIVATE_SOURCE_ARCHIVE` in original bundled R35 preflight. These three are separate, user-provided conversation artifacts, not grounds to synthesize other historical records or to publish the private archive on GitHub.

A new standalone chat script `R40435-LOCATE-ORIGINAL-INPUTS-READONLY.py`, SHA-256 `abd8a8cd4181e75986d5fc693f83a46d9295b702cd1e4077d28228e6c654d35c`, searches HOME and /Volumes for all seven exact original directory basenames and eight exact evidence filenames, plus likely archive name candidates. It classifies symlink vs regular file/directory and prints paths only; no private source contents, archive extraction, writes, Docker/QEMU or device access. A scratch fixture covering an original source directory, one evidence file and one archive match PASS. It is a locator, not an authenticity check; every found copy must still pass the unchanged prior digest/strict source preflight.

Next user action is read-only local discovery; then evaluate authentic source/evidence copies individually and restore only to absent target paths without overwrites, after recording their trusted provenance. The original source stage, provenance restrictions and full R35 strict preflight must remain unchanged. Historical 347 observed opens not recomputed, 1,101 unobserved regular files and 976 UNKNOWN_HOLD retained; no boot/hardware/firmware/delete/prune. **NOT_BOOTABLE**.
