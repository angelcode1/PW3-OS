# R3877.2 helper-image inspection failure — user Mac result and R3877.3 correction

**User-reported evidence only. NOT_BOOTABLE.**

On the user's Colima Docker server (AArch64), the R3877.2 explicit-QEMU attempt failed before any QEMU/ARM32 commands could run: `R3877_2_FAIL_CLOSED`, exit code 2, `REQUIRED_DOCKER_IMAGE_UNAVAILABLE_HOLD`. The runner reported `helper_image_pull_performed=true`, `helper_image_architecture_verified=false`, `test_outcomes=null`. No original stage, physical Kindle, firmware or privileged binfmt changes occurred.

The exact earlier R3877.2 source raises a *different* error `QEMU_HELPER_IMAGE_PULL_FAILED_HOLD` if `docker pull` returns nonzero. Therefore the reported status is consistent with a **failed Docker image inspect after a successful pull**, not proof that the Docker Hub tag did not exist. The published tag is available in the Docker Hub tag catalog. The actual Docker inspect error text was not retained; its exact cause remains unverified. The original source used `--format '{{.Os}}|{{.Architecture}}|{{.Variant}}|{{.Id}}|{{json .RepoDigests}}'`, which is sensitive to optional fields such as `Variant`.

A separate locally packaged R3877.3 changes Docker image inspection to **native JSON parsing** with required OS/architecture and optional Variant/RepoDigests. It also distinguishes an unsuccessful helper pull from an image-inspection failure following a successful pull. It contains the historical R3877.2 script unchanged.

R3877.3 source bundle: `pw3-r3877-3-colima-helper-inspect-fix-readonly.zip` SHA-256 `c85402dfcf7ca64ddbb04166904845be50746193a977b1fa52803d0909aa7926`. The assistant executed **162/162** host tests (139 inherited + 23 new), clean ZIP extraction, all 15 manifest hashes, and an offline `NOT_BOOTABLE` preflight that exited 2. **No R3877.3 ARM/QEMU run on the user's Colima VM has been reported.** This documentation PR does not upload the ZIP or Docker helper binary.

Independent R13 build provenance, physical PW3 Linux 3.0.35 ABI/TLS, ELF loader path and dynamic relocs, KOReader/glibc, device safety, recovery and boot remain unverified. No source image modification or original-stage mapping. **NOT_BOOTABLE.**
