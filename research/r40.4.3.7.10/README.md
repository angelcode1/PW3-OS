# R40.4.3.7.10 — synthetic-only screen DPI metadata trial

**2026-11-04. 35/35 HOST TESTS PASS, ARM/QEMU PENDING; NOT_BOOTABLE. For research and educational purposes only.**

The user's public R379 diagnostic shows original R378 menu import #3 (common settings) remained unreturned, nested `SCREEN_DPI` #13 was last entered and did not return, with no logged R39 guard denial or categorized Lua stdout exception. QEMU exit 1. This does not independently prove an inner Lua error's cause.

Original staged KOReader v2026.07.2 `frontend/ui/elements/screen_dpi_menu_table.lua` reads `Screen.device.screen_dpi` at file load, while the R17 synthetic screen was previously authenticated through DPI=300 and memory-screen geometry without an explicit nested `.device` field contract. **Missing synthetic DPI metadata is a testable hypothesis only.**

The R3710 guest is exactly the SHA-pinned original R378 guest plus **one** block inserted before the already-authenticated original `screen_dpi_menu_table.lua` `dofile`. It requires original R378 source/caller/line/one-use checks and the isolated R17 synthetic device identity, 300 DPI, 1072×1448 memory screen geometry, unchanged FileManager/guest state and no prior denial. When only the fake screen's `.device` is absent, attaches `{screen_dpi=300}` **in memory to that synthetic screen only**, emitting `R4043710_SYNTHETIC_SCREEN_DPI_FIELD_INITIALIZED`. When a matching table already exists it emits `R4043710_SYNTHETIC_SCREEN_DPI_FIELD_ALREADY_VALID` with no change. All other states refuse. It does not modify original Lua, stage, device configuration, actual DPI, hardware, firmware or boot environment.

The original R378 guest import allowances (18 exact original menu source and line locations), genuine FileManager → Tools → native TouchMenu:onMenuSelect path and **entire previous R378→R377→R375→R373→R372→R37→R36→R353→R35 strict reviewer chain** remain mandatory. Success needs a unique correctly ordered DPI marker, original screen-DPI module return, zero QEMU exit and the full previous strict reviewer PASS including synthetic third InkAwayView close/restore and original decoded scratch-only mutation guard. It is a synthetic UI widget selection, not raw touch or physical pen testing.

**Standalone conversation archive:** `pw3-os-r40.4.3.7.10-synthetic-screen-dpi.zip`, SHA-256 `d1f7a5869753bba7ae94fb8cd4ff5d68e9a894fdc55ecc23644c4ce16630f00e`, 43,003 bytes, 13 archive members, 12 SHA-256-pinned source members, ZIP CRC PASS. **35/35 host tests PASS**, twice including clean extraction with Python cache generation and Mac-style wrapper, four shell syntax checks PASS. The launcher fixes the prior R378 typo by selecting a genuinely new default output path. Full code, diff and instructions are included in the ZIP. No private Lua or raw trace is committed.

Mac procedure:

```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.10-synthetic-screen-dpi.zip -d pw3-os-r40.4.3.7.10-synthetic-screen-dpi
SRC="$HOME/Downloads/pw3-os-r40.4.3.7.10-synthetic-screen-dpi"
sh "$SRC/RUN-R4043710-MAC.sh" test
sh "$SRC/RUN-R4043710-MAC.sh" stage-check
sh "$SRC/CHECK-R404374-DOCKER.sh"
# only if all pass and the new output directory does not already exist:
sh "$SRC/RUN-R4043710-MAC.sh" trial
```

Default output `~/Downloads/pw3-os-r40.4.3.7.10-screen-dpi-first-run`. For an existing output, do not delete/overwrite it: supply a fresh path as the second `trial` argument. Trial uses the existing offline `pw3-r394-reopen-trial` ARM64 image, non-root Docker user, no network, read-only stage/release mounts, no-new-privileges, dropped capabilities, disposable tmpfs HOME. Original R26 2,070-stage-file and private 13 Lua capture checks are required before QEMU. Share `R4043710-REVIEW.json` and, only on a strict PASS, `R4043710-SUMMARY.json`; keep raw QEMU trace/private sources local.

**Not tested:** original hardware touch, physical screen/menu tap, PW3 boot/device integration, verified firmware hardware reads/writes. Historical 347 staged observed opens not recomputed, 1,101 unobserved regular stage files and 976 old UNKNOWN_HOLD retained; QEMU decoder incomplete, authenticated R26 provenance and complete dependency closure unproven. **NOT_BOOTABLE; do not boot, write firmware, access hardware, remove files or prune.**
