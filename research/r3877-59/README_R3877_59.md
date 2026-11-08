# PW3-OS R3877.59 — ARMv7 musl pthread/TLS runtime (Mac QEMU only)

**Research and education only. The actual Kindle remains `NOT_BOOTABLE`.** This experiment does not access the Kindle, modify its filesystem/firmware, install an ARM binary on it, change host binfmt, or use guest networking or mounts.

## What R58 established

The Mac's R3877.58 read-only injection attempt returned HOLD for an expected read-only Docker copy refusal. Re-running with explicit `--allow-disposable-writable-layer` passed: pinned QEMU ran actual Alpine ARMv7 BusyBox startup, ash `printf`, stat, date and a 16-byte `/dev/urandom` read; original image was unchanged and all temporary containers removed. QEMU traces included `statx` and `clock_gettime64`, **which used the host Colima Linux kernel, not the physical Kindle's Linux 3.0.35 kernel**.

## R59 probe and limitations

`pw3_r3877_59_armv7_probe.elf` is a **new and deliberately restricted test executable intended only for the disposable QEMU guest**. It was cross-compiled for ARMv7 EABI5 hard-float with Clang 17 and lld using the accompanying `pw3_r3877_59_armv7_probe.c` (`--target=armv7-alpine-linux-musleabihf`, freestanding PIE, no external cross sysroot). The binary has an ELF `PT_INTERP` of `/lib/ld-musl-armhf.so.1`, `PT_TLS`, and undefined imports for `__libc_start_main`, `pthread_create`, `pthread_join`, `__aeabi_read_tp`, `getrandom`, `getentropy`, and related libc functions. It has no `DT_NEEDED` entries; whether the exact Alpine loader resolves its imports is deliberately **untested** and could cause HOLD. This is not a reproduced Alpine package build and **not** a kernel-ready binary.

The expected program prints fixed markers *only if* pthread create/join succeeds, a child sees its own 100→107 TLS change while the parent retains 100, and `getrandom` plus `getentropy` succeed on the QEMU host kernel. No random data are printed. The runner independently executes the untraced control, then QEMU `-strace` and requires observed `clone` and `getrandom` syscall names. The trace may include unclassified lines: no program/trace attribution is claimed for those lines.

This **does not** test `getrandom` returning `ENOSYS`, source-to-installed-musl-binary equivalence, actual Kindle ARM TLS behavior, physical kernel syscall dispatch, recovery, or full Alpine boot compatibility. The target-specific old-kernel ABI gap remains after a hypothetical R59 PASS.

## Bundle validation on Mac

```zsh
mkdir -p ~/Downloads/pw3-r3877-59
unzip -oq ~/Downloads/pw3-r3877-59-qemu-pthread-tls.zip -d ~/Downloads/pw3-r3877-59
cd ~/Downloads/pw3-r3877-59
shasum -a 256 -c SHA256SUMS_R3877_59.txt
python3 -B -m unittest -q test_r3877_49_3.py test_r3877_59.py
```

Expected: **108 host-only tests**, all OK. All tests are synthetic and execute no Docker or ARM code.

### Default is fail-closed, zero Docker

```zsh
python3 -B pw3_r3877_59_qemu_pthread_tls.py > r3877_59_preflight.json
printf 'R3877_59_PREFLIGHT_EXIT_CODE=%s\n' "$?"
```

Expected: `HOLD` / exit 2 with `docker_used=false`.

### Authorised off-Kindle run

```zsh
setopt pipefail
python3 -B pw3_r3877_59_qemu_pthread_tls.py \
  --authorize-offline-qemu \
  --allow-disposable-writable-layer \
  | tee r3877_59_result.json
printf 'R3877_59_EXIT_CODE=%s\n' "$?"
```

The writable fallback is explicitly authorized **only after** Docker reports the expected read-only copy failure, and applies to a disposable container layer, never the pinned original image. The tool uses the unchanged, byte-pinned R49.3 runner's ARM64 helper image and QEMU hash pins, BusyBox hash pin, platform checks, and networkless/unprivileged guest isolation. It injects exactly the QEMU executable and the one hash-pinned ARM probe into the stopped guest, verifies probe readback, checks the exact allowlisted Docker diff, then starts QEMU. It removes/attests all containers and rechecks the parent image. If any check fails, the output is HOLD. No image pulls/builds, mounts, guest networking, or container privilege elevation.

**Possible** narrow success (NOT observed yet):

`PASS_PINNED_QEMU_ARMV7_MUSL_PTHREAD_TLS_AND_HOST_GETRANDOM_ONLY`

Note: The host compiler and `lld` build environment are not pinned or reproducibly attested. This is **not** a run-time provenance equivalence proof for the Alpine downstream musl loader.

## After the test

Share only `r3877_59_result.json` and `R3877_59_EXIT_CODE`; do **not** install the probe on the Kindle or modify its boot chain. If the ELF fails due to unresolved imports, preserve the HOLD; the next test should correct musl's dynamic-link setup from source without relaxing isolation. If pthread/TLS passes, proceed separately with a controlled old-kernel `ENOSYS` simulation and a recovery gate. `NOT_BOOTABLE` remains immutable.
