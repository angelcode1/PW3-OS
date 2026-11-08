# R3877.49 — bounded QEMU ARMv7 syscall-name observation

Research and educational use only. **NOT_BOOTABLE**. No Kindle SSH, firmware writes, boot, host binfmt installation, guest host mounts, network or privileged containers.

## Starting point

R3877.47 user-reported QEMU runtime PASSED three BusyBox applets, with the original Alpine image unchanged. R3877.48 user-reported stopped-image ELF audit PASSED: pinned BusyBox SHA-256 `df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c` has `PT_INTERP=/lib/ld-musl-armhf.so.1`; the loader SHA-256 is `2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990`. See `research/r3877-48/R3877_48_USER_REPORTED_SELECTED_EVIDENCE.json`. Actual PW3 Linux 3.0.35 compatibility is still unverified.

## Standalone R3877.49 host tool

A new release ZIP `pw3-r3877-49-qemu-syscall-observation.zip` was generated and tested in the originating ChatGPT session. **Executable code and tests are distributed via that ZIP and not included in this research-note commit**. Its authoring environment passed **44 offline tests**, checksum verification, clean extraction and an expected zero-Docker preflight HOLD. The real Colima QEMU result is pending.

R3877.49 reuses the exact existing pinned cached Alpine/QEMU image identities and SHA-256 bytes. With explicit local authorization it recreates the R3877.47 stopped-container isolation (read-only copy attempt, separately authorized ephemeral writable layer only on a proven read-only-rootfs Docker copy error, exact-ID cleanup, image unchanged, no network/mounts/privileges). It executes known-good ARMv7 BusyBox applets under `qemu-arm-static -strace -0 /bin/busybox` and exports **only bounded syscall names, counts and ENOSYS/unknown-record counts**, not raw paths, pointers or arguments. A trace-free or failed applet is HOLD. QEMU 10.0.4 user mode translates syscalls through the host, so a PASS is observation of QEMU syscall behaviour only, **never Linux 3.0.35-lab126 compatibility**.

Extract the ZIP under `~/Downloads/pw3-r3877-49` and run:

```zsh
cd ~/Downloads/pw3-r3877-49
shasum -a 256 -c SHA256SUMS_R3877_49.txt
python3 -B -m unittest -q test_r3877_49.py
setopt pipefail
python3 -B pw3_r3877_49_qemu_syscall_trace.py \\
  --authorize-offline-qemu \\
  --allow-disposable-writable-layer | tee r3877_49_runtime.json
print "R3877_49_EXIT_CODE=$?"
```

Only use the writable-layer flag if separately authorized; it is never an invitation to mutate the parent image. Expected **possible** narrow successful classification is `PASS_QEMU_ARMV7_SYSCALL_TRACE_OBSERVATION_ONLY`. An unrecognised QEMU trace or Docker environmental error must HOLD; the original private R13 stage, stock kernel, bootloader, firmware and recovery remain untouched.

Documentation: https://www.qemu.org/docs/master/user/main.html . No GitHub CI runtime claim is made for this local artifact.
