# PW3-OS R3877.62 — Stop non-discriminating QEMU time64 experiments; inventory recovery evidence

Research and educational purposes only. **Physical Kindle status: `NOT_BOOTABLE`**. Do not copy/execute ARM code on the Kindle, flash/write partitions, attempt recovery, reboot or boot the experimental image. This is a **Mac-only, read-only directory name/size inventory** and cannot establish a functioning recovery pathway or authenticate original firmware.

## What the actual R3877.61 run established

The user reported exit `0` and `PASS_QEMU_MUSL_GETENTROPY_ENOSYS_AND_GUEST_STATX_EMULATION_ONLY`. Host-side seccomp self-tests confirmed `getrandom` and `statx` both return `ENOSYS`. The ARMv7 guest made two `getrandom` calls, both returned `ENOSYS`, and the pinned musl `getentropy` reported the error rather than providing internal secure-entropy fallback. Cleanup succeeded; parent image remained unchanged. This result is recorded in `research/r3877-61/R3877_61_USER_REPORTED_SELECTED_PASS.json`. It **does not verify an application entropy strategy**.

## Why not repeat the host seccomp simulation for time64?

Pinned musl 1.2.6 `src/time/clock_gettime.c` Git blob `4d2ec22f38a0012867632c7fcea763f090246174` contains logic to try guest `clock_gettime64`, then fall back to `clock_gettime` on `-ENOSYS` (with additional case-specific behavior).

But pinned QEMU 10.0.4 `linux-user/syscall.c` Git blob `3a25abfaca2ef9f0a049cc38e74133c3187aaca7` dispatches **both guest** `clock_gettime` **and** `clock_gettime64` via the **same host** `clock_gettime()` call. Filtering the host call is therefore not a discriminating test of the guest time64 fallback: both guest paths can be affected, and QEMU may implement guest semantics independently of the Kindle's kernel. An accurate test would need controlled *guest-syscall* fault injection, not the inherited host-only filter. No such verified guest instrumentation or Kindle recovery path is currently available. Do not claim old-kernel time64 compatibility from Colima/QEMU success.

## Mac-only candidate inventory

```zsh
mkdir -p ~/Downloads/pw3-r3877-62
unzip -oq ~/Downloads/pw3-r3877-62-recovery-inventory.zip -d ~/Downloads/pw3-r3877-62
cd ~/Downloads/pw3-r3877-62
shasum -a 256 -c SHA256SUMS_R3877_62.txt
python3 -B -m unittest -q test_r3877_62.py

# No directory supplied: intentional HOLD, no scanning, exit 2.
python3 -B pw3_r3877_62_recovery_inventory.py > r3877_62_preflight.json
printf 'R3877_62_PREFLIGHT_EXIT_CODE=%s\n' "$?"

# Local file metadata only (never copies, hashes, or opens image contents).
setopt pipefail
python3 -B pw3_r3877_62_recovery_inventory.py \
  --scan-root "$HOME/Downloads" \
  --max-depth 3 \
  --max-files 12000 \
  | tee r3877_62_inventory.json
printf 'R3877_62_INVENTORY_EXIT_CODE=%s\n' "$?"
```

Expected result **always** `HOLD`, exit `2`. This is by design. The JSON reports *counts and aggregate sizes* of possible image/dump files, recovery notes, and relevant archives without publishing local filenames, directory paths or contents. Symlinks are never followed; `Library`, hidden dirs, `node_modules`, and `.git` are skipped. This is a bounded local metadata inventory, not a backup or recovery test.

If the local inventory is empty, select a different *specific local directory* with `--scan-root`. The scan is local-only: no Docker, network, Kindle SSH, or background monitoring. A high candidate count cannot lift the `NOT_BOOTABLE` hold.

## Recovery assurance requirements (separate independent evidence)

Before any physical Kindle native-code test, establish and document all of the following:

1. Known-good, independently sourced **original** boot/recovery/rootfs artifacts with verified identities and hashes (not merely a filename match).
2. A documented **independent recovery interface** reachable when the normal OS does not boot, with operator-confirmed access and commands suitable for the exact PW3 hardware revision.
3. Tested, safe restore procedure and an independently verifiable readback / rollback path; a static local backup alone is not a recovery verification.
4. Actual vendor kernel ABI and userspace compatibility checks, as separate from QEMU host syscalls. Kernel `3.0.35-lab126` source/config and QEMU do not on their own prove this.
5. An application-specific secure entropy strategy that does not assume musl `getentropy` will fall back when `getrandom` is unsupported.

None of those five requirements is asserted as complete by this inventory. The physical Kindle remains **`NOT_BOOTABLE`**, regardless of the result.
