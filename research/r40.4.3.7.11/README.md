# R40.4.3.7.11 — original TouchMenu show-boundary diagnostic

**2026-11-04. HOST TESTED; ARM/QEMU PENDING; NOT_BOOTABLE. Research and educational purposes only.**

The user's public R379 analysis of the existing R3710 QEMU failure confirms **14/14 original menu imports entered and returned**, no reported R39 denial, and the original Tools InkAway menu entry resolved; guest exited 1 and the next original TouchMenu shown marker was absent. It cannot tell whether the original `FileManagerMenu:onShowMenu` threw or returned a widget that failed the unchanged assertion.

The R3711 release is an exact **one-span** replacement of the SHA-pinned R40.4.3.7.10 guest, bracketing the original `FileManagerMenu:onShowMenu` with a one-time protected native method call. Error text is never exported: only six fixed categories and `OTHER`. On any failure, the guest **fails closed** with a sanitized error. If the original method returns, the guest records a fixed category for original TouchMenu source identity, sorted Tools table, tab index and UIManager stack/display visibility. Original selection via `TouchMenu:onMenuSelect(ink_item)`, original app/module files, original R3710 synthetic DPI bridge and the original R378 18-import guard are not changed. The full R3710→R378→R377→R375→R373→R372→R37→R36→R353→R35 original strict reviewer chain, prior source pins, R26 2,070-entry and 13 private staged Lua checks and zero guest exit remain mandatory for any PASS. This is a synthetic widget/API scenario, not a physical tap.

**Standalone chat ZIP:** `pw3-os-r40.4.3.7.11-touchmenu-show-boundary.zip`, SHA-256 `e5ff56759e8db12b69752ff5f913abe0b48a9e5b224ac03d7f546de947782afb`, **43,606 bytes**, 13 ZIP members, 12 SHA-256 manifest payloads. Clean extraction, all CRC/member hashes PASS; **43/43 host tests PASS** twice with Python cache generation enabled and separate Mac-style wrapper test PASS, shell syntax PASS. Tests include exact prior guest reconstructability, original strict-review refusal with nonzero guest, false widget/exception cases, duplicate/misordered markers, code/manifest tamper, unlisted sources, symlink and existing-output refusal and Docker read-only/no-network isolation. Original private staged source and raw guest traces are not committed to GitHub.

Mac steps:

```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.11-touchmenu-show-boundary.zip -d pw3-os-r40.4.3.7.11-touchmenu-show-boundary
SRC="$HOME/Downloads/pw3-os-r40.4.3.7.11-touchmenu-show-boundary"
sh "$SRC/RUN-R4043711-MAC.sh" test
sh "$SRC/RUN-R4043711-MAC.sh" stage-check
sh "$SRC/CHECK-R404374-DOCKER.sh"
# Only if all checks pass and output path is new:
sh "$SRC/RUN-R4043711-MAC.sh" trial
```

Default output `~/Downloads/pw3-os-r40.4.3.7.11-touchmenu-show-first-run`. Run into a distinct new output path using `trial "$HOME/Downloads/<new-name>"` if already present; do not delete old runs. Upload only `R4043711-REVIEW.json` and, if the strict reviewer passes, `R4043711-SUMMARY.json`. Keep private stdout/strace, original staged Lua and R26 inventory local. Offline Docker uses the unchanged prebuilt ARM64 image only, with network disabled, non-root user, read-only stage/release mounts, dropped capabilities and ephemeral tmpfs HOME. No image pull/build or device mounts.

Historical 347 staged regular-file observed-open union **not recomputed**; retain 1,101 unobserved regular stage entries and 976 historical UNKNOWN_HOLD records, incomplete QEMU decoder and unresolved R26 provenance/complete dependency closure. No original Tools-menu widget PASS, raw tap or physical device test is claimed. **NOT_BOOTABLE.**
