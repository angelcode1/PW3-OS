# R3877.45 — Direct stopped-container QEMU test; no Docker commit

**For research and educational purposes only. `NOT_BOOTABLE` remains immutable.**

## Why this milestone exists

User-reported R3877.44 Colima output exited 2/HOLD with `DERIVED_PLATFORM_OR_ID_MISMATCH`. It confirmed the ELF32 ARM BusyBox hash `df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c`, but **no QEMU/ARM guest was executed**; its temporary image and containers were removed, and the parent image was unchanged. The exact reason for the derived-image mismatch is **unknown** without the original Docker inspect values. Do not assume the problem was a missing `Variant` or retag the parent to make the check pass. Historical R3877.5 and R3877.6 failures remain recorded; only the R3877.6 captured stderr `-help: applet not found` supports identifying the historical single-hyphen BusyBox argument error.

R3877.45 avoids the `docker commit` platform identity dependency *entirely*: it runs QEMU explicitly inside independently created, initially stopped disposable ARMv7 containers based on the **original pinned image**. It copies the already cached, pinned AArch64 QEMU into each stopped container. It never commits, imports, retags, builds, or pulls an image; never uses binfmt registration; and never mounts the user's filesystem or touches a Kindle. It does **not** relax image/key/digest hashes or the read-only and privilege checks.

## Workflow

- Default: read-only Python preflight with **no Docker calls**; returns HOLD/exit 2.
- Explicit authorization: validates an ARM64 Colima Docker server, the local tagged source Alpine `linux/arm/v7` image and original ID, the locally cached helper digest, the QEMU SHA256 and ARM64 ELF, and the BusyBox SHA256 and ELF32 ARM hard-float EABI flags.
- It obtains all binaries via `docker cp` from stopped containers. It verifies each new test container's actual original image ID, stopped state, exact QEMU entrypoint/argv, non-root UID, read-only rootfs, disabled network, absence of bind/device mounts, dropped capabilities, `no-new-privileges`, and memory/PID limits **before and after copying QEMU**. QEMU is read back from the guest before execution and compared with the pin.
- Four explicit short probes: pinned `qemu-arm --version` (AArch64 control), `qemu-arm /bin/busybox --help`, `qemu-arm /bin/busybox true`, and `qemu-arm /bin/busybox uname -m`. The last probe requires exact `armv7l`; unexpected outputs return HOLD. No guest shell or services, no guest network.
- Only the six newly created temporary containers are removed. Their IDs are shown if cleanup fails; no global `prune`. The original tagged image ID is rechecked. `PASS_ARM32_BUSYBOX_QEMU_ONLY` is permitted only if all four probes pass, cleanup succeeds, and original image ID matches. Otherwise exit 2/HOLD.

**Important:** Docker's ability to `cp` into a stopped `--read-only` container can depend on its runtime implementation. If Docker rejects it, `DOCKER_COMMAND_FAILED:cp` is a legitimate HOLD. **Do not turn off `--read-only`, add `--privileged`, run host emulation registration, or bypass the hash/identity checks.** Instead retain the error for a follow-up design.

## Run on macOS with Colima already started

Unzip the separately supplied `pw3-r3877-45-direct-stopped-guest.zip` in the user's Downloads folder:

```zsh
mkdir -p ~/Downloads/pw3-r3877-45
unzip -oq ~/Downloads/pw3-r3877-45-direct-stopped-guest.zip -d ~/Downloads/pw3-r3877-45
cd ~/Downloads/pw3-r3877-45
shasum -a 256 -c SHA256SUMS_R3877_45.txt
python3 -B -m unittest -q test_r3877_45.py
python3 -B pw3_r3877_45_direct_stopped_guest.py > r3877_45_preflight.json
rc=$?
print "R3877_45_PREFLIGHT_EXIT_CODE=$rc"  # expected 2 / HOLD, no Docker use

setopt pipefail
python3 -B pw3_r3877_45_direct_stopped_guest.py --authorize-offline-qemu | tee r3877_45_runtime.json
rc=$?
print "R3877_45_RUNTIME_EXIT_CODE=$rc"
```

The Python `test_r3877_45.py` tests use mocks, including one simulated full Docker cycle; this does not claim a real local ARM execution. Exit 0 **only** means `PASS_ARM32_BUSYBOX_QEMU_ONLY`; an exit 2 retains HOLD and the JSON reports the failing stage. If cleanup fails, inspect only the recorded `container_ids_requiring_manual_review` and avoid bulk deletion. Source image, private R13 stage, Kindle, firmware and boot are untouched by design.

## Separate outstanding gates

R3877.45 PASS does **not** verify the vendor Kindle Linux 3.0.35 syscall/TLS ABI, Alpine musl/target recovery, KOReader compatibility runtime, physical PW3 device adapter, initial ramdisk, services, independent rootfs boot, or stock recovery. `NOT_BOOTABLE` persists even after PASS. Historical published repository package versions from R3877.43 remain candidates, not authenticated historical installed build-tool versions.

## Verification boundary

The source package was checked with offline unit tests, synthetic Docker lifecycle mocks, clean ZIP extraction and SHA256 manifest verification in the authoring environment. This environment has no Docker daemon, Colima or Kindle; real runtime output is pending the user's own authorized local test. GitHub Actions only runs host/static checks, never Docker, physical device access or QEMU guests.
