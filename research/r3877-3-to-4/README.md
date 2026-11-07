# R3877.3 → R3877.4: AArch64 QEMU helper verified; guest injection HOLD

**Research and educational purposes only. NOT_BOOTABLE.**

## User's actual R3877.3 Mac result

The user reported `R3877_3_FAIL_CLOSED` / `QEMU_GUEST_INJECTION_FAILED_HOLD` / exit **2**. On AArch64 Colima, both the existing signed Alpine ARMv7 image and the external helper-image architecture were verified. The QEMU helper was confirmed as a native AArch64 ELF with SHA-256 `3347b95a4006c1eb19b93ba09469a2c42b04fe5d89a430ce96cbf2a2367cf5c1`, from Docker helper digest `tonistiigi/binfmt@sha256:8f58e6214f4cc9dc83ce8f5acad1ece508eb6b20e696a8c1e9f274481982c541`. No helper pull was required in this run. The helper container and guest containers were removed.

The attempt stopped at `docker cp` injection into the destination guest **before any QEMU, BusyBox or musl runtime process executed**. The original runner did not export the Docker error text. Its destination had been created with `--read-only`, which could account for the injection problem, but **the exact cause was not proven**. Earlier R3877/R3877.1/R3877.2 failures remain preserved as separate events.

## R3877.4 — distinct locally tested candidate (Mac result pending)

Local ZIP `pw3-r3877-4-temporary-qemu-layer-readonly.zip`, SHA-256 `32ac0b852132f258eee40a9e9fb1637222f21e2a5927aeeb7f7c19916df38abf`, clean extraction and 20 checksum files validated. **204/204 host unit tests passed** (162 inherited plus 42 new). These include simulated Docker command and cleanup results, **not actual QEMU execution**.

The runner creates a stopped, networkless, nonprivileged **writable preparation container** from the previously imported Alpine image, copies one locally verified static QEMU binary into the disposable layer, and uses `docker commit --pause=false` to produce a **new untagged temporary derived image**. It removes that preparation container without starting it. Five separate runtime containers use the derived image with `--read-only`, `--network none`, `--cap-drop ALL`, a nonroot UID, and no host mounts/devices. The runner inspects Docker's actual HostConfig and refuses to start if readonly/network/capability invariants are not confirmed. It removes temporary guests and the derived image and rechecks that the original Alpine image ID is unchanged.

No helper image pull without explicit opt-in. Never registers binfmt, never executes in original R13 stage, never touches Kindle hardware or firmware. **No user Mac R3877.4 result has yet been supplied.**

The ZIP is a conversation artifact, *not committed as executable source* in this documentation-only PR. GitHub CI validates only the consistency of the selected user-reported record and synthetic authoring tests. Target PW3 Linux 3.0.35 kernel ABI/TLS, PT_INTERP, glibc/KOReader and independent boot/recovery all remain unverified. **NOT_BOOTABLE.**
