# R40.4.3.7.38 — DT_NEEDED basename candidate audit (read-only)

**Source-only, research and educational purposes. NOT_BOOTABLE.**

The user-reported R3737 Mac stage audit found 12 ELF files referencing one missing PT_INTERP guest path, 19 combined DT_NEEDED entries and 632 undefined dynamic-symbol records referenced by relocations (counts aggregated across ELF files, not globally deduplicated). The requesting ELFs contain ARM TLS relocation types 17, 18 and 19, requiring separate TLS runtime analysis. The original interpreter path is **still absent**; a future relative alias has been simulated but not created.

R3738 is an independently SHA-pinned, read-only tool that checks exact R3737 source SHA256 **27ac20c24670424623ecc8f6bd52e80b6b5835935a403d62548c734b11104c77** and inherits R3736, R3735, R3734, R3733, R3727 and R3726 pins. It replays the 12-requester relocation evidence, privately reads bounded PT_DYNAMIC/DT_STRTAB/DT_STRSZ metadata, extracts 19 DT_NEEDED name literals **only in memory**, and reports aggregate categories for same-basename stage file and symlink candidates. No source path, needed library name, dynamic symbol string or symlink target is exported.

The categories distinguish one or multiple ELF-header-compatible regular/symlink candidates, missing library basenames, incompatible entries and names containing paths. **Same-basename presence is not proof of actual dynamic library lookup**, RPATH/RUNPATH and transitive dependencies are not traversed, and the test does not simulate loader execution. The tool also reports the 5/1/32 inherited ARM TLS-related relocation counts; it does not prove TLS support.

The companion archive `pw3-r3738-needed-library-candidates-readonly.zip` was locally verified: **16/16 synthetic tests PASS**, Python syntax valid, checksum manifest and ZIP integrity PASS. Archive SHA256: `5086cfbff47aa9e0983bf8a94b4d5ea37c2873d118a66c543ccf8d5b9fc474b5`. Tool SHA256 `66f5f3d1fd62c7ad3515c57a1e72b32e2f41be4e9ab74b67d1144f07f1ab2ee3`, tests SHA256 `2fa3a98aa689fbb3cd3d3f887d83afeb7a525ab6abf00e45d01f836063a4991e`. All 11 archive members include exact pinned parents, runnable script, tests, README and SHA256SUMS.

**The runnable Python source and tests are in the user-conversation ZIP, not yet published as standalone source in GitHub. The Mac rootfs result and GitHub Actions PASS have not been verified.**

## macOS without git or gh

Download the archive to Downloads, then:

```sh
mkdir -p "$HOME/Downloads/pw3-r3738"
cd "$HOME/Downloads/pw3-r3738"
unzip -o "$HOME/Downloads/pw3-r3738-needed-library-candidates-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r4043738.py' -v
python3 -B R4043738-NEEDED-LIBRARY-CANDIDATES-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send the resulting JSON including `dt_needed_same_basename_candidate_categories`, `distinct_dt_needed_name_literals` and `per_source_dt_needed_entry_count_histogram`. A HOLD result must not be bypassed by weakening source pins or modifying the stage.

No original stage writes, no alias creation, firmware write, physical Kindle access, boot, pruning, ELF/QEMU execution, or image install. Original R26 source provenance, historical hashes, kernel runtime loader, exact interpreter path, full ABI, transitive dependencies and future image recovery remain held. OpenSSH/SFTP/rsync remain a deferred final-image requirement. **NOT_BOOTABLE**.

## User Mac result

The user reported `REQUESTER_NEEDED_BASENAME_STATIC_CANDIDATES_ONLY`: 12 source ELF files have 19 DT_NEEDED references spanning **six distinct literal library names**. Each reference had **one regular staged same-basename ELF-header-compatible candidate**; no matching symlink candidate. The 12 requesting files contain 7 with one DT_NEEDED, 4 with two, and 1 with four. R3737 and earlier SHA-pinned static checks replayed. Inherited ARM TLS relocation counts remain 5/1/32. Same basename alone does **not** prove runtime loader search path, SONAME equivalence, transitive dependencies or symbol version resolution. Guest PT_INTERP path remains absent and no mapping was applied; original rootfs unchanged. See `USER-MAC-AUDIT-RESULT.json`. **NOT_BOOTABLE**.
