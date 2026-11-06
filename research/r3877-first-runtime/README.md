# R3877 / R3877.1 — First actual ARM32 failure and Colima host diagnosis

**Research and educational use only. Original stage immutable; NOT_BOOTABLE.**

This PR records a **user-supplied** R3877 host execution result and a **user-supplied** R3877.1 diagnostic. It does not claim that GitHub ran Docker/Colima, accessed the user's historical R13 rootfs, or verified the original PW3 running kernel.

## Observations

1. The user's R3877 stage-independent offline preflight returned exit 2, `R3877_OFFLINE_RUNTIME_GATE_READY_NO_ARM_EXECUTION`.
2. The R3877 official-source phase reported Alpine **3.24.3 armv7** release SHA-256 manifest, detached OpenPGP signature and published primary key fingerprint verified. Archive SHA-256 `dc1ddfaf03ede4be79ad7475490f6b7859dbcbbbbb85150aa1ee013b4bc2f0c1`. This authenticated a candidate upstream release, **not** proof that it was the original R13 image input.
3. The user imported that signed archive into the Colima Docker image `pw3-r3877-signed-alpine:3.24.3-armv7-dc1ddfaf03ed`. The first BusyBox help process exited **255**. No BusyBox or musl **PASS** was claimed.
4. R3877.1 subsequently identified Docker server architecture **AArch64**, image platform **linux/arm/v7**, Colima ARM32 binfmt status **NOT_REGISTERED**, and **EXEC_FORMAT_ERROR / exit 255** for all three diagnostics: BusyBox help, BusyBox shell and musl loader. This distinguishes **host ARM32 execution/emulation configuration failure** from a demonstrated failure of the Alpine application itself. It does not prove BusyBox/musl compatibility.
5. The prior R3877 and R3877.1 fail-closed observations remain historical. No host binfmt registration was performed.

## Follow-on (source locally tested; actual Mac execution pending)

A separate R3877.2 source ZIP `pw3-r3877-2-explicit-qemu-arm32-readonly.zip`, SHA-256 `90d6dc0a89450887daabc398468a704d1f55f60fbd315b3db2252596b43c1fae`, was clean-extracted and passed **139/139 synthetic host tests**. It reuses the existing signed-source R3877 Docker image, optionally pulls a QEMU helper image **only after explicit opt-in**, verifies the helper binary's native AArch64 ELF architecture, copies it to a stopped disposable container, and invokes QEMU explicitly to execute ARMv7 guest commands. The runner never registers binfmt, invokes privileged containers, mounts host paths or accesses the original stage. **No user-Mac R3877.2 test has been reported.**

The helper version tag is mutable and its release signer is not independently verified; future Mac results will report the resolved helper image digest and QEMU ELF SHA-256 to make the test reproducible.

## Limits

Success under explicit QEMU on the AArch64 Colima Linux 6.8 VM would **not** verify the old Kindle Linux 3.0.35 kernel, target syscalls/ARM TLS, original PT_INTERP linker placement, KOReader/glibc, independent R13 build provenance, Kindle device features, firmware or recoverability. Neither source nor guest programs were executed on a physical Kindle. **NOT_BOOTABLE.**
