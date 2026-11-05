# R40.4.3.7.31.1 — ARM attribute length repair, read-only

**Source-only correction; 19/19 synthetic tests PASS; Mac stage run not yet executed; NOT_BOOTABLE.**

## Root cause and preserved HOLD

User R3731 returned `HOLD` / `ARM_ATTRIBUTE_SUBSECTION_BOUNDS_HOLD`. Examination against Arm Addenda32 §3.2.4 identified a defect in the parser's **Tag_File sub-subsection byte-size** handling. The length includes the tag byte(s) as well as the four-byte length field and payload. The original code measured from *after* the tag, and its synthetic fixture repeated that mistake. This is a parser defect, **not evidence of malformed or corrupt staged ELF files**. Keep the original audit held as historical evidence.

The corrected source computes the end from the tag start, validates bounded ULEB tag width, honors ELF endianness for lengths, verifies the intact original R3731 source SHA, and inherits unchanged R3726–R3730 pinned parent checks. Negative tests reject malformed lengths, including the original off-by-one fixture. It emits only non-sensitive aggregate classifications.

Official reference: https://github.com/ARM-software/abi-aa/blob/main/addenda32/addenda32.rst

## Package, without git or gh

The verified standalone archive is named `pw3-r3731-1-attributes-fix-readonly.zip`, SHA-256 `809704171359918ed72c81441171775a47718de05142a689b69c902e8b9f5990`; corrected script SHA `1ab0dde8a96fad86608b114e5d20902171d7fd4dedb649bff7026e4c1a372dc4`. The release package includes the corrected script, original preserved script, all pinned parent scripts, SHA256SUMS, synthetic tests and readme. The Python sources are **not yet committed under this GitHub directory**; download the package from the ChatGPT conversation. Do not claim GitHub Actions passed.

Extract the zip into `~/Downloads/pw3-r3731-1`, then run:

```sh
cd "$HOME/Downloads/pw3-r3731-1"
shasum -a 256 -c SHA256SUMS
python3 -m unittest discover -s . -p 'test_r4043731_1.py' -v
python3 R4043731-1-ARM-ATTRIBUTES-CORRECTED-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD" \
  --original-r3731 "$PWD/R4043731-ARM-ATTRIBUTES-READONLY.py"
```

**NOT_BOOTABLE.** Original source authentication, guest interpreter path resolution, runtime loader, dependency closure, physical PW3, firmware, boot and pruning remain held. No stage writes, ELF execution, QEMU or physical device access.

## User Mac corrected run

The user ran R3731.1 against the existing Mac rootfs and reported `ARM_ATTRIBUTES_CORRECTED_STATIC_CLASSIFIED_ONLY`. All 12 requesting ELF files have parseable `.ARM.attributes`, but none declares Tag_ABI_VFP_args: `VFP_ARGS_UNDECLARED=12`. The alternative ELF also has `.ARM.attributes`, with CPU arch and FP arch tags present, the ABI HardFP-use tag present, and **Tag_ABI_VFP_args undeclared**. The corrected parser's original R3731 source pin and all inherited parent SHA-pins were verified. This **does not** prove ARM CPU/float ABI compatibility, Linux 3.0.35 runtime support or successful interpreter selection; the guest path remains absent. The prior uncorrected R3731 HOLD remains recorded. See `USER-MAC-AUDIT-RESULT.json`. `NOT_BOOTABLE`.
