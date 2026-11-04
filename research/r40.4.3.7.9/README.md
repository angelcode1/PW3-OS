# R40.4.3.7.9 — existing R378 run read-only trace classifier

**2026-11-04. HOST TESTED; EXISTING TRACE NOT YET ANALYSED ON USER MAC; NO NEW ARM/QEMU. Research and educational only. NOT_BOOTABLE.**

The user's R378 public review reports a hold after original R375 second InkAwayView close and before original common-settings menu source returned: one `R404378_MENU_IMPORT_ENTER_3` without a corresponding return; index 3 is original `frontend/ui/elements/common_settings_menu_table.lua`. No Tools-menu widget selection or third view was reached. The exact internal failure is unknown without the local private trace.

This version ships only a Python read-only diagnostic and shell launcher, not a new guest. It requires the existing R378 trace `R40435-GUEST-STDOUT-PRIVATE.log` and `R40435-EXIT.txt`, reads optional `R40435-QEMU-RAW-PRIVATE.log` for safe counts, categorizes an original `R39_4_3_FIRST_DENIAL` record if present, and emits fixed checkpoint names and predeclared error categories. If no denial is recorded, the public result says `IMPORT_UNRETURNED_CAUSE_NOT_VISIBLE_IN_STDOUT`. No raw paths, arbitrary Lua exceptions, source or strace arguments are exported. Existing run, original stage and earlier strict reviewer remain unchanged. The diagnostic refuses to overwrite its public output or follow symlinked trace files.

**Standalone versioned conversation ZIP:** `pw3-os-r40.4.3.7.9-existing-trace-diagnostic.zip`, SHA-256 `49011a2975aef98e1fa56539304af9d8a00312ba1b24723cfabe560246fb2380`, **9,370 bytes**, 6 ZIP entries (5 SHA-256 manifest entries). ZIP CRC/member checks PASS, clean-extraction wrapper PASS, **21/21 host tests PASS**, shell syntax PASS. Includes adversarial redaction, fake denial kinds, malformed guest exit, symlink refusal, overwrite refusal, manifest tamper/unlisted-source refusal and Python cache handling. A smoke test on an *older* provided R377 private trace reports the already-known original FileManagerMenu `DOFILE` denial at line 504; this is not a finding about the R378 failed run.

Mac commands:

```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.9-existing-trace-diagnostic.zip -d pw3-os-r40.4.3.7.9-existing-trace-diagnostic
SRC="$HOME/Downloads/pw3-os-r40.4.3.7.9-existing-trace-diagnostic"
sh "$SRC/RUN-R404379-MAC.sh" test
sh "$SRC/RUN-R404379-MAC.sh" diagnose \
 "$HOME/Downloads/pw3-os-r40.4.3.7.8-touchmenu-run-02" \
 "$HOME/Downloads/R404379-EXISTING-R378-DIAG-PUBLIC.json"
```

If the failed R378 run used another output path, substitute that **existing** directory in the second command. Only upload the public JSON `R404379-EXISTING-R378-DIAG-PUBLIC.json`; retain private trace files on the user's Mac. If the exported categories are insufficient, the next step is to inspect privately supplied R378 trace data, without publishing it.

Historical staged regular-file open union **347 not recomputed**, all **1,101** unobserved regular stage files and **976** historical UNKNOWN_HOLD preserved. Original R26 provenance unauthenticated, decoder incomplete, dependency closure unproven. **NOT_BOOTABLE; no hardware/device/firmware writes, file removal, boot, pruning or physical touch.**


## Uploaded R40.4.3.7.9 existing-run diagnostic (2026-11-04)

User-uploaded `R404379-EXISTING-R378-DIAG-PUBLIC.json` (SHA-256 `46b0b536fc73fde9576ca3c1507d25c36e20f0bc4cc03694f6508a4a8869a9be`) confirms the original R378 guest exited 1 after the original R375 second-view-close checkpoint. The common-settings menu-source import (#3) remained unreturned, as did nested `SCREEN_DPI` (#13), which was the last menu source entered. Three import enter markers but only one return marker, with malformed/incomplete source marker pairing. **No original R39 guard denial or classifiable Lua error** appeared in stdout; QEMU raw trace 9,495 lines (9,488 syscall-format) was counted, without independently diagnosing the internal Lua error. R379 was a read-only analysis of the existing run, not a new guest execution. No original TouchMenu selection or third view PASS has been established.

In original KOReader v2026.07.2 `screen_dpi_menu_table.lua`, the top-level expression `Screen.device.screen_dpi` is evaluated on module import. The experimental R378 synthetic screen sets `screen.dpi=300` and width/height but does not explicitly establish that `screen.device.screen_dpi` field. **Missing synthetic metadata is only a hypothesis**. R40.4.3.7.10 tests it under an exact imported original module and synthetic-device identity/state gate: if the in-memory screen lacks `.device`, attach `{screen_dpi=300}` only to that in-memory fake screen. A preexisting correct table is left intact; any other state rejects. Original staged source, R378 menu import security gate and entire strict reviewer chain are unchanged. ARM/QEMU result still pending. No physical input/boot/firmware writes or pruning: `NOT_BOOTABLE`.
