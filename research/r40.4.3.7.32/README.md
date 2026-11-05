# R40.4.3.7.32 — Numeric ARM attribute comparison (read-only)

**Research/education, source-only. NOT_BOOTABLE.** This is a future diagnostic, not a boot/installation package. The real Mac stage **has not been run** for this release.

## Input evidence

The user's R4043731.1 Mac report classified 12 requesting ELF files with parseable `.ARM.attributes`, each with `Tag_ABI_VFP_args` **undeclared**. The single alternative loader ELF also had attributes present with the VFP argument convention undeclared, despite CPU architecture, FP architecture, and HardFP-use tags being present. This does **not** prove the floating-point calling convention or runtime compatibility.

R3732 imports the SHA-256 pinned **unchanged** corrected R3731.1 source, rechecks the original held R3731 SHA and pinned R3726–R3730 chain, repeats the earlier 83 ELF / 19 PT_INTERP / 7 direct / 12 absent and static SONAME results, and parses numeric AEABI `Tag_File` attributes (strictly bounded). It compares the one alternative with all 12 requesting ELF sources. Output is **aggregate numeric tag categories only**; no filenames, interpreter literals, SONAME strings, section bytes, user identifiers or symlink targets.

The comparison covers CPU architecture (`6`), CPU profile (`7`), Thumb ISA (`9`), FP architecture (`10`), PCS wchar size (`18`), alignment needed/preserved (`24`,`25`), enum size (`26`), HardFP-use (`27`) and VFP argument passing (`28`). Matching **numeric values do not prove compatible CPU profiles, runtime loader invocation, usable kernel syscalls, relocations, or safe boot**. Undeclared values remain explicitly unverified. Hardware FP capability is not inferred from the presence of Tag_ABI_HardFP_use.

The source-only audit does not execute binaries or use QEMU, SSH, firmware or live devices. It does not create aliases or alter the original staged rootfs. The missing guest PT_INTERP path **remains absent**. R26 provenance, historical file hashes, complete transitive dependency closure, independent image boot and recovery all remain held. **NOT_BOOTABLE.**

## macOS commands without `git` or `gh`

Download `pw3-r3732-arm-numeric-attributes-readonly.zip` into `~/Downloads` and run:

```sh
mkdir -p "$HOME/Downloads/pw3-r3732"
cd "$HOME/Downloads/pw3-r3732"
unzip -o "$HOME/Downloads/pw3-r3732-arm-numeric-attributes-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -m unittest discover -s . -p 'test_r4043732.py' -v
python3 R4043732-ARM-NUMERIC-ATTRIBUTES-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD" \
  --original-r3731 "$PWD/R4043731-ARM-ATTRIBUTES-READONLY.py"
```

If output reports `HOLD`, send the `hold_category`; never change files or pins to force a successful classification. Expected synthetic tests: **13 passed**; actual stage attribute values **unknown** until user run. A `ARM_NUMERIC_ATTRIBUTES_RELATION_CLASSIFIED_ONLY` result remains **not an ABI or runtime PASS**.

## Related package request

OpenSSH SSH server, SFTP server and rsync are [reserved for the final validated Alpine image](../../docs/PW3-REMOTE-TRANSFER-PLAN.md). None are installed by this diagnostic.

## User Mac numeric ARM attributes result

The user reported `ARM_NUMERIC_ATTRIBUTES_RELATION_CLASSIFIED_ONLY` on the local stage. Each of the 12 requesting ELFs declares the same numeric `CPU_ARCH=10`, `CPU_ARCH_PROFILE=65`, `FP_ARCH=3`, `THUMB_ISA_USE=2`, `ABI_ALIGN_NEEDED=1`, `ABI_ENUM_SIZE=2` and `ABI_PCS_WCHAR_T=4` values as the one alternative. Nine of twelve declare `ABI_ALIGN_PRESERVED=1` and three leave it undeclared; ten declare `ABI_HARDFP_USE=3` and two leave it undeclared. All twelve requesters and the alternate leave `ABI_VFP_ARGS` undeclared. **Undeclared is not equivalence**, and these numeric declarations do not establish Linux 3.0.35 kernel support, loader execution, real guest-path resolution, independent boot or safe pruning. See `USER-MAC-AUDIT-RESULT.json`. The missing guest interpreter path remains absent. `NOT_BOOTABLE`.
