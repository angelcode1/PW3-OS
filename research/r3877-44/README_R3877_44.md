# R3877.44 — Correct BusyBox `-help` misdiagnosis and rerun QEMU safely

**Research/educational only. `NOT_BOOTABLE` remains immutable.**

## Historical R3877.6 discovery

The earlier user-supplied R3877.6 runtime output, recovered from the user's 2026-11-07 Mac log, contained **exactly**:

```
probe: busybox_help
exit_code: 127
output: -help: applet not found\n
output SHA-256: 686d46a259767f1b59961c24aa5e885e1bb178829e9bd8886f34b68723d6ac8c
```

The earlier classifier `GUEST_FILE_OR_INTERPRETER_UNAVAILABLE` was **wrong for these bytes**: this is a BusyBox applet/argument usage error, consistent with invoking `busybox -help` rather than the documented `busybox --help`. This does **not** establish the historical test's complete command line as executed, nor prove a full target musl/old Kindle kernel runtime. The R3877.6 wrapper's runtime exit code remains 2 and its historical `HOLD` is preserved unchanged. R3877.5's historical exit 127 also remains unchanged; the new diagnostic reinterprets only the recovered output.

## New R3877.44 local test

The standalone `pw3_r3877_44_busybox_qemu_recheck.py` uses Python 3 stdlib and ordinary Docker CLI (no `buildx`). It **never** touches the Kindle or original private R13 rootfs. Default preflight **does not invoke Docker** and deliberately returns exit 2/HOLD. A separate explicit flag is necessary for the local test.

In authorized mode the tool:

1. Requires an existing local cached ARMv7 image `pw3-r3877-signed-alpine:3.24.3-armv7-dc1ddfaf03ed`, AArch64 Colima Docker server, and the existing `tonistiigi/binfmt:qemu-v10.0.4` helper with the exact previously observed repository digest. **No pulls** are performed.
2. Copies the emulator from a **stopped** temporary helper container to the host's auto-deleted temp folder; checks its previously observed SHA-256 and ELF64 AArch64 machine type. Copies the candidate BusyBox from a **stopped** ARMv7 image container and verifies ELF32 ARM machine type.
3. Copies the pinned emulator only into that **disposable, stopped copy**; commits a temporary derived image, verifies its ARMv7 platform by Docker JSON inspection. The original tagged image is not committed, changed or replaced.
4. Executes four bounded, read-only, networkless, unprivileged QEMU-user probes: emulator `--version`, BusyBox `--help`, BusyBox `true`, BusyBox `uname -m`. No guest shell, mounts, host devices, `binfmt_misc` registration, source image build, or Kindle actions.
5. Tries to remove its two stopped containers and derived image and verify the parent image ID is unchanged. Any missing pin, unexpected result or cleanup failure results in `HOLD`.

**A PASS is limited to these tests on this Docker image**, not PW3 Linux 3.0.35 kernel compatibility, full musl syscall/TLS coverage, KOReader, device hardware, boot or recovery. The official signed-source provenance is **not reauthenticated** by this tool; previous signing claims remain user-reported provenance only.

## macOS commands

After extracting the standalone ZIP, in its folder:

```sh
cd ~/Downloads/pw3-r3877-44
shasum -a 256 -c SHA256SUMS_R3877_44.txt
python3 -B -m unittest -v test_r3877_44.py

# Expected: exit 2, HOLD; NO Docker activity.
python3 -B pw3_r3877_44_busybox_qemu_recheck.py > r3877_44_preflight.json
rc=$?
echo "R3877_44_PREFLIGHT_EXIT_CODE=$rc"  # expected 2
cat r3877_44_preflight.json
```

On the user's zsh shell, use this form to capture exit code robustly:

```zsh
setopt pipefail
python3 -B pw3_r3877_44_busybox_qemu_recheck.py \
  --authorize-offline-qemu | tee r3877_44_runtime.json
rc=$?
print "R3877_44_RUNTIME_EXIT_CODE=$rc"
```

The explicit runtime test requires Docker/Colima to be running and both images already present in its local cache. `exit 0` means `PASS_ARM32_BUSYBOX_QEMU_ONLY` with all four probes and cleanup verified. `exit 2` means retain HOLD and inspect the `error_category` and per-probe `output_prefix` fields in the JSON. **Do not relax pins automatically**, install QEMU on host, run a privileged binfmt container, or flash the Kindle.

Caveat: cleanup is best-effort if the Docker daemon becomes unavailable or crashes; in that case use the reported temporary IDs and inspect manually before any cleanup. Never use blanket Docker pruning.

## Verification performed in this ChatGPT session

29 synthetic/host-only unit tests passed. Preflight generated the expected HOLD/exit 2 with **zero** Docker actions. An actual Colima ARMv7 runtime replay is **not yet performed** in this ChatGPT session.
