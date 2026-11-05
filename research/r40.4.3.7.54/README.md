# R40.4.3.7.54 — Alternative guest interpreter self-relocations and referenced dynamic symbols

**Read-only research. NOT_BOOTABLE.** No original R13 stage mutation, guest alias, ELF execution/QEMU, relocation application, firmware, pruning or boot.

## Evidence from the user’s R3753 Mac run
Exactly one same-basename candidate exists away from the requested guest PT_INTERP path. The candidate is ET_DYN, ARM EABI v5 and soft-float flagged, matching the twelve requester ELF header flags. Its entry is in an executable PT_LOAD; two PT_LOAD segments, one executable and one writable, plus GNU RELRO, SysV/GNU hashes, version metadata, no direct DT_NEEDED, no PT_TLS and no PT_INTERP. **This does not prove the candidate is an operational loader**. The guest interpreter path is still absent.

## R3754 diagnostic
Downloadable ZIP `pw3-r3754-interpreter-self-reloc-readonly.zip` holds a SHA-pinned new script and all predecessors; the R3753 source SHA is `08bf159b9ce22e76dc51d5337f615990c40db317a1ef271ebe39f83bda732537`. R3754 replays R3753 and earlier baselines and preserves the original R3745 HOLD. It reads only bounded ELF32 ARM dynamic relocation tables `DT_REL`, `DT_RELA`, `DT_JMPREL`, their ARM type numbers, memory target geometry, referenced dynsym binding/definition/type categories, and selected dynamic-policy flags. Duplicate physical records in multiple table descriptors count by table occurrence and are separately counted. If SysV hash metadata is available, referenced dynsym indexes are bounded by nchain.

Only aggregates leave the tool. The script does **not** export ELF bytes, paths, symbol names, addresses, versions, values, or hashes from the stage; it never runs or modifies the alternative loader. This is a static self-relocation inventory, **not proof of loader self-relocation, ABI semantics, TLS compatibility, missing weak import behavior, dependency closure, recovery or boot**.

## Host verification and distribution
42 new plus 661 inherited synthetic tests = **703/703 PASS** on clean extraction; 52 SHA256 manifest checks PASS and 53-member ZIP integrity PASS. ZIP SHA256: `37b23c974fedfcd5638aa55ac66bb2571d6076b0350e1694f033d067080847e8`. The full executable program, pinned predecessors, tests and CI example are in the **conversation ZIP only**. GitHub contains release metadata and hashes, not full executable code. No R3754 GitHub Actions PASS is claimed.

## Run on Mac without git/gh
Download ZIP into `~/Downloads`, then:

```sh
mkdir -p ~/Downloads/pw3-r3754
cd ~/Downloads/pw3-r3754
unzip -o ~/Downloads/pw3-r3754-interpreter-self-reloc-readonly.zip
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043754-INTERPRETER-SELF-RELOC-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send JSON especially `dynamic_relocation_table_occurrences`, `dynamic_relocation_arm_type_counts`, `dynamic_relocation_target_storage_categories`, `referenced_dynsym_classification`, `referenced_dynsym_bound_category`. If HOLD, report `hold_category` and preserve the R13 stage and SHA pins. Original R26 source provenance, historic hashes, kernel ABI, guest PT_INTERP, runtime TLS and symbol resolution remain held. **NOT_BOOTABLE.**
