# R40.4.3.7.77 — Archived user Mac failure and source-supported alias hypothesis

**Research and education only. Immutable NOT_BOOTABLE.**

This directory preserves the user's R3777 **offline and online** observations separately, without retroactively changing either result. The offline run reported `R3777_OFFLINE_KEYRING_PACKAGE_PREFLIGHT_NO_FETCH` and exit 2, replaying the R3776 public-key source corroboration. The online run reported `R3777_FAIL_CLOSED_HOLD`, category `ALPINE_KEYS_PACKAGE_MEMBER_NONREGULAR_HOLD`, exit 2.

## Evidence and likely diagnostic cause

The pinned upstream [Alpine `alpine-keys` APKBUILD](https://github.com/alpinelinux/aports/blob/f223d8d0d1a43fb02d57c33c52f999eb7197bd54/main/alpine-keys/APKBUILD) installs raw public keys in `/usr/share/apk/keys` and the architecture's `/etc/apk/keys`, with architecture-specific symbolic links under `/usr/share/apk/keys/<arch>/` pointing to `../<key>`.

The **R3777** archive reader treated any matching key basename in the selected key directories as requiring a regular file. Therefore encountering an expected architecture alias can cause its specific `NONREGULAR_HOLD`. This is a *source-supported hypothesis* for the Mac failure, not proof of the exact offending archive member. No user package archive was uploaded. On exception the original program reinitializes its output status; its `false` signature/key-check counters **cannot be read as negative cryptographic test outcomes**.

## Next prepared R3778 local package

`pw3-r3778-keyring-archive-alias-readonly.zip` was prepared separately in the assistant's working container and passed **298/298 synthetic host tests**, clean extraction, manifest checks and a missing-stage fail-closed test. It preserves the R3777 parent file SHA, fixes **only** the read-only archive public-key member matcher, and requires three exact roles per staged public key: (a) regular `etc/apk/keys/<key>`, (b) regular `usr/share/apk/keys/<key>`, (c) an architecture alias `usr/share/apk/keys/<arch>/<key>` symlink with literal `../<key>`. It does **not** follow links, install an APK, alter the stage or change any older verifier source. R3778 has not been run on the user's Mac and is **not** part of this PR.

## Trust boundaries

R3776 public key source equality is a corroboration, not independent cryptographic attestation of the publisher. R3775's staged file differences (1 regular text file and 3 symlinks) remain observed against the retrieved signed packages, subject to staged-key trust; their historical cause is unverified. Three `noarch` vs architecture-specific index discrepancies remain. The original R13 image provenance, physical running kernel, ARM interpreter, runtime ABI/TLS, boot and recovery are unverified.

No guest execution, firmware writes, device access, rootfs modifications, mapping or pruning. **NOT_BOOTABLE**.
