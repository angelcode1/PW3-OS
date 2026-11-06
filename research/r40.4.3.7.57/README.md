# R40.4.3.7.57 — Alternative interpreter vs requesters: ARM build attributes

**Read-only research and educational use; immutable `NOT_BOOTABLE`.** No original R13 rootfs writes, symlink or guest mapping, ARM/QEMU execution, firmware, boot or pruning.

## Prior Mac evidence preserved

The user's R3756 run of the unchanged R13 stage returned `ALTERNATE_INTERPRETER_SELF_SYMBOL_GNU_VERSION_METADATA_STATIC_ONLY`. Its single alternate ELF32 ARM ET_DYN candidate's `DT_SONAME` matches the staged candidate basename; all nine defined self-referenced dynsym entries have nonempty names, mapped GNU Verdef indexes, and clear VERSYM hidden bits. Three Verdef records exist. A consistent self-version map **does not** prove the candidate can run as a loader, relocate itself, or handle weak references. The guest PT_INTERP path remains absent in all twelve requesters.

## New bounded read-only survey

The source SHA-pins unmodified R3756 (`786aca0dd7e577e82a8292019d6dac4bad89fbf8ef2852bf171dfeed04c0760d`) and replays its entire inherited pinned baseline including the original R3745 HOLD. It finds the same one alternate loader and twelve requesters, and reads ELF32 ARM `.ARM.attributes` (SHT_ARM_ATTRIBUTES, 0x70000003) section bytes using the original no-follow file reader. It verifies lengths, version `A`, vendor and public AEABI scope boundaries, ULEB128 integers, and only recognized public file-level attribute tags. Unknown public tags, malformed structures, conflicting repeated tags or missing source pins produce HOLD. Private vendor and section/symbol-scoped attributes are never mistaken for public file-level attributes.

It compares **only declared file-level metadata**: Tag_CPU_arch, Tag_CPU_arch_profile, Tag_ARM_ISA_use, Tag_THUMB_ISA_use, Tag_ABI_PCS_R9_use, Tag_ABI_PCS_GOT_use, Tag_ABI_PCS_wchar_t, Tag_ABI_align_needed/preserved, Tag_ABI_enum_size, Tag_ABI_HardFP_use, Tag_ABI_VFP_args, Tag_DIV_use. For each of twelve requesters, each tag is classified as BOTH_PRESENT_EQUAL, BOTH_PRESENT_DIFFERENT, REQUESTER_ONLY, CANDIDATE_ONLY or BOTH_ABSENT. An absent `.ARM.attributes` section or absent tag is **not** silently considered compatible. Unsupported public tag formats cause a safe HOLD and can be revised in a separate version; original code/pins remain unchanged.

Output is numerical aggregates and allowlisted category names only: no ELF words, attribute values, addresses, file paths, vendor names, symbol names, version strings, raw bytes or computed identifiers. Header/attribute equality is not proof of Linux kernel, dynamic loader, TLS runtime, ABI, guest interpreter, recovery, boot or dependency closure compatibility. No interpreter-path alias is created. Original R26 source provenance and historic hashes remain unverified.

Specification references: [Arm ADDENDA32](https://github.com/ARM-software/abi-aa/blob/main/addenda32/addenda32.rst) and [Arm AAELF32](https://github.com/ARM-software/abi-aa/blob/main/aaelf32/aaelf32.rst).

## Verification

**59 new + 804 inherited = 863 synthetic Python tests passed** (including pinned-module call-chain integration). Clean extraction rerun is also required and reported in RELEASE-STATUS; full SHA256SUMS covers all extracted files except itself. The ZIP integrity and checksum verification must pass before the Mac stage audit. The runnable source and tests are packaged in the ZIP; GitHub release documentation alone is not executable or a GitHub Actions run.

## macOS runbook (no git or gh)

Download `pw3-r3757-arm-build-attributes-readonly.zip` into `~/Downloads`, then:

```sh
mkdir -p ~/Downloads/pw3-r3757
cd ~/Downloads/pw3-r3757
unzip -o ~/Downloads/pw3-r3757-arm-build-attributes-readonly.zip
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043757-INTERPRETER-ARM-BUILD-ATTRIBUTES-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send result JSON including `candidate_attribute_section_category`, `requester_attribute_section_categories`, and `requester_candidate_file_tag_relation_counts`. If HOLD occurs, send `hold_category` without bypassing source pins or modifying the stage.

**NOT_BOOTABLE**. OpenSSH/SFTP/rsync deferred to a future independently validated image.