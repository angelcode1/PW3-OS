# PW3 R3877.26 — Pinned Alpine musl source inputs and in-memory patch audit

**Research and educational purposes only. `NOT_BOOTABLE` remains mandatory.** No Kindle SSH, firmware writes, boot attempts, raw eMMC reads, ARM program execution, Docker start or toolchain build. This is a Mac-host audit of public Alpine packaging inputs only.

## R3877.25 observed baseline (user-reported)

R3877.25 returned `PASS_PINNED_APORTS_SIGNATURES_AND_PUBLIC_LOADER_MATCH_ONLY` with exit code 0. Both the Alpine ARMv7 repository index and `musl-1.2.6-r3.apk` package signatures verified against the exact RSA public key file `alpine-devel@lists.alpinelinux.org-616adfeb.rsa.pub` in pinned aports Git snapshot `35f5eb2864e50dd4448758d31f3e2a32f733ab84`. SHA-256 of both public APK loader and cached-image loader = `2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990`. Those keys are anchored to the public Git snapshot, **not to an independently established external trust root**.

This closes the signed-public-package matching milestone. It does *not* prove that any musl build could be reproduced from source, that the PW3 kernel can execute it, or that no security vulnerability remains.

## New inputs verified by R3877.26

The pinned `alpinelinux/aports` Git snapshot contains `main/musl/APKBUILD` blob `b729315a72d9060cc69ba9bddec53c0691c05158` at musl `1.2.6-r3`. It lists **twelve inputs**:

- One upstream `musl-1.2.6.tar.gz` release archive.
- Six downstream patches: `handle-aux-at_base`, pthread mutex-priority stub, LoongArch64 signal-header adjustment, and three security patches (`CVE-2026-6042`, `CVE-2026-40200`, `CVE-2026-107891`).
- Five packaging helper inputs: `ldconfig`, `__stack_chk_fail_local.c`, `getconf.c`, `getent.c`, `iconv.c`.

R3877.26 validates all 12 files against the **SHA-512 checksums in that exact pinned APKBUILD**. It also checks the exact Git-blob SHA-1 for APKBUILD and each of the eleven downstream files. The pinned manifest and APKBUILD must agree in **names, order and digests**. The upstream release tarball is verified by the APKBUILD SHA-512 only (no upstream signing key or reproducible build claim).

If input verification succeeds, the auditor reads only the relevant files from the musl tar.gz and applies all six patches **in memory**, in APKBUILD order, with **exact context matching** and no fuzz or file-system writes. It reports affected paths and SHA-256s of the modified **source files**, not compiled outputs. It never executes patch scripts or musl source. It rejects malformed/path-escaping archives, mismatched Git blobs, unlisted patches, wrong checksums, failed hunks and unexpected source paths.

An in-memory patch pass establishes exact applicability of the pinned Alpine patches against a verified upstream archive. **It does not prove that Alpine's build flags, cross compiler, generated files, build environment, all APKBUILD build steps or resulting binary are reproducible.** The exact package loader was previously matched and signature-verified, but source-to-binary provenance remains unverified.

### Run on Mac

```sh
mkdir -p ~/Downloads/pw3-r3877-26
unzip -oq ~/Downloads/pw3-r3877-26-aports-source-patch-audit.zip -d ~/Downloads/pw3-r3877-26
cd ~/Downloads/pw3-r3877-26
shasum -a 256 -c SHA256SUMS_R3877_26.txt
python3 -B -m unittest -q test_r3877_26.py
sh FETCH_PINNED_APORTS_MUSL_INPUTS.sh sources
set -o pipefail
python3 -B pw3_r3877_26_aports_input_audit.py --source-dir sources --inputs-only | tee r3877_26_inputs.json
printf 'R3877_26_INPUTS_EXIT_CODE=%s\n' "$?"
python3 -B pw3_r3877_26_aports_input_audit.py --source-dir sources | tee r3877_26_result.json
printf 'R3877_26_EXIT_CODE=%s\n' "$?"
```

Expected results: `PASS_PINNED_APORTS_INPUT_BYTES_ONLY` and, if all hunks exactly apply in memory, `PASS_PINNED_APORTS_SOURCE_PATCH_MEMORY_APPLY_ONLY`. Both deliberately retain `hold_category=NOT_BOOTABLE` and `immutable_hold=NOT_BOOTABLE`. Do not bypass a HOLD if the downloaded source changes; provide the JSON classification for diagnosis. No need to log into or modify the Kindle.

## Follow-on research gaps

1. Build provenance: match the actual published APK build's build environment/flags, toolchain and generated files, and reproduce its loader byte-for-byte; not done here.
2. Trace Alpine **application-specific** syscall requirements and `getrandom` error paths; musl's `getrandom` wrapper alone has no built-in ENOSYS fallback.
3. Test old kernel time64/legacy futex behaviour in a controlled non-Kindle emulation environment; mainline Linux v3.0 source names do not establish Amazon's vendor syscall table.
4. Independently verify recovery and original R13 stage provenance before any device deployment.

Nothing here authorizes Alpine installation or boot, or mixing stock KOReader soft-float/glibc components into Alpine hard-float/musl.
