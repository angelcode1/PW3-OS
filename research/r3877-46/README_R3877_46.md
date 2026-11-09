# PW3-OS R3877.46 — fail-closed `docker cp` rootfs-policy diagnostic

**Research / educational purposes only. `NOT_BOOTABLE` is immutable. No Kindle access or firmware writes.**

## Why another harness

User-reported R3877.45 returned exit 2 / `HOLD`, `DOCKER_COMMAND_FAILED:cp`, and `guest_containers_created=1`, with QEMU and BusyBox bytes already pinned. `authorized_qemu_execution_performed=false` and `runtime_probes={}`. Since the helper and BusyBox extraction `docker cp` commands had already succeeded, the failure was in the subsequent **copy of the pinned QEMU binary into the first stopped `--read-only` guest**. This inference is based on the harness's program order and selected output, not on captured Docker stderr.

The R3877.46 default first **reproduces this read-only guest copy** and records the *actual* Docker error family, exit code, error-output SHA-256 and length. Raw Docker stderr, local paths, usernames and identifiers are not published. An exit code alone is never taken as proof of read-only rootfs denial.

If and only if the actual copy error matches an explicit read-only-rootfs pattern **and** the operator supplied a separate `--allow-disposable-writable-layer` flag, the harness can test a more compatible isolation design: an ephemeral **writable container layer** over the unchanged cached parent image. That is a **deliberate relaxation of the guest's read-only-rootfs property**, not a permission to modify the original image, the Kindle, host filesystem, volumes, devices or network. The writable layer is in a uniquely identified disposable container; it is removed after the probe. No `docker commit`, `image prune`, new image, host volume or privilege is used.

The fallback guests remain networkless, unprivileged (`65534:65534`), `--cap-drop ALL`, `--security-opt no-new-privileges`, 256 MB memory / 64 PIDs, and no volumes, host devices or bind mounts. Docker inspect is checked before starting. The QEMU binary is copied only into each stopped guest and verified via SHA-256 readback. On the writable path, Docker `diff` before and after execution must contain only the injected emulator file and its ancestor directories; any other filesystem modification causes HOLD. Cleanup uses exact recorded container IDs and verifies that each is gone. The parent image ID must match the pinned R3877.45 observation before and after the test.

The test reuses the previously reported cached image names, Alpine parent ID, pinned helper repository digest, QEMU SHA-256 and BusyBox SHA-256; no pulls. It tests QEMU `--version`, BusyBox `--help` (**not** `-help`), BusyBox `true`, and BusyBox `uname -m` (expected `armv7l`). It does not validate complete musl compatibility, the PW3's old Linux 3.0.35 kernel, the private R13 stage, KOReader, independent boot or recovery.

## On macOS with Colima/Docker

Unzip `pw3-r3877-46-readonly-cp-gate.zip` to `~/Downloads/pw3-r3877-46`; run from that directory:

```zsh
cd ~/Downloads/pw3-r3877-46
shasum -a 256 -c SHA256SUMS_R3877_46.txt
python3 -B -m unittest -q test_r3877_46.py

# Default: no Docker activity. HOLD and exit 2 are expected.
python3 -B pw3_r3877_46_readonly_cp_gate.py > r3877_46_preflight.json
print "R3877_46_PREFLIGHT_EXIT_CODE=$?"

# Step 1: explicitly authorize offline Docker probing of a read-only guest.
setopt pipefail
python3 -B pw3_r3877_46_readonly_cp_gate.py \
  --authorize-offline-qemu | tee r3877_46_readonly.json
print "R3877_46_READONLY_EXIT_CODE=$?"
```

If the result's `read_only_copy_probe.classification` is `READONLY_ROOTFS_COPY_REJECTED`, then the default correctly stops with `READONLY_COPY_REJECTED_WRITABLE_FALLBACK_NOT_AUTHORIZED`. At this point the operator may **separately** opt in to disposable writable-layer testing:

```zsh
python3 -B pw3_r3877_46_readonly_cp_gate.py \
  --authorize-offline-qemu \
  --allow-disposable-writable-layer | tee r3877_46_runtime.json
print "R3877_46_RUNTIME_EXIT_CODE=$?"
```

**Do not use the extra flag if the error was unclassified.** In that case, share `r3877_46_readonly.json` for the next narrow diagnosis; do not modify Docker or relax security settings. If the read-only copy succeeds, the first command itself runs all four read-only QEMU probes and no writable fallback is needed.

A result of `PASS_ARM32_BUSYBOX_QEMU_ONLY` with exit 0 requires all four probes, verified stop states, allowed-only filesystem changes (if using writable fallback), cleanup, and unchanged parent image. It is **not** a boot-ready signal. Other outcomes must keep `NOT_BOOTABLE`. No Kindle SSH or physical-device work occurs.

## Verified scope

The Python implementation and 34 synthetic/host-only unit tests were executed in the authoring environment. The ZIP is SHA-256 manifested and independently re-extracted and tested. **Actual Colima QEMU execution was not performed in the authoring environment.** The linked GitHub workflow must only run the offline unit tests and preflight, never Docker or Kindle operations.
