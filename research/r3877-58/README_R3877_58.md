# PW3-OS R3877.58 — First expanded off-device QEMU runtime gate

**For research and educational purposes only. `NOT_BOOTABLE` is immutable for the Kindle.** No Kindle SSH, eMMC/firmware writes, recovery or boot operations. QEMU uses the **Colima host's Linux kernel**, not the physical Kindle's Linux `3.0.35-lab126` kernel.

## Context

R3877.57 user-reported Mac PASS verified the pinned BusyBox 1.37.0-r31 `armv7` ELF carries the exact 304-name applet array; `ash` is present, `seedrng` is not. This does not execute applets. R3877.49.3 previously ran pinned ARMv7 BusyBox `true`, `uname`, and `echo` on Colima via pinned AArch64 QEMU 10.0.4. R3877.58 stops adding source-only tests and expands **runtime** observation on exactly the same pinned image and QEMU helper, using the unchanged R49.3 safety harness.

## What is actually exercised

Run untraced controls, then separate `qemu-arm-static -strace` observations of the following **existing** BusyBox applets:

| Probe | Actual guest command | PASS condition |
| --- | --- | --- |
| Startup | `/bin/busybox true` | exit 0, no output |
| Shell | `/bin/busybox ash -c "printf 'PW3_R58_ASH_OK\\n'"` | exact marker |
| File metadata | `/bin/busybox stat -c %s /bin/busybox` | positive decimal file size |
| Clock | `/bin/busybox date +%s` | plausible Unix timestamp |
| Device read | `/bin/busybox od -An -tx1 -N16 /dev/urandom` | exactly 16 hex octets |

Each traced run must exit 0, observe at least one QEMU syscall record and have a preceding independently verified untraced control. The trace parser may leave output attribution unresolved; this is reported rather than hidden. No raw random bytes, syscall pointer arguments, kernel symbol addresses or private file paths are published in JSON.

**Not tested:** musl pthread creation, ARM-private TLS runtime on the physical Kindle, `getrandom`-ENOSYS application fallback, ABI compatibility with the real vendor kernel, actual Kindle GPU/display, binary build reproducibility and recovery. This is not a Linux 3.0.35 compatibility pass. Even the QEMU `/dev/urandom` read uses a host-provided device endpoint and must not be mistaken for an on-device entropy test.

## Safety controls

- Default mode returns HOLD/exit 2 with no Docker access.
- QEMU authorization is explicit; the optional writable disposable guest needs an **additional** explicit flag and is attempted only after a read-only copy failure is positively classified.
- The unchanged byte-pinned R49.3 runner checks the Colima ARM64 host, exact ARMv7 immutable parent image ID `sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a`, the QEMU helper image and binary SHA-256, and the original BusyBox SHA-256.
- Guest runs are `--network none`, nonprivileged UID 65534, capability-drop-all, `no-new-privileges`, no host bind mounts/devices, 64 PID and 256 MiB limits. Each temporary container must be removed and the parent image identity rechecked.
- No additional ARM guest binary is compiled, copied or executed; QEMU is the only host executable injected into a disposable guest.

## Mac commands

```zsh
mkdir -p ~/Downloads/pw3-r3877-58
unzip -oq ~/Downloads/pw3-r3877-58-qemu-runtime.zip -d ~/Downloads/pw3-r3877-58
cd ~/Downloads/pw3-r3877-58
shasum -a 256 -c SHA256SUMS_R3877_58.txt
python3 -B -m unittest -q test_r3877_49_3.py test_r3877_58.py

# Expected HOLD, exit 2; no Docker.
python3 -B pw3_r3877_58_qemu_applets.py > r3877_58_preflight.json
printf 'PREFLIGHT_EXIT_CODE=%s\n' "$?"

# Explicit OFF-KINDLE QEMU test, first try read-only guest injection:
setopt pipefail
python3 -B pw3_r3877_58_qemu_applets.py --authorize-offline-qemu \
  | tee r3877_58_result.json
printf 'R3877_58_EXIT_CODE=%s\n' "$?"
```

If the result is `HOLD` specifically because `read_only_copy_probe.classification == READONLY_ROOTFS_COPY_REJECTED` and `base_error_category == READONLY_COPY_REJECTED_WRITABLE_FALLBACK_NOT_AUTHORIZED`, an operator may separately authorize a **disposable writable container layer** (never the parent image):

```zsh
python3 -B pw3_r3877_58_qemu_applets.py \
  --authorize-offline-qemu --allow-disposable-writable-layer \
  | tee r3877_58_writable_fallback_result.json
printf 'R3877_58_WRITABLE_EXIT_CODE=%s\n' "$?"
```

Do not retry on other HOLD categories. A first real PASS is classified as `PASS_PINNED_QEMU_BUSYBOX_ASH_STAT_DATE_URANDOM_RUNTIME_ONLY`; all device-compatibility and recovery gates stay HOLD. GitHub CI runs **only host-only synthetic tests and preflight**, with no Docker daemon/QEMU or physical device access.

## Following gate

Once off-Kindle applet execution passes, the next meaningful work is a separately pinned **off-Kindle ARM pthread+TLS program** and controlled `getrandom`-ENOSYS test, plus an independent recovery assessment. Neither is included or claimed here. `NOT_BOOTABLE` remains immutable.
