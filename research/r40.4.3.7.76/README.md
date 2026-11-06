# R40.4.3.7.76 — Alpine public key source corroboration (user Mac evidence)

**Research/educational use only. Immutable NOT_BOOTABLE.** This directory records a user-reported Mac result; it does not assert that GitHub runners inspected the user's private R13 stage or downloaded any package archives.

## Observed R3776 result

The user ran the offline SHA-pinned R3776 source and reported `PINNED_ALPINE_APORTS_PUBLIC_KEY_OFFLINE_CORROBORATION_ONLY`, exit **2** and the original `APK_INSTALLED_FILE_RECORD_DISAGREEMENT_HOLD`. The probe compared the original staged Alpine RSA **public** keys to three pinned public-key files from the `alpinelinux/aports` upstream mirror at commit `f223d8d0d1a43fb02d57c33c52f999eb7197bd54`.

- 3/3 pinned upstream public-key Git blob IDs matched their packaged bytes.
- 2/2 staged keys matched the corresponding upstream *DER* public key bytes.
- 2/2 staged key files also matched the upstream public files byte-for-byte.
- The staged pair matched the expected `armhf` or `armv7` key set.
- No staged package was installed or executed, and no rootfs file or firmware was modified.
- The upstream Git commit was **not cryptographically signed**; a published file and digest are not an independently attested signer identity.

The report is preserved separately in `USER-MAC-KEY-CORROBORATION-RESULT.json`. No user private key, package name, path, hash, or rootfs byte was uploaded.

## Relevant earlier local observations (not re-executed)

The preceding Mac R3775 report compared three signed official Alpine packages against the R13 stage and found that the packages contained all four discrepant entries. The signed package payloads and installed database records agreed; the staged regular-file bytes differed once, and three staged symlink literals differed. Package signatures, index control checksums and payload `datahash` all validated **against staged keys**. This does not establish *when* the stage changed, its original image source, or independent trust of those keys.

R3774/R3775 additionally observed three `noarch` package-control architecture values versus architecture-specific signed-index values, retaining `PACKAGE_PKGINFO_COORDINATE_MISMATCH_HOLD`. The documented `apk index --rewrite-arch ARCH` option is a **possible** cause of such a difference, not proof of the command's historical execution. See [apk-index(8)](https://man.archlinux.org/man/apk-index.8.en).

## Next prepared R3777 host test

An independently versioned local ZIP named `pw3-r3777-signed-alpine-keyring-readonly.zip` (SHA-256 `9414ce29935f8e52fdc4efaa21162921a6d19b467fe818b647b8d1d3770bfe76`) adds a bounded, host-only check against the current official, *signed* Alpine `alpine-keys` package. The ZIP was clean-extracted and passed **272/272** synthetic host tests in the assistant environment (250 inherited + 22 new). It was **not run on the user's R13 stage** and is **not included in this repository change**.

If the R3777 online test passes, it independently corroborates **key material across three distribution channels** (staged rootfs, pinned aports source, and retrieved signed Alpine keyring package). Because the package's signature is verified using the *same staged public keys*, that corroboration **does not create an independent signing-identity trust root**. The R13 image provenance and the original file/architecture HOLDS persist.

## Immutable boundary

Historical R3765–R3775 tools and user reports are not silently reconstructed or rewritten in this directory. The original R13 stage, R26 inventory, signed-package metadata and historic discrepancy outputs remain unchanged. Actual device kernel identity, ARM interpreter selection, runtime ABI/TLS, full dependency/recovery and independent image provenance remain unverified. **No boot, package install, firmware writes, guest execution, mapping or pruning authorized. NOT_BOOTABLE.**
