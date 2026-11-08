# PW3-OS R3877.61 — Direct musl `getentropy()` response to `getrandom` ENOSYS

**Research and education only. Mac/Colima/QEMU only. Physical Kindle `NOT_BOOTABLE`.** No Kindle SSH or physical-device ARM execution, no firmware write, no boot or recovery actions. This cannot prove actual vendor Linux `3.0.35-lab126` behavior.

## Already verified

The user-reported R3877.60.4 Mac runtime result passed, exit 0: the AArch64 launcher independently attested that host `getrandom` and `statx` were denied with ENOSYS, the ARM guest `getrandom` returned ENOSYS, and guest `statx` succeeded under QEMU 10.0.4 emulation. Pinned QEMU, BusyBox, Alpine image and container cleanup were verified. But R59's original ARM source **never called `getentropy()` if `getrandom()` failed**.

Upstream musl 1.2.6 `src/misc/getentropy.c` (Git blob SHA1 `651ea95f14310cda867b88378a0aedf2225d4462`) calls `getrandom` and retries only on `EINTR`; on `ENOSYS` it returns `-1` preserving errno. It does **not** implement a `/dev/urandom` fallback. `src/linux/getrandom.c` (Git blob SHA1 `6cc6f6b047c18c9c8c564b5ece3f80a2f2b1f65f`) wraps the syscall directly.

## What this test does

Retain *byte-for-byte* the QEMU and container isolation logic, pinned AArch64 seccomp launcher SHA-256 `b9a433e2397e27c4cbdd2aade7b57cc39af4e6f36b37a4f204833b282a987b02` and historical R49.3 runner. Add one new freestanding, dynamically linked ARMv7 hard-float PIE with `PT_INTERP=/lib/ld-musl-armhf.so.1`, `DT_NEEDED=libc.so`, and `PT_TLS`. It performs pthread/TLS checks, then calls **both** `getrandom` and `getentropy` with the host `getrandom` filter installed. Each must return `-1`, `errno=ENOSYS`; no successful random byte output is accepted. The untraced guest output must match exactly these four lines:

```
R61_PASS_ARMV7_PTHREAD_TLS
R61_OBS_GETRANDOM_ENOSYS
R61_OBS_GETENTROPY_ENOSYS
R61_PASS_QEMU_MUSL_ENTROPY_ENOSYS_ONLY
```

The separate QEMU trace must show **exactly two** guest `getrandom` calls, both ENOSYS. Guest `statx` must still succeed under QEMU internal fallback, while the host launcher verifies raw host `statx` ENOSYS. Each control and trace runs with a separate checked container. Files are never copied into an image, only ephemeral guests; image and anonymous-volume cleanup are verified. Default invocation returns HOLD/exit 2 without invoking Docker. No host mount, privileged guest, guest networking, host binfmt change or Kindle actions.

**A successful runtime result is narrowly `PASS_QEMU_MUSL_GETENTROPY_ENOSYS_AND_GUEST_STATX_EMULATION_ONLY`.** It does not verify a secure entropy fallback, nor runtime behavior on Kindle Linux 3.0.35. It actually demonstrates that musl's `getentropy` has *no* internal fallback to `/dev/urandom` when the kernel returns ENOSYS. Application-specific entropy behavior, time64 legacy fallback, vendor syscalls and recovery remain unverified.

## Mac commands

```zsh
mkdir -p ~/Downloads/pw3-r3877-61
unzip -oq ~/Downloads/pw3-r3877-61-getentropy-enosys.zip -d ~/Downloads/pw3-r3877-61
cd ~/Downloads/pw3-r3877-61
shasum -a 256 -c SHA256SUMS_R3877_61.txt
python3 -B -m unittest -q test_r3877_49_3.py test_r3877_60.py test_r3877_60_1.py test_r3877_60_2.py test_r3877_60_3.py test_r3877_60_4.py test_r3877_61.py

# Default HOLD, zero Docker:
python3 -B pw3_r3877_61_qemu_getentropy_enosys.py > r3877_61_preflight.json
printf 'R3877_61_PREFLIGHT_EXIT_CODE=%s\n' "$?"

# Explicit Mac-only QEMU test, same known read-only refusal gate and disposable fallback:
setopt pipefail
python3 -B pw3_r3877_61_qemu_getentropy_enosys.py \
  --authorize-offline-qemu --allow-disposable-writable-layer \
  | tee r3877_61_result.json
printf 'R3877_61_EXIT_CODE=%s\n' "$?"
```

Stop on HOLD. Keep the JSON report. No Kindle commands.

## Build provenance limitation

The new ARM ELF was linked on a host with clang/lld; an empty SONAME `libc.so` anchor was used *only* at link time to populate `DT_NEEDED`. The anchor is absent from the release and is never copied into the guest. The binary SHA-256 is `ee6b5b8d175618afc46a15cf4451e070c1e67f5da3213150d0882188354acfa2`. This is a new research test program, not a reproducible rebuild of patched musl or an installation artifact for the Kindle.
