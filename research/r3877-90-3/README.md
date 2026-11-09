# R3877.90.3 — short SSH-command KOReader batch (host-tested)

**Status**: host synthetic tests **80/80 PASS**, original six-ELF + nine-Lua closure and twelve assertions retained, native Kindle **NOT RUN**. Mandatory hold: `NOT_BOOTABLE`.

## New evidence
- User R3877.90.2 reported SSH exit 255, stdout 0 bytes, stderr 12,151 bytes, no verified batch log and cleanup unconfirmed.
- Read-only R3877.90.1 inventory before the subsequent failure is not a new cleanup attestation.
- Generated command argument was **9,020 bytes** (R3877.90) compared with **5,778 bytes** (R3877.89, device PASS).
- R3877.90.3 stages SHA-256 checked `batch.lua` as a regular tar member and invokes by path. Its generated SSH command is **4,817 bytes** with the synthetic source fixture, strictly below 8,000.
- Its 12 cases are the same as R90, with per-case stdout flush, six bounded stderr phase markers and strict fail-closed validation. SSH 255 is a transport hold, never a test failure/pass.
- Local source tests 28 + 26 + 26 = **80/80 PASS**. Complete tar construction, POSIX shell syntax, guards, invalid phase order, positive/negative simulated SSH results are tested.
- No boot, flashing, mounts, e-ink, input or power actuation. Native execution would be explicitly opted-in root SSH with temporary RAM files only; cleanup may remain uncertain after a disconnect.

## Distribution / provenance
Archive: `pw3-r3877-90-3-short-argv-batch.zip`, SHA-256 `02ac9e9b7f8f54ebc7e43dfddd7fd8170256dfa2a903545679449d47358f0480`.

The runnable source archive and checksum manifest are delivered in the conversation. This research note alone is not the runnable source and no new GitHub CI PASS is claimed.

## Safest next steps
1. Verify source manifest and 80 host tests, then `--stage "$STAGE" --review-only --verbose`. Expected `HOST_SHORT_COMMAND_BATCH_READY_DEVICE_UNVERIFIED` with `remote_command_bytes` around 4817, exit 2.
2. **After** the latest R90.2 failed connection, rerun the read-only R90.1 inventory and require SSH exit 0, >=1 scanned tmpfs and 0 matching R90 directories. Do not delete anything.
3. If a fresh inventory and host preflight pass, a single attended explicit `--acknowledge-one-shot-kindle-batch` is possible. Never automatically retry. Complete per-case PASS output plus SSH 0 and six phase markers needed for batch PASS.

Full KOReader application, driver safety and independently verified restore/boot remain unverified.
