# PW3 R3877.29 — signed package declared-source crosscheck

**User-reported local result:** `PASS_SIGNED_APK_DECLARED_COMMIT_SOURCE_BLOBS_ONLY`, exit 0.

Alpine ARMv7 musl 1.2.6-r3's *signed* public APK declares aports commit `8f79d39391b46d6dbf1800fb68b8212a21d5ee2e`. The 12 musl recipe/patch/helper Git blobs and five selected build recipes matched the later pinned snapshot. The user's Mac run reverified the signed APK/index and the cached loader; the canonical patched source fingerprint remains `61bc0d7c9559ffb9c6d1f25a40f041a04391bd2960a0176ac65cc9fe4aae7b8e`.

**Unverified:** actual builder compiler/linker identities, effective CFLAGS/LDFLAGS, build host, source-to-loader byte reproducibility, Amazon kernel syscall dispatch, Kindle execution, recovery. The matching package builddate and declared commit time are metadata consistency only, not independent builder attestation.

Research/educational purposes only. **NOT_BOOTABLE** remains immutable. No Kindle SSH, partition access, installation, firmware write or boot.

The full R3877.29 local Python verifier and synthetic tests are available in the conversation's `pw3-r3877-29-declared-source-commit.zip` artifact; this repository update records the selected successful result only.
