# R3877.50 — Public Lab126 ARM syscall source crosswalk for observed QEMU applets

**Research/educational only. Immutable `NOT_BOOTABLE`.** No Kindle SSH, physical-device commands, firmware writes, boot, ARM emulation, Docker, mounts, package installation or source compilation. This is a **host-only public source audit**.

## What R3877.49.3 established

The user reported exit 0, `PASS_QEMU_SYSCALL_NAMES_AND_UNTRACED_APPLET_CONTROLS_ONLY`. Exact untraced `true`, `uname -m`, and echo controls passed. Three QEMU user-mode traces included **55 syscall records**, with 14 distinct names and no observed `ENOSYS` or unknown calls in this limited workload. Some traced stdout lines still had **unverified provenance**; the untraced applet outputs were validated independently. QEMU user-mode success is **not** Linux 3.0.35 kernel syscall success.

## New public source crosswalk

In the public GitHub mirror `katadelos/linux-3.0.35-lab126` at **commit `7ac2585f384573da8cbdcc987a3503e2e6ff1fb4`**, this project observed:

- `arch/arm/include/asm/unistd.h` Git blob `2c04ed5efeb50707ac3353958434d37691841839`, identical to the already pinned `torvalds/linux` upstream `v3.0` ARM header.
- `arch/arm/kernel/calls.S` Git blob `80f7896cc0164ad6f74469f1e777b90c1f306443`.

All 14 observed names have an ARM EABI number in that header, with the corresponding non-placeholder entry in the **public source** `calls.S`. The older `*32` user/group syscall names map to generic `sys_getuid`, `sys_getgid`, `sys_setuid`, and `sys_setgid` entries as expected; `uname` maps to `sys_newuname`. The report records exact numbers, names, and entries, but **does not assert** that this source tree matches the installed Kindle kernel binary, that the particular kernel configuration builds every entry, that runtime dispatch succeeds or that musl behaves correctly on it.

The Python analyzer verifies both Git blob identities **before** parsing and requires the exact R49.3 input result and observed syscall sets. It never downloads source or runs the guest. Source mismatches/changed runtime evidence cause `HOLD` (exit 2). The initial repository-source observation is recorded separately in `PUBLIC_LAB126_MIRROR_SOURCE_SELECTED_OBSERVATION.json` and must not be mistaken for an independently run Mac diagnostic.

## Run the pinned source check on macOS (no Docker)

Extract this release to `~/Downloads/pw3-r3877-50`, verify checksums, and run unit tests:

```zsh
cd ~/Downloads/pw3-r3877-50
shasum -a 256 -c SHA256SUMS_R3877_50.txt
python3 -B -m unittest -q test_r3877_50.py

# Without inputs: expected exit 2/HOLD and absolutely no network or device access.
python3 -B pw3_r3877_50_public_lab126_syscall_crosswalk.py
```

Fetch only the two public source files to a separate Mac-local directory, using HTTPS certificate verification and the **exact commit**, never a floating branch:

```zsh
mkdir -p source
base='https://raw.githubusercontent.com/katadelos/linux-3.0.35-lab126/7ac2585f384573da8cbdcc987a3503e2e6ff1fb4'
curl --fail --location --silent --show-error --retry 0 \
  "$base/arch/arm/include/asm/unistd.h" -o source/unistd.h
curl --fail --location --silent --show-error --retry 0 \
  "$base/arch/arm/kernel/calls.S" -o source/calls.S

setopt pipefail
python3 -B pw3_r3877_50_public_lab126_syscall_crosswalk.py \
  --r49-report ~/Downloads/pw3-r3877-49-3/r3877_49_3_runtime.json \
  --header source/unistd.h \
  --calls source/calls.S | tee r3877_50_result.json
print "R3877_50_EXIT_CODE=$?"
```

If any source fetch or pin fails, STOP and preserve the `HOLD`; do not relax hashes or use alternate unpinned sources. A successful result is only `PASS_PINNED_PUBLIC_LAB126_SOURCE_SYSCALL_CROSSWALK_ONLY`, and the report always retains `NOT_BOOTABLE`.

## What remains a real blocker

The **exact running Kindle kernel build and its actual syscall table are not attested** to this public mirror. Conditional build flags, kernel backports, syscall argument and return-value semantics, threading/TLS, time64 fallback, entropy, openat/stat operations, suspend/resume, KOReader's separate glibc soft-float runtime and recovery remain unverified. No deletion, boot action or on-device binary execution is authorised. The next useful gate is an evidence-led, separately reviewed source/build-provenance and musl-fallback risk matrix, not an image flash.

## Verification boundary

Synthetic unit tests and no-input preflight run entirely offline. GitHub Actions is host-only, does **not** download the public kernel or inspect a local running Kindle, and does not promote any source-only result into a target-runtime PASS.
