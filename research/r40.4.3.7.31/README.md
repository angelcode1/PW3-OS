# R40.4.3.7.31 — static ARM attributes audit package

**Host-only synthetic tests: 12/12 PASS. Mac stage: NOT YET RUN. NOT_BOOTABLE.**

The R3730 user Mac run reported 12 requesting ELF source objects with matching ELF32 ARM EABI5 soft-float header flags and a single alternate loader whose `DT_SONAME` matched the missing interpreter basename. The **exact `PT_INTERP` guest path remains absent**. Header hints do not establish AAPCS/VFP argument compatibility, actual runtime loader selection, kernel 3.0.35 compatibility or boot viability.

R3731 checks the `SHT_ARM_ATTRIBUTES` metadata of the 12 requesting source ELFs and the alternative. It distinguishes section-table/attributes absent, parsed AEABI `Tag_ABI_VFP_args` classes, and malformed/unsupported sections (held). It verifies the exact SHA-256 of the downloaded R3730 parent and inherits R3729/R3728/R3727/R3726 pins. It does not execute any staged ELF or write to the R13 stage, and exports only aggregate counts.

**Availability:** the standalone offline ZIP was generated and clean-extract tested in the conversation, `pw3-r3731-arm-attributes-readonly.zip`, SHA-256 `a4cf906eba5e9e67b37911938628e7524140fd4f9f917eb0fc25d3dd0b9e5031`. **The actual Python source and test files are not present in this GitHub commit**; only the release status and research description are recorded. Do not claim GitHub Actions passed.

When downloaded to `~/Downloads` on macOS, run:

```sh
mkdir -p "$HOME/Downloads/pw3-r3731" &&
cd "$HOME/Downloads/pw3-r3731" &&
unzip -o "$HOME/Downloads/pw3-r3731-arm-attributes-readonly.zip" &&
shasum -a 256 -c SHA256SUMS &&
python3 -m unittest discover -s . -p 'test_r4043731.py' -v &&
python3 R4043731-ARM-ATTRIBUTES-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

No library install, symlink creation, firmware write, physical Kindle access, boot, package installation or pruning. Preserve `NOT_BOOTABLE` and the existing SHA-pinned baseline.

## User Mac hold and corrected successor

User R3731 stage audit reported `HOLD: ARM_ATTRIBUTE_SUBSECTION_BOUNDS_HOLD`. Inspection against Arm Addenda32 §3.2.4 showed the R3731 Tag_File length parser counted the byte-size from after the tag, even though the byte-size includes the tag. Original synthetic fixtures repeated the same off-by-one. This **original HOLD is preserved**; no stage corruption or ABI compatibility has been demonstrated. The corrected read-only successor is [R3731.1](../r40.4.3.7.31.1/README.md), 19 synthetic tests PASS; its Mac run is pending. **NOT_BOOTABLE**.
