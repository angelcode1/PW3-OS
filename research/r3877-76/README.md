# R3877.76 — No-UART runtime capability preflight

Research-only, **HOLD / NOT_BOOTABLE**. This milestone does not permit independent boot or replacing startup scripts. The user's active stock system and root SSH remain the safe control plane. Prior evidence records Linux `3.0.35-lab126`, `armv7l`, approximately 503 MiB RAM, and 2.28 GiB free under `/mnt/us` (FUSE `fsp`). `command -v` reported `chroot`, `mount`, `losetup`, `initctl` unavailable, but that alone does not prove system-call or applet absence. Previous Mac-only UART inventory returned zero recognized USB serial names; no independent restore was demonstrated.

## Device-side read-only check

On Mac, run:

```zsh
cd ~/Downloads/pw3-r3877-76
sh -n pw3_r3877_76_readonly_runtime_preflight.sh
setopt pipefail
ssh -T -o ConnectTimeout=15 -o ConnectionAttempts=1 -p 2222 \
  root@192.168.8.102 'sh -s' \
  < pw3_r3877_76_readonly_runtime_preflight.sh \
  | tee r3877_76_runtime_raw.txt
printf 'SSH_EXIT_CODE=%s\n' "$?"
```

It performs read-only queries of `/proc/cpuinfo`, `/proc/mounts`, and existence/executable bits in standard system directories. It never runs a custom ARM binary, changes the userstore, installs packages, calls `mount`, or changes the boot chain. The command does establish one authorized SSH session. Review and redact the output if necessary before publishing. Do not infer executable support merely because the FUSE mount lacks `noexec`.

## Follow-up decision

If ARM VFP and at least one suitable statically invokable runtime are present, plan a separately approved, bounded **single-process** ELF loader/ABI trial from an isolated temporary path. The trial must not chroot, mount, replace PID 1, control the e-ink device, intercept input, or install startup hooks. Keep the original Kindle UI and SSH reachable. Do not run the Inkwell install/start script for this test: its boot script deliberately mounts a rootfs image and changes userspace startup behaviour. Reference: https://github.com/pragyaangaur/Inkwell/blob/main/src/linux/boot.sh

## Holds

Vendor kernel syscall and musl/hard-float compatibility, FUSE execution, full KOReader runtime dependencies, physical e-ink/input drivers, independently verified restore access and standalone boot are **all unverified**. This is a capability inventory, not deployment approval.
