# R40.4.3.7.36 — static PT_DYNAMIC relocation metadata preflight

**Host-only research; NOT_BOOTABLE.** The user's previous R3735 Mac stage run classified one alternate ELF loader and all 12 requesters as static PT_LOAD structure candidates. None of the real runtime, original-source provenance, missing-interpreter-path or boot holds are closed.

R3736 is a new standalone Python ZIP supplied in this conversation, not yet a Mac-stage result. It verifies SHA-256 of the unchanged R3735 source and replays the R3734/R3733/R3727/R3726 lineage and its held guest-path classification. The audit verifies bounded, file-backed PT_DYNAMIC and DT_REL/DT_RELA/DT_JMPREL relocation table descriptors (plus target-address containment in PT_LOAD memory). It emits numeric counts and categories only; no paths, symbol names, library strings or source bytes.

**Synthetic host tests: 16/16 PASS**, including a mocked twelve-requester audit and malformed descriptor rejections; checksum manifest and clean ZIP extraction independently verified. No GitHub Actions run or real Mac stage audit has been verified. The tested ZIP is `pw3-r3736-dynamic-relocations-readonly.zip`, SHA-256 `e591c91f0893af5fd31d4f0929b9cf249107b74b96124b273ae67d0218690e45`. The script is SHA-256 `48189e67421d5aaebfa3dfdc1bfd64cd8b383c347d09a0fc58fa8bbdb38fb447`; tests `dc078ba878c770306c87ce8faaf0d5f3d75e3e23eb9b1c3144f46ae2239e6927`. The **Python source and tests are in the conversation ZIP but not in this repository commit**.

## Run on macOS without git or gh

Download the ZIP into `~/Downloads` and run:

```sh
mkdir -p "$HOME/Downloads/pw3-r3736"
cd "$HOME/Downloads/pw3-r3736"
unzip -o "$HOME/Downloads/pw3-r3736-dynamic-relocations-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r4043736.py' -v
python3 -B R4043736-DYNAMIC-RELOCATION-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

This classification never applies relocations, resolves the actual PT_INTERP guest pathname, installs a loader or a guest mapping, runs an ELF/ARM QEMU, changes the original stage or authorizes firmware, boot or pruning actions. All runtime dependencies and kernel ABI compatibility remain unverified. The OpenSSH/SFTP/rsync package requirement for the later validated independent image remains unchanged. **NOT_BOOTABLE**.

## User Mac stage result

R3736 returned `DYNAMIC_RELOCATION_TABLES_STATIC_CLASSIFIED_ONLY`. The alternative loader has **21 REL and six PLT relocation entries**, zero RELA, three distinct relocation types, zero `DT_NEEDED`, and zero relocation target addresses outside PT_LOAD ranges. The **12 requesting ELFs** total **2,924 REL, 575 PLT, zero RELA and 19 literal DT_NEEDED entries**, with no relocation targets outside PT_LOAD. All 12 source files were classified `RELOCATION_TABLES_BOUNDED_STATIC_CANDIDATE`; SHA-pinned R3735 and earlier source chains replayed. These counts are user-reported; no relocation application, actual symbol resolution or source authenticity has been verified. The guest interpreter path is **still absent** and no future alias has been applied. Original rootfs unchanged. See `USER-MAC-AUDIT-RESULT.json`. **NOT_BOOTABLE**.
