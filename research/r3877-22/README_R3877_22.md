# PW3 R3877.22 — Pinned upstream Linux v3.0 ARM syscall source binding

**Research and educational purposes only. `NOT_BOOTABLE` is immutable.** This audit does not contact the Kindle; it neither installs binaries nor touches any partition, mount, bootloader, or the original R13 stage. It does **not** test runtime syscalls.

## What R3877.21 actually established

The user-reported R3877.21 matrix returned `PASS_VERSION_CONFIG_RISK_MATRIX_ONLY` with `parsed_arm_syscall_definitions=0`. The actual Kindle is reported as `3.0.35-lab126`, `armv7l`, ARM TLS available, basic kernel configuration flags enabled, and live ext3 root backed by `mmcblk0p1`. R3877.21 did not inspect any actual ARM `unistd.h` source, musl's exact fallback implementation or the vendor syscall dispatch table.

## R3877.22 scope

This host-only script requires an explicitly downloaded **upstream Linux v3.0** `arch/arm/include/asm/unistd.h` whose Git blob SHA-1 matches GitHub's exact `torvalds/linux` `v3.0` file, `2c04ed5efeb50707ac3353958434d37691841839`. Git uses SHA-1 of `b'blob '+ascii(len(data))+b'\0'+data`, not raw-file SHA-1. The validator checks that identity before parsing syscall name/number macros, then crosschecks a baseline of ARM EABI syscall numbers. It records whether the 20 core names are present and whether seven newer names exist in the *upstream v3.0 reference*. Upstream source identity is not vendor kernel source provenance.

**The upstream header is not included in this ZIP.** Obtain it on your Mac from the official Linux GitHub repository using HTTPS; keep the exact bytes. No network request comes from this Python code.

## On your Mac

```sh
mkdir -p ~/Downloads/pw3-r3877-22
unzip -oq ~/Downloads/pw3-r3877-22-upstream-syscall-source.zip \
  -d ~/Downloads/pw3-r3877-22
cd ~/Downloads/pw3-r3877-22
shasum -a 256 -c SHA256SUMS_R3877_22.txt
python3 -B -m unittest -q test_r3877_21.py test_r3877_22.py

# Host network access ONLY. Abort on certificate/HTTP errors; never curl -k.
curl -fLsS --retry 0 --connect-timeout 10 \
  'https://raw.githubusercontent.com/torvalds/linux/v3.0/arch/arm/include/asm/unistd.h' \
  -o upstream-linux-v3.0-arm-unistd.h

set -o pipefail
python3 -B pw3_r3877_22_upstream_source_binding.py \
  upstream-linux-v3.0-arm-unistd.h \
  R3877_21_USER_REPORTED_INPUT.json \
  | tee r3877_22_result.json
printf 'R3877_22_EXIT_CODE=%s\n' "$?"
```

Expected classification if the exact header downloads and passes verification: `PASS_PINNED_UPSTREAM_ARM_SOURCE_NAMES_ONLY`. Any missing input, modified/mismatched source blob, inconsistent device metadata, or malformed syscall definitions emits `HOLD`, exit 2. The test suite itself uses synthetic ARM source fixtures and cannot prove that a public header was fetched.

## Interpretation, bounds and next steps

- The `arm_eabi_number` is a v3.0 **source definition**, not proof of kernel dispatch, presence of vendor backports, or successful target execution.
- The absence of a post-v3.0 name in the upstream v3.0 header does not prove the syscall is missing in `3.0.35-lab126`.
- Musl >=1.2 time64 syscalls require an exact package/version source fallback audit, especially `clock_gettime64` and `futex_time64`; this is **not** established by the upstream header.
- KOReader's existing glibc soft-float build should not be loaded in the hard-float musl Alpine environment. Static symbol candidates previously identified do not prove dynamic binding.
- A safe recovery/rollback has not been verified; `NOT_BOOTABLE` remains enforced.

Source references:
- https://github.com/torvalds/linux/blob/v3.0/arch/arm/include/asm/unistd.h
- https://raw.githubusercontent.com/torvalds/linux/v3.0/arch/arm/include/asm/unistd.h
- https://git-scm.com/book/en/v2/Git-Internals-Git-Objects
