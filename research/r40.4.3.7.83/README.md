# R40.4.3.7.83 — Signed Alpine ARMv7 minirootfs baseline (user Mac result)

**Educational/research use only. Immutable `NOT_BOOTABLE`.**

## Observed on user's Mac

The user's original R3782 verifier stopped at `STAGE_METADATA_UNREADABLE_HOLD` because it omitted the required `rootfs/` directory. R3783 preserved the original R3782 source bytes and corrected only that rootfs subtree traversal using no-follow directory FDs.

The user then supplied two R3783 JSON results, reproduced as separate `offline` and `online` objects in `USER-MAC-SIGNED-MINIROOTFS-RESULT.json`. Both have exit code **2** and retain `ORIGINAL_R13_IMAGE_PROVENANCE_UNAUTHENTICATED_HOLD`.

The successful online run verified the selected official **Alpine 3.24.3 ARMv7 minirootfs** tarball's SHA-256 release record and detached GPG signature, with release-key fingerprint matching Alpine's published fingerprint. These are **user-reported tests**, not executed against the private stage by GitHub Actions.

## Actual source-to-stage overlap reported

| Category | Archive | Present/matching staged entry | Differences |
| --- | ---: | ---: | ---: |
| Regular files (SHA-256) | 83 | 83 | **0** |
| Symlink target literals | 335 | 29 literally matching; 335 present as symlinks | **306 differing** |
| Directories | 96 | 96 | **0** |

Archive member count is **515** including one archive-root entry. Compared regular-file content totaled 5,446,454 bytes. No archive file or directory was missing or unexpectedly replaced by another entry type. **The 306 link-literal differences must not be treated as equivalent destinations without a separate no-follow lexical check; nor is a textual difference alone proof of a broken symlink.**

This evidence corroborates substantial overlap with the official signed Alpine minirootfs. It does **not prove that the downloaded candidate was the original R13 input**, authenticate the independently assembled image, establish signer identity out of band, determine the cause or date of 306 link changes, or resolve the earlier four signed-APK discrepancies (1 changed regular file + 3 changed symlink targets).

## Prepared next verification

A separately packaged, locally tested **R3784** no-follow symlink-literal pattern probe compares only the 306 differences while replaying the unchanged R3783 archive signature and original crosswalk. The package `pw3-r3784-signed-symlink-pattern-readonly.zip` has SHA-256 `e85424aee816489609aa50e208504250d12aaf911a444426f9460dc52c39a74a`. Clean extraction, SHA-256 manifest and **94/94 synthetic host tests** passed in the assistant's environment. This ZIP and its code are **not committed** in this documentation PR and have **not** been tested on the actual R13 stage.

## Immutable limits

No guest execution, Kindle device access, firmware modification, stage changes, package installation, interpreter mapping, pruning or boot authorized. Actual PW3 kernel identity, runtime ABI/TLS, exact PT_INTERP path, recoverability and complete image provenance remain unverified. **NOT_BOOTABLE**.
