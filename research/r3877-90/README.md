# R3877.90 — batched non-graphical KOReader diagnostic

**Status (2026-11-09):** offline package generated and verified, **28/28 synthetic host tests PASS**, ZIP integrity and all included file SHA-256 manifest entries PASS. **Physical R3877.90 run NOT performed.** `NOT_BOOTABLE` remains in force.

User requested batch testing rather than one increment at a time. This is a controlled, high-signal test: 12 pure Lua tests in one LuaJIT process using the *same pinned R3877.89 six native ELF files and nine Lua modules*. A single SSH connection, checksum verification, loader mapping check, ephemeral tmpfs stage and cleanup path serve all cases.

**Cases:** `module_graph`, `bit_builtin`, `math_helpers`, `geometry_rectangles`, `serpent_serialize`, `logger_api`, `widget_instance`, `widget_inheritance`, `event_nil_varargs`, `child_priority`, `parent_fallback`, `widget_clear`.

**Logging:** Each case emits its own fixed status and controlled failure code. Optional `--verbose` reports CPU milliseconds and approximate Lua heap KiB. Host stdout parser enforces fixed case IDs, order, counts, ASCII and bounded size; it doesn't print raw source/stage paths or native traceback. A case failure doesn't stop diagnostic collection, but the overall run remains a HOLD. A disconnected SSH/timeout does **not** prove cleanup.

Local package (available separately in ChatGPT conversation, no licensed KOReader binaries included): `pw3-r3877-90-koreader-batch.zip`, **38,143 bytes**, SHA-256 `e59497657234c2792561e1411fb89f6a1a742df0dabbb2e74c8564acc220c97c`. Contains source, tests, pinned R89 dependencies, README and checksum manifest. The executable source and synthetic CI workflow **have not yet been published to the repo**; do not claim GitHub CI or an actual Kindle PASS for R90.

## Mac commands

```zsh
cd ~/Downloads
unzip -oq pw3-r3877-90-koreader-batch.zip -d ~/Downloads
cd ~/Downloads/pw3-r3877-90
shasum -a 256 -c SHA256SUMS_R3877_90.txt
python3 -B -m unittest -q test_r3877_90.py
STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
setopt pipefail
python3 -B pw3_r3877_90_batch.py --stage "$STAGE" --review-only --verbose | tee r3877_90_offline.json
printf 'OFFLINE_EXIT_CODE=%s\n' "$?"
```

Offline readiness is `offline_validation_passed=true`, `all_nine_source_pins_match=true`, `batch_case_count=12`, `hold_category=HOST_BATCH_READY_DEVICE_UNVERIFIED`, exit 2. Host-only if no explicit live opt-in.

Once that passes, user may separately run:

```zsh
python3 -B pw3_r3877_90_batch.py --stage "$STAGE" --acknowledge-one-shot-kindle-batch --verbose --target root@192.168.8.102 --port 2222 | tee r3877_90_live.json
printf 'LIVE_EXIT_CODE=%s\n' "$?"
```

Expected on all PASS and cleanup: `PASS_KOREADER_NON_GRAPHICAL_BATCH`, 12 case passes, exit 0, while `immutable_hold=NOT_BOOTABLE`.

Do **not** include the real UIManager, framebuffer, touch, input devices, power management, Wi-Fi or stock filesystem write operations in this batch. They require separately reviewed capability/effect gates. Independent restore and bootability remain unverified.
