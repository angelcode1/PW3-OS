# R3877.4 commit-image-ID HOLD, R3877.5 tagged image candidate

**Research and educational use only. Original R13 stage immutable. NOT_BOOTABLE.**

## Actual user Mac evidence

The user ran 204/204 R3877.4 host tests successfully. Their explicit-QEMU runtime attempted to use the previously verified AArch64 Colima Docker server and cached `tonistiigi/binfmt:qemu-v10.0.4` helper. QEMU ELF SHA-256 was `3347b95a4006c1eb19b93ba09469a2c42b04fe5d89a430ce96cbf2a2367cf5c1`.

R3877.4 successfully **copied QEMU into a stopped disposable preparation container** and removed that container. The next step stopped at `DOCKER_NEW_IMAGE_ID_INVALID_HOLD`, before creating or starting any ARMv7 runtime guest. The existing signed Alpine image ID remained unchanged. No R13 files, devices, firmware, binfmt settings or network-enabled guests were touched.

The R3877.4 source returned this HOLD only after `docker commit --pause=false` had a zero exit code but the command's **printed output did not match a strict 71-character `sha256:` image-ID regex**. Docker's official CLI examples show shortened printable commit image identifiers, so the check was inappropriate. But the **actual stdout was not captured**; the precise output is unknown. A temporary **untagged image might have been created**, even though the R3877.4 output field `disposable_derived_image_created=false` only means its **ID was not successfully validated**. Do not perform broad `docker image prune` or delete an unverified dangling image.

## R3877.5 candidate (local host validation only)

The separate `pw3-r3877-5-tagged-temp-qemu-runtime-readonly.zip`, SHA-256 `8d1b7fc3f30427e6f1d2fcc637df5ed8af3ce0423de4451d91befd7a4c7d1cf3`, passed **254/254** authoring-host tests (204 inherited + 50 new), a clean ZIP extraction, 25 member SHA-256 manifest checks and a fail-closed offline preflight (exit 2). The full source remains in the conversation ZIP, not in this GitHub documentation PR. **No R3877.5 runtime result on the user's Colima machine has been reported.**

R3877.5 preserves the original R3877.4 script byte-identically and pins its SHA-256 `6472ebf64cd3eb9c36f0750319ca0db5a8f3aa2792bd9093cdd94e8d81026c08`. It creates a fresh random scoped temporary image tag, refuses an existing or unverified collision, commits the stopped preparation container to the new tag, then validates the resulting **canonical image ID** with native Docker JSON inspection (not command stdout). It verifies architecture and a different ID from the original signed Alpine image. Five separate networkless, read-only, nonprivileged containers perform explicit QEMU probes, if opted into by the user. Cleanup removes only the exact new tag and, if Docker retains a dangling derived image, the previously verified exact image ID; it checks both are absent. A cleanup failure is a HOLD. The original signed Alpine image is untouched and there is no privileged binfmt registration, `prune` call, stage mount or Kindle operation.

No authoring-host Docker/QEMU runtime was available; simulated Docker lifecycle success is **not** actual ARMv7 execution. Even a future Colima success does not establish Kindle Linux 3.0.35 ABI/TLS, original R13 PT_INTERP mapping, KOReader/glibc, historical source provenance or bootability.

**Historical R3877 through R3877.4 failures preserved. NOT_BOOTABLE.**
