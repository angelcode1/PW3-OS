# R3786 — Crosswalk of signed minirootfs vs signed APK discrepancies

**User-reported Mac observations; research and educational use only. NOT_BOOTABLE.**

## Scope

The user's R3786 offline preflight returned `R3786_OFFLINE_DUAL_SOURCE_PREFLIGHT_NO_FETCH` / exit 2. The online source comparison separately replayed official authenticated Alpine minirootfs and signed APK payload checks and reported `R3786_SIGNED_MINIROOTFS_APK_DISCREPANCY_INTERSECTION_STATIC_ONLY` / exit 2.

The JSON file in this folder preserves selected reported fields and a **marked inference derived jointly from R3785 and R3786**. It is not the complete original user JSON. GitHub cannot access the original R13 stage and does not rerun any source-package or signature checks.

## Findings

- All **three previously discrepant APK symlink paths** are also signed-minirootfs symlink paths. The signed APK literals match the signed minirootfs original target literals **3/3**. All three staged target changes are precisely the **absolute-to-relative** conversions previously found in R3784, and **3/3** normalize to the same virtual destination.
- R3785 independently reported the **306** changed minirootfs symlinks' final endpoints all structurally equivalent, without host symlink dereferencing. The R3786 lexical check is consistent with that result; neither proves actual guest runtime link resolution.
- The remaining **one regular-file discrepancy** is present as a regular file at the identical path in the signed minirootfs. R3785 reported that **every one of the candidate minirootfs's 83 regular files matched the staged rootfs byte-for-byte**. Together, those Mac-reported observations imply the discrepant staged file **matches the signed minirootfs**, while it **differs from the retrieved signed APK payload**. This is a useful signed-source content-divergence observation, **not evidence of the original installation history or of a legitimate/illegitimate postinstall edit**.

## Important limits

This is a narrow cross-source reconciliation, **not** a reproduced original R13 build, a historical provenance signature, or an explanation of why the installed database disagrees with the signed APK payload. The downloaded signed minirootfs has not been proven to be the original R13 build input. The observed keyring signer identity was not attested out-of-band. Original target PW3 kernel, interpreter path, runtime ABI/TLS, KOReader application execution, firmware and recovery remain unresolved.

## Current runtime focus

The separately tracked R3877.2 ZIP (`pw3-r3877-2-explicit-qemu-arm32-readonly.zip`, SHA-256 `90d6dc0a89450887daabc398468a704d1f55f60fbd315b3db2252596b43c1fae`) passed 139 local host tests but has **not** been executed in the user's Colima runtime. R3877.1's original ARM32 `EXEC_FORMAT_ERROR` is preserved in the separate repo record. Do **not** infer a QEMU PASS from GitHub CI. The physical Kindle and original R13 stage remain untouched. **NOT_BOOTABLE**.
