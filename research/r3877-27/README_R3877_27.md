# PW3 R3877.27 — Pinned patched musl source-tree fingerprint

**Research and educational use only. `NOT_BOOTABLE` remains immutable.**

## Verified inputs from user-reported R3877.26.1

R3877.26.1 returned `PASS_PINNED_APORTS_SOURCE_PATCH_MEMORY_APPLY_ONLY`, with 13 verified source inputs, 6 pinned Alpine patches, 26 unique full-context hunks, 13 shifted hunks, and 7 changed source files. No Kindle access, compilation, firmware modification, boot attempt, or binary reproducibility occurred. The seven patched-file SHA-256 values are copied as a fixed test baseline in `R3877_27_EXPECTED_PATCHED_SHA256.json`.

The audit was previously pinned to Alpine `aports` commit `35f5eb2864e50dd4448758d31f3e2a32f733ab84`, musl `1.2.6-r3`. Public package signatures and candidate loader bytes were separately verified in R3877.25. This does not independently verify the upstream public key trust chain, Amazon vendor kernel, or a reproducible compilation.

## What this audit establishes

1. Revalidate all 13 existing local source inputs using their pinned Git blob and SHA-512 constraints.
2. Reconstruct all 7 patched files using the R3877.26.1 **unique full-context, no-fuzz** algorithm in memory and require exact equality with the seven user-reported post-patch SHA-256 values.
3. Read the original source tar archive in memory. Hash every regular file's contents and size, every directory, every symlink's **unfollowed** target, and the reported permission bits; overlay the seven patched files, including new source files. The resulting SHA-256 is a reproducible canonical JSON *source-tree fingerprint*, not the digest of a generated tar archive or of a compiled binary.
4. Emit a compact JSON result with the fingerprint, counts, and an immutable `NOT_BOOTABLE` hold.

The tooling **does not reconstruct the Alpine builder's exact compiler, linker, build environment, flags or package signing process**. It does not rebuild musl. Even a passing result does not prove the patched source produced the signed public loader or runs on Kindle Linux 3.0.35.

## Run on Mac — no network, Kindle SSH, Docker, or build required

Use the **already downloaded** R3877.26 inputs:

```sh
mkdir -p ~/Downloads/pw3-r3877-27
unzip -oq ~/Downloads/pw3-r3877-27-source-tree-fingerprint.zip -d ~/Downloads/pw3-r3877-27
cd ~/Downloads/pw3-r3877-27
shasum -a 256 -c SHA256SUMS_R3877_27.txt
python3 -B -m unittest -q test_r3877_26.py test_r3877_26_1.py test_r3877_27.py
set -o pipefail
python3 -B pw3_r3877_27_patched_tree_fingerprint.py \
  --source-dir ~/Downloads/pw3-r3877-26/sources \
  | tee r3877_27_result.json
printf 'R3877_27_EXIT_CODE=%s\n' "$?"
```

Expected successful classification: `PASS_PINNED_PATCHED_SOURCE_TREE_FINGERPRINT_ONLY`. The fingerprint is *not* known until the real source archive is analyzed on your Mac. Do **not** confuse an offline synthetic test pass with a real source-tree verification.

## Future gate

Next, enumerate the Alpine builder toolchain, build flags, and exact package revision. Only if those are pinned should an **off-Kindle** rebuild and byte comparison to the *signed* loader be attempted. Build mismatch is not automatically evidence of tampering: nondeterministic build paths, compiler versions and link flags must first be controlled. Any work affecting the Kindle's physical boot path remains prohibited.
