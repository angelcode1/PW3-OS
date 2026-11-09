# R3877.77 — bounded single-process ARM EABI execution (no UART)

**Research-only. `NOT_BOOTABLE` is immutable for standalone PW3-OS deployment.**

## Why this test

The user-reported R3877.76 live Kindle read-only probe established Linux
`3.0.35-lab126`, `armv7l`, VFP, VFPv3 and NEON in `/proc/cpuinfo`, and
executable files named `chroot`, `mount`, `losetup`, `initctl`, and `busybox`
in standard filesystem locations. Earlier `command -v` failures were PATH
search failures, not evidence that those files or kernel features were missing.
`/dev/root` is still mounted EXT3 read-only; the additional rootfs `rw`
pseudo-mount does not override that. `/mnt/us` is a `fuse.fsp` mount and the
lack of a `noexec` option does not prove native ELF execution.

## Test scope and safety

This Python source deterministically builds a tiny **312-byte ELF32 ARM EABI5**
executable containing eight fixed ARM instructions and a fixed output string.
The ELF has one `PT_LOAD` segment and no `PT_INTERP`, glibc, musl, loader,
heap, filesystem, network, display, input or privileged syscall dependency.
It issues only `write(1, marker, length)` and `exit(0)`.

The optional live command:

1. Establishes one SSH connection to the already-authorized running Kindle.
2. Verifies exact kernel release and architecture.
3. Refuses to proceed unless `/proc/mounts` shows an **existing** writable,
   executable `tmpfs` mounted exactly at `/tmp`, `/dev/shm` or `/run`.
4. Creates a private, one-shot RAM-backed directory, streams the 312-byte ELF
   from the Mac, verifies its byte count and SHA-256, marks it executable,
   runs it **once**, removes it and its directory, and verifies expected output.
5. Reports a bounded status without printing remote paths, hashes, or raw logs.

It **does write a temporary file to RAM and execute a newly constructed ARM
program as the SSH user (`root`)**. It does **not** run `chroot`, `mount`,
`losetup`, `initctl`, change boot scripts, remount, reboot, flash, touch
block devices or execute Alpine itself. If no suitable tmpfs exists, the test
refuses with `NO_EXISTING_EXECUTABLE_TMPFS` **without writing the payload**.
A connection failure or unexpected result stays `HOLD`; cleanup is confirmed
only on the successful path. If the remote connection is interrupted after
copying starts, a RAM temporary directory might remain until reboot and can
be investigated separately before retrying.

## Mac steps

```zsh
mkdir -p ~/Downloads/pw3-r3877-77
unzip -oq ~/Downloads/pw3-r3877-77-one-shot-arm-eabi.zip \
  -d ~/Downloads/pw3-r3877-77
cd ~/Downloads/pw3-r3877-77

shasum -a 256 -c SHA256SUMS_R3877_77.txt
python3 -B -m unittest -q test_r3877_77.py

# Safe default: no Kindle contact, expected HOLD and exit 2.
python3 -B pw3_r3877_77_arm_syscall.py

# Explicitly authorize the one-shot RAM-only ARM syscall probe.
setopt pipefail
python3 -B pw3_r3877_77_arm_syscall.py \
  --acknowledge-single-process-tmpfs-execution \
  --target root@192.168.8.102 --port 2222 \
  | tee r3877_77_result.json
printf 'R3877_77_EXIT_CODE=%s\n' "$?"
```

**Interpretation:** Exit `0` and `PASS_SINGLE_ARM_EABI_SYSCALL_ONLY` mean
only that the tiny ARM binary executed its output and exit syscalls on this
kernel and that the remote cleanup path completed. This does **not** prove
musl, dynamic ELF loading, hard-float calls, TLS, KOReader, graphics, mount
isolation, failure recovery or independent PW3-OS boot. An exit of `2`
means HOLD/REFUSAL; inspect `hold_category` and do not broaden automatically.
`NOT_BOOTABLE` remains unchanged in **both** cases.

## Private backup and recovery status

p1, p2, prepartition 32 MiB, and both eMMC boot-area image transfers were
verified by matching remote and local SHA-256 values. They capture the
current device state, not authenticated factory stock. The p3/p4 snapshots,
independent recovery console and restore capability are unverified. Do not
copy raw firmware images or private checksum records to the public GitHub
repository.
