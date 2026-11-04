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
