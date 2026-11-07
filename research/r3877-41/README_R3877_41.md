# R3877.41 — Crosscheck signed loader ABI with pinned printed link and recipe

**Research and educational purposes only. Immutable hold: `NOT_BOOTABLE`.**

R3877.40 succeeded with the signed public Alpine musl APK/index and a byte-identical cached loader. User-reported static ELF metadata is archived at `research/r3877-40/R3877_40_USER_SELECTED_STATIC_ELF.json`.

The loader is ELF32 little-endian ARM, EABI5, `e_flags=0x05000400` hard-float with ARMv7 / VFPv3-D16 and VFP argument registers. It contains one hashed GNU build-ID, no compiler `.comment` and no DWARF debug sections. These observations cannot identify the historical compiler or prove vendor kernel compatibility.

A standalone host-only R3877.41 analyzer and its 20 synthetic regression tests are distributed in `pw3-r3877-41-abi-recipe-link-crosscheck.zip` in the originating chat. The executable Python sources are **not in this commit** and no R3877.41 GitHub CI pass is claimed.

To run on Mac, extract that ZIP, verify `SHA256SUMS_R3877_41.txt`, run `python3 -B -m unittest -q test_r3877_41.py`, then run:

```sh
python3 -B pw3_r3877_41_abi_recipe_log_crosscheck.py \
  --elf-report ~/Downloads/pw3-r3877-40-1/r3877_40_result.json \
  --log ~/Downloads/pw3-r3877-30/musl-armv7-build.log \
  --apkbuild ~/Downloads/pw3-r3877-26/sources/APKBUILD
```

Expected classification only upon real-file success: `PASS_PINNED_SIGNED_ELF_RECIPE_LOG_ABI_CROSSCHECK_ONLY`.

The R3877.41 static crosscheck verifies:
- Prior R3877.40 report's signed APK/index and loader hash claims and exact ABI/build-ID markers
- Public musl ARMv7 build log byte count and SHA-256, link lines 1666–1667 and joined hash
- Alpine's musl APKBUILD pinned Git blob, `CHOST`/CFLAGS handling, and soname link option

Printed `cc` flags are not proof of executed argv, compiler defaults or historical toolchain versions. No binaries are executed; no Docker, SSH, Kindle storage, boot or firmware paths are accessed.

**Outstanding blockers:** actual builder compiler/linker identity and flags; signed-loader source-to-binary reproducibility; vendor kernel runtime compatibility; verified recovery.
