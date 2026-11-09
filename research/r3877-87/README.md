# R3877.87 — native KOReader Widget / EventListener dependency-dispatch experiment

**STATUS: prepared, not executed on Kindle.** Host regression tests: **18/18 PASS**; ZIP checksum manifest and CRC PASS. **NOT_BOOTABLE** is immutable.

## Confirmed preceding device checkpoint

User-reported R3877.86: `PASS_KOREADER_EVENT_LUA_MODULE_SINGLE_PROCESS`, SSH exit 0, glibc mapping verified, pinned `ui/event.lua` import verified, temporary RAM files reported removed. No firmware, boot, mount or chroot modifications, KOReader GUI not started. Evidence: [R3877.86 pass JSON](../r3877-86/R3877_86_USER_REPORTED_LIVE_PASS.json).

## Next narrow source-pinned test

- Directly import genuine `ui/event` and `ui/widget/widget` from KOReader tag `v2026.07.2`; `ui/widget/widget` must itself import genuine `ui/widget/eventlistener`.
- Assert that a synthetic `Pw3Smoke` event dispatches through an in-memory Widget handler, then that an unhandled event is ignored.
- These three pinned upstream Lua files are 858, 2,011 and 1,104 bytes respectively, with exact Git blob SHA1s `3e042eb2a017e2a4e6fd27a6e4c1c7d2e388bd14`, `8dd4082b1a7ee533997ebfa8f963fb08487c1acb`, `545e6424b55cebf8c36e4ae58c79da6ebb002a69`.
- Reuse the R3877.83 glibc loader + LuaJIT ELF bundle, original pinned dependency validators and explicit RPATH inhibition. Every byte is verified after transfer and loader `--list` must show private RAM mappings before LuaJIT starts.
- Do **not** import UIManager, Device, blitbuffer, run GUI, mount, chroot, flash or alter stock startup. Exit on failure without automatic retry; cleanup may be unconfirmed on SSH timeout.

**R3877.87 source package:** `pw3-r3877-87-koreader-widget-dispatch.zip`, SHA-256 `b17a2739c7a962f7f7cbeb9085afa095e323c2c4a0c03f320c4ad7fb17272c07`. The self-contained source/test ZIP is attached to the conversation; this repository entry records the evidence and reproducible plan rather than claiming the unpublished scripts are repository-hosted.

## Local verification and experiment

Extract ZIP under `~/Downloads` and execute:
```zsh
cd ~/Downloads/pw3-r3877-87
shasum -a 256 -c SHA256SUMS_R3877_87.txt
python3 -B -m unittest -q test_r3877_87.py
STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
setopt pipefail
python3 -B pw3_r3877_87_widget_dispatch.py --stage "$STAGE" --review-only | tee r3877_87_offline.json
printf 'R3877_87_OFFLINE_EXIT_CODE=%s\n' "$?"
```

Expected host-only HOLD, exit 2, `offline_validation_passed=true`, `upstream_modules_exactly_pinned=true`. If that passes, and only after explicit user authorization, the one-shot test is:
```zsh
python3 -B pw3_r3877_87_widget_dispatch.py --stage "$STAGE" \
  --acknowledge-one-shot-kindle-widget-dispatch \
  --target root@192.168.8.102 --port 2222 | tee r3877_87_live.json
printf 'R3877_87_LIVE_EXIT_CODE=%s\n' "$?"
```
If successful, expected `PASS_KOREADER_WIDGET_EVENT_DISPATCH_SINGLE_PROCESS` with SSH exit code 0; no R3877.87 device pass has occurred yet.

**Never conflate module-dispatch success with KOReader GUI readiness, EPDC input/display, kernel/device firmware, backup completeness or independent recovery.**
