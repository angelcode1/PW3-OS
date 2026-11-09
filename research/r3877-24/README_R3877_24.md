# PW3 R3877.24 — Indexed public Alpine musl loader byte comparison

**Research and educational only. `NOT_BOOTABLE`.** Mac-only. No SSH, Kindle access, raw eMMC, boot, firmware writes, Alpine execution, Docker execution or package installation.

## Why this follows R3877.23

The user successfully reported both R3877.23 source-only and stopped-image candidate checks. The cached Alpine candidate image ID remains `sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a`; installed musl is `1.2.6-r3` for `armv7`, and its extracted loader SHA-256 is `2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990`. The pinned Alpine 3.24 aports `APKBUILD` agrees on the package version, but previous work has **not** established that the candidate loader bytes match the publicly published Alpine package.

R3877.24 compares that original **existing** candidate loader to the published `musl-1.2.6-r3.apk` from Alpine v3.24/main/armv7, and cross-checks the package against the repository `APKINDEX.tar.gz`. No Alpine binary runs.

## Run on macOS

```sh
mkdir -p ~/Downloads/pw3-r3877-24
unzip -oq ~/Downloads/pw3-r3877-24-public-apk-loader-match.zip -d ~/Downloads/pw3-r3877-24
cd ~/Downloads/pw3-r3877-24
shasum -a 256 -c SHA256SUMS_R3877_24.txt
python3 -B -m unittest -q test_r3877_24.py

# Download two public files on the Mac. TLS verification stays enabled.
sh FETCH_PUBLIC_ALPINE_MUSL.sh public-musl

# Reuse the file R3877.23 already copied from your *stopped* Docker container.
# There is no need to start Docker or contact the Kindle again.
set -o pipefail
python3 -B pw3_r3877_24_public_apk_loader_match.py \
  --apk public-musl/musl-1.2.6-r3.apk \
  --index public-musl/APKINDEX.tar.gz \
  --candidate-loader ~/Downloads/pw3-r3877-23/candidate/loader \
  | tee r3877_24_result.json
printf 'R3877_24_EXIT_CODE=%s\n' "$?"
```

If the existing `candidate/loader` is unavailable, you can re-run R3877.23's **stopped-container** collector, but do not change the image or attempt the comparison using some newly downloaded loader substituted for the cached candidate.

## Checks and classification

A `PASS_INDEXED_PUBLIC_MUSL_LOADER_BYTES_MATCH_ONLY` result requires all of:

1. The existing candidate loader matches the previously pinned SHA-256 baseline.
2. The public `.apk` is a bounded, well-formed Alpine v2 package (concatenated gzip tar segments).
3. Its `.PKGINFO` declares package `musl`, version `1.2.6-r3`, architecture `armv7`.
4. The `.PKGINFO` `datahash` matches SHA-256 of the compressed payload stream.
5. The package contains `lib/ld-musl-armhf.so.1` with the same **complete bytes** as the candidate loader, with a matching SHA-256.
6. `APKINDEX.tar.gz` has a unique matching `musl` entry whose `Q1` checksum matches SHA-1 of the compressed package control stream.

A malformed archive, invalid hash, mismatch, or absent file reports `HOLD` and exits with code 2. Tar paths are never extracted to disk, so package-supplied filenames cannot overwrite files on your Mac. The Python analyzer has no network or subprocess calls.

**Authenticity caveat:** Checking an index checksum and an archive `datahash` is a consistency test, not an independent signature verification. In particular this script **does not** cryptographically verify the Alpine repository's signing key, the APKINDEX signature, or the package signature. It does not produce reproducible-build proof or source-to-binary equivalence, and does not audit all Alpine downstream patches. It does not establish that the 3.0.35-lab126 kernel supports syscalls the binary may make.

The exact published APK was **not** fetched or tested inside the authoring environment due to its network restrictions. The test suite uses only synthetic `.apk`/`APKINDEX` fixtures; the real package comparison requires your Mac to run the above command. Failures from actual public package layout should be reported for a parser fix, not worked around by weakening validation or modifying Kindle files.

## Sources

- Alpine v3.24 armv7 repository: https://dl-cdn.alpinelinux.org/alpine/v3.24/main/armv7/
- APK v2 format reference: https://man.archlinux.org/man/apk-v2.5.en

## Still unresolved after a PASS

`vendor_kernel_dispatch_verified=false`, `target_musl_runtime_verified=false`, `binary_provenance_to_patched_source_verified=false`, `alpine_application_syscall_requirements_verified=false`, `recovery_verified=false`, and `NOT_BOOTABLE` is immutable. The existing KOReader remains glibc/soft-float and must not be linked directly with this Alpine musl/hard-float image.
