# PW3-OS R3877.60 — QEMU older-kernel ENOSYS simulation, no Kindle access

**Research / educational purposes only. The physical Kindle remains `NOT_BOOTABLE`.** This is an opt-in Mac/Colima runtime test, not a native Kindle execution or boot. There are zero Kindle SSH sessions and no device, partition, recovery, root filesystem or firmware writes.

## Grounded starting point

The user's Mac R3877.59.2.1 result was a QEMU runtime PASS: ARMv7 hard-float musl process startup, `pthread_create`/join, TLS isolation, `getrandom` and `getentropy` succeeded **using Colima's host Linux kernel**. That does not test the older Kindle Linux `3.0.35-lab126` syscall table or fallback behavior.

Previous R3877.58 QEMU traces saw `statx` and `clock_gettime64`, neither of which can be assumed available on Linux 3.0.35. This step targets **`getrandom` and `statx` only**. It does not simulate `clock_gettime64`, establish `getentropy` fallback (musl has none), or establish the Kindle vendor kernel's actual syscall dispatch.

## Mechanism (strictly Mac-side)

A hash-pinned, *freestanding AArch64 executable* (`pw3_r3877_60_aarch64_seccomp_launcher.elf`) is used solely as the disposable guest entrypoint. It calls `prctl(PR_SET_NO_NEW_PRIVS)`, then stacks a small seccomp-BPF filter with `prctl(PR_SET_SECCOMP)`. The filter verifies AArch64 architecture and makes two **host** syscalls return `ENOSYS` (38): `getrandom` (AArch64 syscall 278) and `statx` (AArch64 syscall 291). For all others it adds no restriction, leaving Docker's existing built-in seccomp restrictions in force. It then `execve`s the unchanged pinned QEMU ARM user emulator.

This is an **extra stacked filter**, not `docker --security-opt seccomp=unconfined`, not a replacement `SCMP_ACT_ALLOW` Docker policy, and not a change to host or Kindle binfmt. The harness requires Docker Engine to report its **built-in seccomp profile**; verifies the strict guest isolation policy, the exact QEMU/helper/BusyBox/ARM payload hashes and launcher readbacks; and never starts a guest until these checks pass.

Independent untraced controls require:

- Original R59 ARMv7 pthread/TLS program to run and report the **actual guest-observed `getrandom` `ENOSYS` branch**, exit 0, with exact output.
- BusyBox `stat -c %s /bin/busybox` to return exactly the size of the pinned BusyBox ELF, exit 0.
- Separate QEMU `-strace` runs to show `getrandom` and `statx`, respectively, reporting `ENOSYS`. The trace can have unattributed output, recorded but not exposed. An `ENOSYS` from a different syscall **does not pass**.

**Pass does not mean:** target Kindle Linux 3.0.35 compatibility; vendor syscalls; original Alpine musl build provenance; genuine target kernel old ABI; app-level cryptographic fallback; musl `getentropy` fallback; native ARM application deployment; device boot/recovery. Those remain unverified and `NOT_BOOTABLE` stays immutable.

## Release verification on macOS

```zsh
mkdir -p ~/Downloads/pw3-r3877-60
unzip -oq ~/Downloads/pw3-r3877-60-qemu-enosys.zip -d ~/Downloads/pw3-r3877-60
cd ~/Downloads/pw3-r3877-60
shasum -a 256 -c SHA256SUMS_R3877_60.txt
python3 -B -m unittest -q test_r3877_49_3.py test_r3877_60.py
```

Expected: `Ran 103 tests`, `OK`. The tests are synthetic host-only; **they do not invoke Docker or run ARM code**.

Expected deliberate no-Docker preflight: `python3 -B pw3_r3877_60_qemu_enosys.py` exits 2 / HOLD.

## First real Mac QEMU test

The user's earlier R58/R59 runs documented a read-only Docker copy refusal. Thus the command below explicitly approves a **disposable writable container layer if and only if the new read-only copy is positively classified as read-only filesystem refusal**. It does **not** permit changing the parent image, host mounts, networking or Kindle.

```zsh
setopt pipefail
python3 -B pw3_r3877_60_qemu_enosys.py \
  --authorize-offline-qemu \
  --allow-disposable-writable-layer \
  | tee r3877_60_result.json
printf 'R3877_60_EXIT_CODE=%s\n' "$?"
```

If and only if all independent controls, filter marker, exact target syscall/ENOSYS traces, cleanup and unchanged parent image pass:

`PASS_QEMU_ARMV7_HOST_SECCOMP_GETRANDOM_STATX_ENOSYS_ONLY` / exit 0.

Otherwise the tool returns HOLD / exit 2. Do **not** loosen security, bypass the filter, rerun with random Docker options or run the payload on the Kindle to force success. Share the sanitized JSON and exit code for targeted correction. The generated report never includes raw guest syscall arguments, memory addresses, random bytes, host paths or arbitrary stderr.

## Prior evidence and provenance

- Pinned parent Alpine image: `sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a`.
- Pinned QEMU helper: `tonistiigi/binfmt:qemu-v10.0.4`, pinned digest and extracted SHA-256 checked by unchanged R49 helper.
- ARM pthread/TLS probe: SHA-256 `b0b89626cd48482e99ea8515b4c808c378e1ff65b4ea4de05b16a4c373df18f4`.
- AArch64 seccomp-launcher SHA-256: `66252ad8f424e8b902e8bb7c68021f9b367d962b02b926a818fda18af3fe49a4`; source provided for audit, but independently reproducible source-to-binary compiler provenance is not claimed.
- Linux seccomp filters stack with the highest-precedence action used; Docker default seccomp is an allowlist. References: https://kernel.org/doc/html/latest/userspace-api/seccomp_filter.html and https://docs.docker.com/engine/security/seccomp/.
