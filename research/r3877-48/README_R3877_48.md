# PW3-OS R3877.48 — Cached BusyBox PT_INTERP / pinned musl-loader linkage audit

**Research and education only. `NOT_BOOTABLE` remains immutable.** This milestone runs **no ARM guest code, no Kindle commands, and no firmware writes**. It does not claim Linux `3.0.35-lab126` syscall support.

## Grounded starting evidence

The user-reported R3877.47 Colima QEMU test passed ARMv7 BusyBox `true`, `uname -m` (`armv7l`) and the exact echo marker; it also observed that forcing target `argv[0]` with QEMU `-0 /bin/busybox` restored normal BusyBox help. GitHub records this as `R3877_47_USER_REPORTED_SELECTED_EVIDENCE.json`. Those applet observations do **not**, without a static ELF dependency audit, prove that a musl dynamic interpreter was needed or loaded: BusyBox could be statically linked. The prior R3877.24-25 research pinned the SHA-256 of the candidate musl loader in the unchanged cached Alpine image to `2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990` and compared its bytes with a signed public Alpine musl package.

## What the new check does

1. **Default preflight: zero Docker calls**, exit 2 / HOLD.
2. With explicit authorization, inspect the already cached Alpine image for exact image ID `sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a`, platform Linux ARMv7. No image pull.
3. Create exactly one **stopped** temporary container with `--platform linux/arm/v7 --pull never --network none --entrypoint /bin/true`. Inspect it to ensure it is not running, uses the pinned image, has no host binds, devices or mounts and is nonprivileged.
4. Copy only `/bin/busybox` and `/lib/ld-musl-armhf.so.1` from that stopped container to auto-deleted host temporary files. `docker cp -L` follows the loader symlink **inside the stopped container**. Verify the previously observed BusyBox SHA-256 `df4dd71f...e930c` and loader SHA-256 `2acf3c82...778990` (full values pinned in source).
5. Strictly parse ELF32 little-endian ARM EABI5 hard-float program headers, requiring the BusyBox `PT_INTERP` to be **exactly** `/lib/ld-musl-armhf.so.1`, one `PT_DYNAMIC`, and the matching loader to be an ELF32 ARM ET_DYN without its own PT_INTERP. Reject corrupt ELF headers, unsafe strings, wrong ABI and any byte mismatch.
6. Remove the exact stopped container ID, verify absence, and re-check the immutable parent image ID. A cleanup failure or any mismatch is HOLD.

A possible pass is `PASS_PINNED_BUSYBOX_MUSL_PT_INTERP_LINKAGE_ONLY`. In combination with R3877.47, this would be evidence that QEMU ran a dynamically linked BusyBox requiring the pinned musl loader **on the Colima host**. The R3877.48 tool **does not run the loader**, authenticate the historical compiler, prove GNU/glibc KOReader runtime compatibility, or validate the actual Kindle vendor kernel. If BusyBox has **no** `PT_INTERP`, the tool reports HOLD rather than falsely asserting a dynamic-loader result; this would mean a separate loader-specific runtime test is needed.

## macOS / zsh

Download and extract `pw3-r3877-48-musl-interpreter-audit.zip` to `~/Downloads/pw3-r3877-48`, then:

```zsh
cd ~/Downloads/pw3-r3877-48
shasum -a 256 -c SHA256SUMS_R3877_48.txt
python3 -B -m unittest -q test_r3877_48.py

# Preflight deliberately invokes NO Docker and returns 2/HOLD.
python3 -B pw3_r3877_48_musl_interp_audit.py > r3877_48_preflight.json
print "R3877_48_PREFLIGHT_EXIT_CODE=$?"

# Explicitly authorized stopped-image audit; NO ARM execution, no Docker guest start.
setopt pipefail
python3 -B pw3_r3877_48_musl_interp_audit.py \
  --authorize-stopped-image-audit | tee r3877_48_result.json
print "R3877_48_EXIT_CODE=$?"
```

Share `r3877_48_result.json` and the exit code. If it returns HOLD, leave the cached image unchanged and use the specific `error_category` to guide the next diagnostic. Do not switch interpreters, modify the original image, install packages on the Kindle or attempt boot.

## Tested scope

The authoring environment ran **27 host-only synthetic unit tests**, checked that default preflight performs no Docker operations, and verified the release ZIP and manifest. No Colima/Docker runtime access was available in the authoring environment. GitHub Actions must run only the host Python tests and no-Docker preflight; it must never run QEMU or interact with the Kindle.
