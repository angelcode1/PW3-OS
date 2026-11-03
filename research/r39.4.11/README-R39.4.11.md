# R39.4.11 — third genuine ReaderUI:init metadata sidecar read

**Status: HOST-TESTED ONLY; ARM/QEMU PENDING; NOT_BOOTABLE.**

The actual R39.4.10 guest was a strict FAIL after the previously blocked PdfDocument constructor metadata read succeeded. A **third** `dofile` was denied just after the second `ReaderUI:init` called `Input:inhibitInput(true)`. Original KOReader v2026.07.2 `frontend/apps/reader/readerui.lua` calls `DocSettings:open(file)` at line 131. The user-supplied R39.4.10 independent R25 guest control stayed PASS; original strict R39.4 and separate R39.4.10 reviews FAIL. Preserve those exact results.

The R39.4.11 experimental guard allows **exactly three**, source-bound reads of the *same* first-cycle-created disposable PDF sidecar, in fixed order: genuine FileManager provider lookup, original PdfDocument constructor conversion, then genuine `ReaderUI:init` at line 131 (after Input inhibit, before release). The third phase requires original Lua function identity and source line, the first PDF already closed, an open distinct second PDF present in the DocumentRegistry with reference count exactly 1, the same exact ordinary (not symlink) sidecar and original `DocSettings:open` through C `pcall`. All additional or alternate `dofile` attempts remain denied. The original two genuine metadata write-opens remain exact-source/mode-bound, with the second requiring the third successful sidecar read. Previous historical R39.4.7–R39.4.10 predictions/reviewers are retained, not repurposed.

The separate strict `r394/review_r39411.py` requires independently rerun unchanged original R39.4, R39.4.5, R39.4.6 and R25 gates PASS, three exact ordered source-bound sidecar observations, zero denied operations, both genuine Home returns, an empty DocumentRegistry on second close and final genuine FileManager Close. Nothing in this source trial constitutes an ARM PASS.

Run with fresh sibling output (same eight inherited inputs plus source and output):

```sh
cd "$HOME/Downloads"
SRC="$HOME/Downloads/pw3-os-r39.4.11-isolated"
mkdir -p "$SRC"
unzip -q pw3-os-r39.4.11-readerui-third-sidecar-arm-trial.zip -d "$SRC"
cd "$SRC"
shasum -a 256 -c SHA256SUMS-R39411
python3 -m unittest discover -s tests -q
sh ./run-r394-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json" \
  "$PWD" \
  "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.2.4-scroll-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.3.3-home-first-run/R39.3.3-SENTINEL-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.4.11-third-read-first-run"
```

Run the separate reviewer regardless of guest PASS/FAIL if the input files exist:

```sh
python3 r394/review_r39411.py \
  --log "$HOME/Downloads/pw3-os-r39.4.11-third-read-first-run/R394-EMULATION.log" \
  --baseline "$HOME/Downloads/pw3-os-r39.4.11-third-read-first-run/R394-R25-BASELINE-CONTROL.json" \
  --preflight "$HOME/Downloads/pw3-os-r39.4.11-third-read-first-run/R394-SOURCE-PREFLIGHT.json" \
  --previous-r39-3-3 "$HOME/Downloads/pw3-os-r39.3.3-home-first-run/R39.3.3-SENTINEL-REVIEW.json" \
  --strict-review "$HOME/Downloads/pw3-os-r39.4.11-third-read-first-run/R394-REVIEW.json" \
  --out "$HOME/Downloads/R39.4.11-THREE-READS-REVIEW.json"
cd "$HOME/Downloads"
zip -j R39.4.11-ARM-EVIDENCE.zip \
  pw3-os-r39.4.11-third-read-first-run/R394-EMULATION.log \
  pw3-os-r39.4.11-third-read-first-run/R394-R25-BASELINE-CONTROL.json \
  pw3-os-r39.4.11-third-read-first-run/R394-SOURCE-PREFLIGHT.json \
  pw3-os-r39.4.11-third-read-first-run/R394-REVIEW.json \
  R39.4.11-THREE-READS-REVIEW.json
```

Preserve failed evidence unchanged. The original R25 control and all original staged KOReader files remain unchanged. **NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE**. Preserve all 976 `UNKNOWN_HOLD` staged files. Research and educational purposes only.
