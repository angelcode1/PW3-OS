# R40.4.3.7.41 — GNU symbol version candidate classification (read-only)

**Research only. NOT_BOOTABLE. Zero stage writes. No ELF execution, emulation, firmware, Kindle access, or guest aliases.**

## Why

The user-reported R3740 Mac audit classified 632 referenced undefined dynsym entries across 12 requesting ELF objects, representing 369 distinct names. Comparing **names only** to six direct regular-file library candidates gave 517 one-name candidates, 80 multiple candidates and 35 with no candidate. All 12 sources and all six providers have GNU version tag metadata. Name presence alone is not a resolution result.

## What R3741 does

R3741 verifies the exact SHA-256-pinned R3740 Python source and replays the unchanged 12 requester/six provider/632 undefined/369 name baseline. This includes pinned R3739→R3738→R3737→R3736→R3735→R3734→R3733→R3727→R3726. It locates the same six direct library candidates, using no writable mode, and reads bounded ELF32 ARM GNU `.gnu.version`, `.gnu.version_d`, `.gnu.version_r` records only after checking their dynamic tags, section links, record counts, file-backed PT_LOAD addresses and strtab bounds.

For every unique relocation-referenced undefined dynsym index in each requester, it distinguishes explicit GNU required-version names from unversioned/global references, and counts provider definitions with equal version names (or default/unversioned visibility for an unversioned reference). All names are bytes inspected in memory **only**, never included in the output. It flags missing or malformed version metadata as `HOLD` rather than assuming success. The script compares providers by name/version only; **it is not runtime loader symbol resolution**, search order, namespace/interposition, TLS semantics, full dependency closure or version hash validation.

The previous R3740's 35 name-absent entries may be satisfied outside the six staged direct providers. Conversely, matching name/version here does not prove a runtime definition is selected. No rootfs alias is created, no relocations applied, and the sole missing guest interpreter path remains absent. Original R26 provenance, 2070 historic inventory hashes, kernel ABI, recovery and boot/pruning requirements remain open. The future OpenSSH, SFTP and rsync packaging requirement is not changed.

## Mac commands — no `git` or `gh`

Download `pw3-r3741-gnu-version-candidates-readonly.zip` to `~/Downloads` and paste:

```sh
mkdir -p "$HOME/Downloads/pw3-r3741"
cd "$HOME/Downloads/pw3-r3741"
unzip -o "$HOME/Downloads/pw3-r3741-gnu-version-candidates-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r4043741.py' -v
python3 -B -m unittest discover -s . -p 'test_r4043740.py' -v
python3 -B -m unittest discover -s . -p 'test_r4043739.py' -v
python3 -B R4043741-GNU-SYMBOL-VERSION-CANDIDATES-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Share the result's `version_filtered_static_candidate_categories`, `source_symbol_version_requirement_categories`, `distinct_required_version_names_in_memory` or the `hold_category`. If `HOLD`, **do not** alter source pins or the original rootfs to force success. An `HOLD` may reflect unsupported but valid ELF structures; no stage mutation is permitted.

**NOT_BOOTABLE** regardless of results.
