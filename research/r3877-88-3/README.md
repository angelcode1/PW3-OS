# R3877.88.3 — UTF-8 source-pin correction (host-only)

**R3877.88.2 refusal was a tooling bug, not evidence of staged-source drift.** The Python reference-recovery step checked the Git API's 10,735-byte blob against a mistaken 10,734-byte assertion. The user independently printed: `PREVIOUS_RAW_BYTES 10735` and `PREVIOUS_RAW_GIT_SHA dc8362ae455d3fddce2513865d340b482a9bdc53`. The latter proves the *downloaded reference* has exact pinned content; it does **not** by itself authenticate the staged R13 file.

## Cause

The official KOReader `v2026.07.2` Git blob `frontend/ui/geometry.lua` has one non-ASCII `µ` (U+00B5), which takes two UTF-8 bytes. Previous research tool metadata used the decoded string length **10,734 characters**, not the correct **10,735 bytes**. The actual Git blob SHA-1 was always correctly pinned as `dc8362ae455d3fddce2513865d340b482a9bdc53`.

This affected three Mac-only preflights:
- R3877.88 `PINS['ui/geometry']` expected 10,734 bytes and incorrectly classified the 10,735-byte staged file as `PINNED_MISMATCH_HOLD` without letting its hash decide.
- R3877.88.1 inherited that mistaken byte length and reported `ONE_BYTE_LONGER_BUT_NOT_SINGLE_INSERTION` when the source may in fact match.
- R3877.88.2 used `REF_BYTES=10734`, rejecting an otherwise hash-correct upstream reference.

## Correction

Keep the Git blob SHA exactly unchanged. Change only the expected **byte lengths** to `10735` in all three tools. Do **not** edit `ui/geometry.lua` or any R13 stage file.

The host-only correction package `pw3-r3877-88-3-utf8-pin-correction.zip` was created in the conversation: 18 synthetic tests passed, SHA-256 manifest verified, ZIP integrity verified. It contains fixed copies of the three scripts plus `pw3_r3877_88_3_pin_correction.py`, which rechecks all eight KOReader source pins **on the original stage** and the separately pinned KOReader-base Serpent source. The tested executable source is currently distributed as the conversation ZIP; this document does not claim its bytes are independently in GitHub or that CI ran.

Run:
```zsh
cd ~/Downloads
unzip -oq pw3-r3877-88-3-utf8-pin-correction.zip -d ~/Downloads
cd ~/Downloads/pw3-r3877-88-3
shasum -a 256 -c SHA256SUMS_R3877_88_3.txt
python3 -B -m unittest -q test_r3877_88_3.py
STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
setopt pipefail
python3 -B pw3_r3877_88_3_pin_correction.py \
  --stage "$STAGE" --acknowledge-host-only-pin-correction | tee r3877_88_3_result.json
printf 'R3877_88_3_EXIT_CODE=%s\n' "$?"
```

Expected exit 2, `HOLD / NOT_BOOTABLE`. If stage matches, expect `all_nine_source_pins_match=true` and `hold_category=ALL_NINE_GIT_BLOBS_MATCH_DEVICE_RUNTIME_STILL_UNVERIFIED`.

The code does not contact the Kindle or modify the stage. The original R26 stage identity, full module dependency closure and WidgetContainer runtime, GUI/display/input, independent restore and standalone boot remain unverified. No native execution or boot authorization is implied.
