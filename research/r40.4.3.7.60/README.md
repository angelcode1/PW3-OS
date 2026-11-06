# R40.4.3.7.60 — Historical R26 tooling ZIP checkpoint (read-only)

**Research and educational use only. `NOT_BOOTABLE`.** Do not modify the original R13 stage, create guest interpreter mappings, execute staged ARM ELFs or QEMU, write firmware, prune files or boot.

## Why this is the next provenance check

The R3758 user Mac-stage audit verified all 2,070 historical R26 inventory entries against the current R13 stage, including 1,448 file hashes, 335 literal symlink targets, 287 directories and 2,070 permission modes. R3759 then found the original R13 manifest as a regular stage file whose own bytes still match R26, but it contained **no recognized build, source, signature, signing-key, attestation or file-hash collection fields**. Therefore neither audit authenticates the image or its author.

An earlier PW3-OS project checkpoint, `docs/R26-STATIC-DEPENDENCY-INVENTORY.md`, records the original release ZIP filename `pw3-os-r26-static-dependency-inventory.zip` and its published SHA-256, `3084db2fe0ec7d13618eaee609bf42083a834bba096f0a0c657287e4a4c0fa0c`. R3760 tests whether the **locally retained original R26 source-tool ZIP** is byte-for-byte consistent with that documentation, rather than rehashing the stage alone. This is a reproducibility checkpoint, **not an independently trusted upstream signature**.

## What this audit does

- SHA-pins the unchanged R3759 script (`89f0dc418437dfbd082ef8251c0182e28731d73f55bdaee2214b60afb41b3b4`) and replays R3759/R3758 and the historical held baseline on the original stage and R26 private inventory.
- Requires a separate original R26 tooling ZIP **outside** the stage. It never regenerates the ZIP or replaces a mismatching copy.
- Reads the ZIP with no-follow access, bounded file size and before/after stat checks; compares its full SHA-256 to the exact documented value.
- Verifies ZIP member integrity, disallows unsafe or duplicate member paths, symlink members and excessive decompressed data. When an internal `SHA256SUMS` is recognizable, also verifies every listed entry against the packaged file bytes. A manifest with unsupported syntax is reported as such, not presumed to match.
- Prints only aggregate counts and fixed result categories. **No local file paths, file names, private hash values, source bytes, ZIP contents or manifest records leave the Mac.**

A match with the repository-published R26 ZIP hash means the original *tooling artifact* agrees with the documented checkpoint. It **does not authenticate who produced the R26 ZIP, the original R13 rootfs, its manifest, the true firmware provenance, the alternate interpreter, recovery or boot**. The original R13 stage, R26 private inventory and original R3759 source are untouched. A missing or mismatching archive returns a HOLD; it does **not** invalidate R3758's valid historical stage inventory match.

## Host verification

32 new R3760 synthetic tests plus 940 inherited tests = **972/972 PASS**. These tests do **not** read your original R13 stage or the original R26 ZIP. The distribution ZIP includes all SHA-pinned predecessor source scripts, their inherited tests, the new audit and regression tests, workflow example, this README and checksums. See `RELEASE-STATUS.json` and `SHA256SUMS`.

## Mac runbook (no git or gh)

Download `pw3-r3760-r26-source-archive-checkpoint-readonly.zip` to `~/Downloads`, then paste:

```sh
mkdir -p "$HOME/Downloads/pw3-r3760"
cd "$HOME/Downloads/pw3-r3760"
unzip -o "$HOME/Downloads/pw3-r3760-r26-source-archive-checkpoint-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043760-R26-SOURCE-ARCHIVE-CHECKPOINT-READONLY.py \
  --stage "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  --r26-inventory "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-INVENTORY.json" \
  --r26-archive "$HOME/Downloads/pw3-os-r26-static-dependency-inventory.zip" \
  --parent-dir "$PWD"
```

If that historical R26 ZIP was retained elsewhere, change only the **`--r26-archive` path**; do not rename or modify the original file to force a match. If absent, return the HOLD category. Share only the resulting JSON, particularly `release_zip_sha256_matches_repo_checkpoint`, `embedded_checksum_manifest_category`, `embedded_checksum_records_matched`, and `result` or `hold_category`.

## Remains held

The R13 manifest and R26 tooling source chain have no independently authenticated upstream trust anchor. The guest PT_INTERP path remains absent; no mapping has been applied. Kernel ABI, runtime ARM TLS, symbol resolution, dependency closure, safe recovery, boot and file pruning are still unproven or forbidden. **`NOT_BOOTABLE`.**
