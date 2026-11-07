# R3877.40 — Signed musl ARMv7 loader: static ELF metadata research

**Research/educational use only; immutable `NOT_BOOTABLE`.**

The R3877.39 user-reported Mac result passed: 1,423 exact printed compile/link object matches, five extra compile outputs, five distinct copy destinations, and a later exact-token mention for each destination. Those later mentions have unresolved command families and do **not** attest executed filesystem operations.

R3877.40 investigates the larger remaining gap: historical compiler and linker identity. The host-only diagnostic revalidates the **signed Alpine v3.24 armv7 musl 1.2.6-r3 APK and index** with pinned Alpine public-key bytes and the exact cached loader hash `2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990`, then statically inspects ELF32 ARM headers, optional `.ARM.attributes`, `.comment`, and GNU build-ID records. No loader is executed or built, and no Kindle access occurs.

The standalone diagnostic, source and synthetic tests have been supplied as the Mac ZIP `pw3-r3877-40-signed-loader-elf-metadata.zip` in the conversation. **The real APK/loader audit has not yet run.** The offline ZIP passed 61 synthetic tests. This research record is not a real-input PASS claim.

Do not infer the historical builder toolchain from recipe version numbers or compiler producer strings alone. A producer string cannot identify the historical machine, linker flags or signed-loader reproducibility.

Preserve `NOT_BOOTABLE` regardless of static ELF findings: Amazon vendor kernel dispatch, runtime ABI behavior, rootfs recovery and original builder provenance remain unverified.
