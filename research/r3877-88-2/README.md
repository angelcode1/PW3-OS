# R3877.88.2 — host-only geometry source-drift comparison

**Status: runnable local package tested, real R13-stage result pending. NOT_BOOTABLE.**

## Why

The user-reported R3877.88.1 analysis established:
- `ffi/serpent.lua`: 8,979-byte exact match to KOReader-base `6e4bc81af4e04f78d81677a323a780a71b29702a`, upstream blob `812668de60aefeedfad1cbfca211a877a7dcaea0`.
- `ui/geometry.lua`: 10,735 bytes in the R13 stage versus 10,734 bytes upstream; the staged file **does not** become the pinned upstream Git blob by omitting any single byte. The mismatch remains a HOLD, not a license to modify the stage.
- The original R3877.88 eight-file stage scan was 7/8 exact. R26 original stage regular-file count (1,448) differs from the newer scan (1,446), provenance unresolved.

## Exact upstream source reference

KOReader v2026.07.2 annotated tag resolves to commit `9192014d8bd82a91dc1012473be0f238dedfdb54`. Its `frontend/ui/geometry.lua` source is **10,734 bytes**, Git blob SHA-1 `dc8362ae455d3fddce2513865d340b482a9bdc53`.

## Local R3877.88.2 package

ChatGPT conversation artifact: `pw3-r3877-88-2-geometry-diff.zip`, ZIP SHA-256 `86b5138440128f63e33894f9b2a816df4f63721a45a95ca436d18358e086bd51`.

This is a **Mac-only, read-only, stdlib Python** source comparison:
- 18 synthetic host tests PASS; package checksum manifest and ZIP integrity verified.
- Explicit opt-in only; both files opened no-follow, bounded regular files; no network functionality inside Python.
- Public upstream file downloaded separately from the exact pinned commit, validated by Git blob SHA-1 and byte count before the staged file is compared.
- Reports first differing byte, common prefix/suffix, line counts and endings, CRLF normalization status and up to twelve non-disclosing changed-line alignment hunks. No raw stage source excerpts or stage-file hash in report.
- No SSH/device connection, no Lua/ELF execution, no mounts, no stage modifications, no boot/firmware changes, no GUI.
- Always `HOLD / NOT_BOOTABLE`, exit 2; **no R3877.88.2 real staged source result yet**.
- The full source/test suite is in the tested conversation ZIP and is **not yet versioned here as standalone files**. Do not claim CI or user execution.

## macOS commands

```zsh
cd ~/Downloads
unzip -oq pw3-r3877-88-2-geometry-diff.zip -d ~/Downloads
cd ~/Downloads/pw3-r3877-88-2
shasum -a 256 -c SHA256SUMS_R3877_88_2.txt
python3 -B -m unittest -q test_r3877_88_2.py
curl -fL --retry 0 --connect-timeout 10 --max-time 30 \
  'https://raw.githubusercontent.com/koreader/koreader/9192014d8bd82a91dc1012473be0f238dedfdb54/frontend/ui/geometry.lua' \
  -o geometry-v2026.07.2-upstream.lua
STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
setopt pipefail
python3 -B pw3_r3877_88_2_geometry_diff.py \
  --stage "$STAGE" \
  --upstream-geometry "$PWD/geometry-v2026.07.2-upstream.lua" \
  --acknowledge-readonly-two-file-diff \
  | tee r3877_88_2_result.json
printf 'R3877_88_2_EXIT_CODE=%s\n' "$?"
```

Never edit the original staged geometry to fit a digest. Any future separately staged pristine upstream module requires explicit review; current module/GUI/boot/recovery holds remain.
