# R3877.47 — ARMv7 BusyBox positive applet probes + QEMU argv0 comparison

**Research / educational only. Immutable `NOT_BOOTABLE`. No Kindle, firmware, rootfs, boot, privileged Docker, host bind mounts or network.**

## Why this changes the gate

The user's R3877.46 Colima runs (selected JSON in `R3877_46_USER_REPORTED_SELECTED_EVIDENCE.json`) confirm that read-only `docker cp` fails and that the separately approved disposable writable fallback executed the pinned QEMU helper (`--version` PASS). The subsequent BusyBox invocation with Docker-inspected argument vector `/bin/busybox --help` returned **exit 127** and exactly `-help: applet not found\n`. It is an applet-dispatch response, **not** a successful `--help`, no proof of a complete musl runtime, and not evidence of a missing loader. The original R3877.46 historical HOLD is unchanged.

BusyBox's compiled-in multicall entry point and argv0 dispatch can influence help behaviour. Historical BusyBox source contains a known case where `--help` is rendered `-help: applet not found` when `CONFIG_BUSYBOX` is disabled; however **the independently inspected Alpine 3.24-stable upstream** `main/busybox/busyboxconfig` contains `CONFIG_BUSYBOX=y` (Git blob `f94784573735b83ad7129c92ef37c170a676bf8e`). This upstream config is not authenticated build provenance for the **exact extracted** `/bin/busybox` binary. Another hypothesis is QEMU/argv0 handling. Neither hypothesis is proven by the 127 result alone.

R3877.47 keeps the R3877.46 safety gate unchanged: the operator must explicitly authorise offline QEMU; optional writable fallback requires an additional flag **and** a freshly observed read-only-rootfs `docker cp` error. All guest images are verified against pinned identities and platform, and guests are stopped before QEMU injection, SHA-256 readback, and policy checks. For writable ephemeral layers, only injected QEMU and ancestor-directory changes are allowed before and after execution. All containers are removed by exact ID and checked absent; the original parent image ID is checked unchanged. No new derived image, network, host volume, device, or firmware writes are used.

### Revised test sequence (six separate disposable guest containers)

1. Native pinned QEMU `--version` (non-ARM guest code by itself)
2. `/bin/busybox true` (must exit 0 silently)
3. `/bin/busybox uname -m` (must emit exactly `armv7l\n`)
4. `/bin/busybox echo PW3_R3877_47_ARMV7_QEMU_OK` (must emit the exact marker)
5. `/bin/busybox --help` (diagnostic; success or **exact historical** known dispatch anomaly)
6. `qemu-arm-static -0 /bin/busybox /bin/busybox --help` (diagnostic control to force argv0)

The **positive ARM32 execution gate** requires probes 2–4 to succeed, strict Docker-verified argv for each, verified exit state, no unauthorized filesystem changes, successful cleanup and unchanged parent. The help probes must both be accounted for. A help probe with exit 127 and *exact* known output `-help: applet not found\n` is classified as `KNOWN_BUSYBOX_APPLET_DISPATCH_ANOMALY`, **not** a help PASS, and does not erase independently successful applet evidence. Any other unexpected help failure is a HOLD. If the core applets succeed, a narrow `PASS_ARM32_BUSYBOX_APPLETS_QEMU_ONLY` is possible even when help is separately anomalous, with `immutable_hold=NOT_BOOTABLE` unchanged. Any core applet failure is a HOLD.

This intentionally does not attest the target PW3 Linux `3.0.35-lab126` kernel, loader startup across all syscalls, TLS, glibc KOReader compatibility, recovery, or boot.

## macOS / Colima commands

After extracting the ZIP, inside the extracted directory:

```zsh
cd ~/Downloads/pw3-r3877-47
shasum -a 256 -c SHA256SUMS_R3877_47.txt
python3 -B -m unittest -q test_r3877_47.py

# Default: NO Docker; expected exit 2 and HOLD.
python3 -B pw3_r3877_47_qemu_applet_argv0.py > r3877_47_preflight.json
print "R3877_47_PREFLIGHT_EXIT_CODE=$?"

# Explicit local Colima execution. The second opt-in is warranted ONLY after
# the prior R3877.46 read-only rejection and is re-gated this run.
setopt pipefail
python3 -B pw3_r3877_47_qemu_applet_argv0.py \
  --authorize-offline-qemu \
  --allow-disposable-writable-layer | tee r3877_47_runtime.json
print "R3877_47_RUNTIME_EXIT_CODE=$?"
```

Expected output cannot be promised before a real run. A PASS carries the narrow classification above and exit 0; unexpected results return `HOLD` and exit 2. Report `runtime_probes` and `help_diagnostics` including the forced-argv0 comparison. **Do not** force device boot, change QEMU binfmt registrations, waive hash pins or perform blanket image pruning.

## Verification boundary

The authoring environment ran Python unit tests and inspected release ZIP and SHA-256 manifest. It did **not** execute Colima, Docker or the ARMv7 binary. The GitHub Actions workflow runs only Python synthetic tests and the no-Docker preflight. The observed R3877.46 data remain user-reported.
