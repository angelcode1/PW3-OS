# R40.4.3.7.7 — original FileManager Tools → TouchMenu selection experiment

**2026-11-04. HOST TESTED; ARM/QEMU PENDING; NOT_BOOTABLE. For research and educational purposes only.**

The user's R40.4.3.7.6 private nine-source menu collector and public audit were inspected. CRC and all 9 manifest member hashes PASS; ZIP SHA-256 `44889dbfd47a18854beaeec2c739bb11afca1033c10c125ec2f576573d568e83`; static menu contract candidates present. This does not amount to a runtime UI or menu PASS. The R40.4.3.7.5 prior public reviewer reports authentic HandlerSandbox native `InkAwayOpen` dispatch, a second genuine InkAwayView, and prior R36 draw/save/reload within one offline ARM run; private raw trace was not independently replayed.

The R377 guest extends the **exact** prior R375 Lua guard at one source-pinned insertion after the second view has closed. It requires genuine original FileManagerMenu, original registered InkAway action and original sorted Tools tab, opens the actual FileManager menu through its original method, checks an original TouchMenu instance and its uniquely identified InkAway item, and calls **original TouchMenu:onMenuSelect** on that live item. It never directly invokes `item.callback`, `onInkAwayOpen` or `InkAway:openCanvas` from the new insertion; verifies third original InkAwayView, menu teardown and FileManager restoration.

**Scope distinction:** This tests a *synthetic menu-widget selection via the original TouchMenu selection API*, not a synthetic raw tap through `TouchMenuItem:onTapSelect`, not physical touchscreen input and not an actual displayed tap. The trial is fail-closed if the emulated runtime chooses the non-touch `Menu` widget, the Tools entry is absent/ambiguous or the prior strict tests regress. The original R375 reviewer and entire R373/R372/R37/R36/R353/R35 strict chain are mandatory; guest zero exit and old decoded mutation confinement are mandatory. No existing original stage or Lua source is patched.

A new source-only preflight verifies the current staged originals against every digest in the private R376 ZIP and checks the original original FileManagerMenu/TouchMenu/InkAway menu contracts; it also reads the staged MenuSorter and menu-order implementation for lexical signs, without assuming that static code proves runtime selection. The prior R375 gate checks the original R26 2,070-item and private 13-file staged-source references before QEMU. Docker uses existing prebuilt `pw3-r394-reopen-trial` only, with network off, read-only stage/release mounts, privileges dropped, non-root UID and disposable tmpfs HOME; no device mount, boot, firmware write, or pruning.

**Standalone chat ZIP:** `pw3-os-r40.4.3.7.7-touchmenu-selection.zip`, SHA-256 `cdb878586d4337d2af86b91555ea86a71a78143e183b1793227778da1b1004bc`, 41,629 bytes, 12 ZIP members (11 SHA256SUMS entries); clean extraction and manifest integrity PASS, **21/21 host tests PASS**, shell syntax PASS, one source-contract fixture made from the uploaded originals PASS. The runnable guest, reviewer, source verifier, one-command Mac launcher and runbook are inside this ZIP; none of the private source files is committed.

Mac procedure:

```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.7-touchmenu-selection.zip -d pw3-os-r40.4.3.7.7-touchmenu-selection
SRC="$HOME/Downloads/pw3-os-r40.4.3.7.7-touchmenu-selection"
sh "$SRC/RUN-R404377-MAC.sh" test
sh "$SRC/RUN-R404377-MAC.sh" stage-check
sh "$SRC/CHECK-R404374-DOCKER.sh"
# only after all three pass
sh "$SRC/RUN-R404377-MAC.sh" trial
```

Default new guest output: `~/Downloads/pw3-os-r40.4.3.7.7-touchmenu-first-run`. Share only `R404377-REVIEW.json` and if present `R404377-SUMMARY.json`; keep raw trace and original menu source captures private. **ARM has not run yet.** No recomputed stage-open union: old 347 only; preserve 1,101 stage regular files unobserved and 976 historical UNKNOWN_HOLD, optional puzzles, incomplete QEMU decoder, unproven R26 provenance and incomplete dependency closure. **NOT_BOOTABLE; no device/hardware/firmware actions, file removal or pruning.**


## Uploaded R377 guest failure and raw trace boundary (2026-11-04)

The user provided `R404377-REVIEW.json`, `R40435-EXIT.txt`, private guest stdout and raw QEMU stderr. The run exited 1; review verdict `R40_4_3_7_7_GUEST_OR_STRICT_MENU_SELECTION_HOLD`. The last completed original checkpoint was `R40437_SECOND_VIEW_CLOSED_FILEMANAGER_RESTORED`, after R36 original drawing/save/reload and R375 original native plugin entry markers; no `R404377_*` menu markers were present. The original R39 guard printed `R39_4_3_FIRST_DENIAL kind=DOFILE` for the genuine `frontend/apps/filemanager/filemanagermenu.lua` call at line 504. The precise denied original source request is `frontend/ui/elements/common_settings_menu_table.lua` inside FileManagerMenu `setUpdateItemTable()`. The old R375 strict reviewer holds on the nonzero exit; this does **not** invalidate the preceding R375 public ARM PASS. Original runtime menu/third view remain untested.

Inspecting the tagged KOReader v2026.07.2 sources identifies 18 literal original menu-element `dofile` targets across FileManagerMenu, common-settings and screen-eink submenus, including nested conditional imports. The [R40.4.3.7.8](../r40.4.3.7.8/README.md) experimental correction adds only narrowly authenticated source/line/state/single-use allowances for those exact imports, keeps the original R39 denial for all others, requires all 18 original staged modules to match fixed upstream Git blob pins **before** QEMU, and preserves the unchanged R377/R375/earlier strict reviewer chain. No arbitrary source execution, physical menu tap, boot, firmware writes or pruning are authorized. The original private raw trace and original staged contents have **not** been committed; **NOT_BOOTABLE**.
