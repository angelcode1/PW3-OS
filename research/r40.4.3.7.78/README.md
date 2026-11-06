# R40.4.3.7.78 — User Mac signed Alpine keyring alias verification

**Research and educational purposes only. Immutable NOT_BOOTABLE.**

The user's R3778 **offline** and **online** observations are separately preserved in `USER-MAC-KEYRING-RESULT.json`. These are user-reported data, not re-executed by GitHub, and no private R13 rootfs content was uploaded.

## Verified by the reported online R3778 output

- The Alpine main repository index verified against one of the staged public keys.
- The retrieved `alpine-keys` package's signature and its signed-index control identity verified with staged keys; the compressed data payload `datahash` matched.
- The archive contained two verified regular `etc/apk/keys` members and two verified regular `usr/share/apk/keys` members, plus two selected-architecture symlinks lexically validated as literal `../<same key>` targets, without following links.
- Both selected public keys matched the staged keys and the pinned `alpinelinux/aports` upstream public keys.
- The `alpine-keys` package had **zero** `.PKGINFO` vs index architecture discrepancies; the **three different affected packages** with `noarch` vs target-architecture index values remain under separate investigation.

The previous R3777 online `ALPINE_KEYS_PACKAGE_MEMBER_NONREGULAR_HOLD` remains historical user evidence. Its stricter parser rejected legitimate architecture-specific symlink aliases documented by [Alpine's pinned `alpine-keys` APKBUILD](https://github.com/alpinelinux/aports/blob/f223d8d0d1a43fb02d57c33c52f999eb7197bd54/main/alpine-keys/APKBUILD).

## Trust boundaries

The package/index were verified using the **staged** public keys, and the pinned upstream Git commit is unsigned; this does **not** constitute independently attested distribution signer identity or an independent trust root.

R3775 previously recorded one staged `/etc` regular file and three symlink targets differing from the signed package payloads; their historical cause, R13 image provenance and install sequence remain unknown. The physical PW3 running kernel, dynamic linker path, runtime ABI/TLS and boot viability are not verified. No changes were made to the stage. **NOT_BOOTABLE**; no firmware writes, device access, guest code execution, mapping, pruning or boot authorized.

## Prepared follow-up (not part of this PR)

An independently versioned local R3779 ZIP tests the three affected packages' additional signed-index vs `.PKGINFO` field parity. Its synthetic host suite (330/330), clean extraction and checksum manifest passed in the assistant environment. This user-run test has not yet been performed against the real R13 stage and is **not** included or represented as a GitHub CI validation of the rootfs. If only the architecture differs, the observation is *consistent with* documented `apk index --rewrite-arch` behavior, **not proof** the original image build ran that command.
