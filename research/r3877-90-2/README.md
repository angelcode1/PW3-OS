# R3877.90.2 — transport-first KOReader 12-case batch

**Hold:** `NOT_BOOTABLE`. No independent boot/recovery, display/input, KOReader GUI or full application runtime verified. The Kindle has **not** run R3877.90.2.

## Evidence

- R3877.90 host preflight matched all nine pinned Lua modules but its live SSH returned 255 with no verified case log. `REMOTE_OUTPUT_SIZE_OR_TERMINATOR_INVALID` was a **secondary parsing symptom**; zero of 12 batch cases could be verified.
- User ran R3877.90.1 read-only inventory: SSH exit **0**, one recognized tmpfs mount scanned, **0** matching `pw3-r3877-90-*` temporary directories observed. `CONNECTION_RESET_OR_BROKEN_PIPE` was a classification of **verbose stderr** and does not supersede the successful SSH exit. Independent cleanup is not fully verified.
- R3877.89 genuine WidgetContainer child dispatch and earlier native glibc/LuaJIT tests remain valid on the physical PW3.

## Replacement diagnostic runner

The separately delivered `pw3-r3877-90-2-transport-batch.zip` has ZIP SHA-256 `a8f57c2ca93b68d26cee1e10b2eb0a73110e2d8a174109883810709ba3f0abd4`.

- The exact original R3877.90 remote shell and 12-case LuaJIT workload are pinned byte-for-byte (source SHA-256 `502da633408e7a27e44fffebf22be1b714df50df81ac6fad8bee494a9ed33b35`).
- The original R3877.90.1 diagnostic classifier is pinned SHA-256 `452fd8247825611869f86f503cf533336618efad007ad33c322ec5677102ad59`.
- Adds keepalive options and transport-first SSH error reporting. SSH 255 does **not** enter case-log parsing.
- Live mode remains **explicit opt-in**, transfers one prevalidated bundle to an already-mounted executable tmpfs, runs one LuaJIT process, and never retries automatically.
- `--verbose` reports per-case PASS/FAIL, CPU ms, and Lua heap KiB when the entire strict output log is received.
- Optional `--ssh-debug --private-ssh-stderr <absolute-new-path>` saves raw SSH diagnostics to a private 0600 **local Mac file**, never to the JSON.
- Synthetic host suite: **54 tests PASS** (original 28 and new transport 26). ZIP integrity, source SHA manifest and generated shell syntax verified. No physical test executed for this version.

Runnable script and its pinned helper sources are currently distributed in the conversation ZIP. Do not claim that repository CI has run or that those helper source files have been individually published by this documentation commit.

## Mac workflow

```zsh
cd ~/Downloads
unzip -oq pw3-r3877-90-2-transport-batch.zip -d ~/Downloads
cd ~/Downloads/pw3-r3877-90-2
shasum -a 256 -c SHA256SUMS_R3877_90_2.txt
python3 -B -m unittest -q test_r3877_90.py test_r3877_90_2.py
STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
setopt pipefail
python3 -B pw3_r3877_90_2_transport_batch.py --stage "$STAGE" --review-only --verbose | tee r3877_90_2_offline.json
printf 'R3877_90_2_OFFLINE_EXIT_CODE=%s\n' "$?"
```

Only if the offline report says `offline_validation_passed=true` and `all_nine_source_pins_match=true`, a separate attended live attempt may be explicitly authorized:

```zsh
python3 -B pw3_r3877_90_2_transport_batch.py \
  --stage "$STAGE" \
  --acknowledge-one-shot-kindle-batch --verbose --ssh-debug \
  --private-ssh-stderr "$PWD/r3877_90_2_ssh_stderr_PRIVATE.log" \
  --target root@192.168.8.102 --port 2222 \
  | tee r3877_90_2_live.json
printf 'R3877_90_2_LIVE_EXIT_CODE=%s\n' "$?"
```

The private log must not exist before the command; retain it locally. If any SSH interruption, timeout, remote refusal or incomplete output occurs, retain `HOLD`, **do not retry automatically** and perform a separate read-only inventory before considering any further device test.
