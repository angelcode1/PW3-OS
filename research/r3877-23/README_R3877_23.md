# PW3 R3877.23 — Pinned musl 1.2.6 upstream fallback-source audit

**Research/education only. `NOT_BOOTABLE` is immutable. This is entirely on your Mac.** No SSH, no raw eMMC reads, no Kindle binaries installed/executed, no boot changes. Do not link the soft-float glibc KOReader libraries against hard-float musl.

## Why this step

R3877.22 passed the **pinned upstream Linux v3.0 ARM syscall-name/header** check. This did not test the actual `3.0.35-lab126` vendor dispatch, the installed Alpine image, or musl's older-kernel fallbacks.

R3877.23 distinguishes **upstream source**, **Alpine packaging snapshot**, and (optionally) the **cached local image**. It does not assume that the branch/tag `3.24.3` identifies a precise installed musl package version. The pinned Alpine `3.24-stable` Git commit `35f5eb2864e50dd4448758d31f3e2a32f733ab84` has an `APKBUILD` with `musl 1.2.6-r3` and downstream patches; your actual cached image may differ. If so, the candidate check intentionally reports HOLD. The musl upstream source is tag `v1.2.6` in the `ifduyue/musl` mirror.

## Step 1 — verify the downloadable package and its host-only tests

```sh
mkdir -p ~/Downloads/pw3-r3877-23
unzip -oq ~/Downloads/pw3-r3877-23-pinned-musl-fallback-audit.zip -d ~/Downloads/pw3-r3877-23
cd ~/Downloads/pw3-r3877-23
shasum -a 256 -c SHA256SUMS_R3877_23.txt
python3 -B -m unittest -q test_r3877_23.py
```

## Step 2 — fetch only *public* source files to the Mac

```sh
sh FETCH_PINNED_SOURCES.sh sources
python3 -B pw3_r3877_23_musl_source_audit.py \
  --source-dir sources | tee r3877_23_source_only.json
```

The downloader uses `curl --fail --location --retry 0` with TLS certificate verification enabled and explicit URLs. The **Python audit does not access the network**. It recomputes Git's **SHA-1 blob identity** for every downloaded file and checks that it matches the pinned GitHub API evidence. This is pinned-source identity verification, not a claim of cryptographic source signing or provenance beyond GitHub.

If all pinned source files match, the report is `PASS_PINNED_UPSTREAM_MUSL_SOURCE_ONLY`. Upstream musl paths checked:
- `src/time/clock_gettime.c`: when available, `clock_gettime64` → time32 `clock_gettime` after `-ENOSYS` (within conditional builds).
- `src/thread/__timedwait.c`: `futex_time64` → legacy `futex` after `-ENOSYS`, with finite time32 clamping; this is not an unconditional time64 guarantee.
- `src/stat/fstatat.c`: `statx` → `fstatat_kstat` when available and `-ENOSYS` occurs.
- `src/linux/getrandom.c`: **direct syscall wrapper**; the wrapper itself contains no entropy fallback for `-ENOSYS`. Calling application code has **not** been audited.
- `arch/arm/bits/syscall.h.in` and `arch/arm/syscall_arch.h`: upstream ARM-specific numbers/VDSO definitions (not vendor kernel dispatch).

## Step 3 — inspect the existing cached Docker image *without executing it*

This uses only the Mac's previously tested **Colima/Docker** environment and requires the existing local image tag:

```sh
sh COLLECT_STOPPED_IMAGE_METADATA.sh candidate
python3 -B pw3_r3877_23_musl_source_audit.py \
  --source-dir sources --candidate-dir candidate --require-candidate \
  | tee r3877_23_result.json
printf 'R3877_23_EXIT_CODE=%s\n' "$?"
```

The collection helper first checks image ID against the **previously audited** immutable baseline `sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a`. It then uses `docker create --entrypoint /bin/true` **but does not start** that temporary container. It copies only `/lib/apk/db/installed` and the musl loader into local `candidate/` with `docker cp`, cleans up the stopped container, and never runs ARM code. The Python audit checks the **musl package version/arch** and the loader's previously observed SHA-256 `2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990`.

If the actual candidate is `musl 1.2.6-r3`, architecture `armv7`, and all pinned IDs match, the report is `PASS_PINNED_MUSL_SOURCE_AND_CANDIDATE_METADATA_ONLY`. The installed package/version may be different, in which case the report is an intentional HOLD, **not** a reason to change the image or the Kindle. Do not install/update musl to force a pass.

## Remaining holds — even after a PASS

`target_musl_runtime_verified=false`, `vendor_kernel_dispatch_verified=false`, `alpine_application_syscall_requirements_verified=false`, `binary_provenance_to_patched_source_verified=false`, `recovery_verified=false`, and `NOT_BOOTABLE`. A tag, apk package version, or loader hash alone **does not prove** the binary was built from the pinned upstream sources plus the pinned Alpine patches. In particular the source audit **does not** confirm all downstream patches or transitive calling-code fallbacks. The next stage should audit the **specific Alpine downstream patch changes** and, later, non-Kindle emulated ABI/syscall behaviour before any consideration of device execution.

User-reported R3877.22 baseline: all 20 checked syscall names in upstream Linux v3.0, source Git blob `2c04ed5efeb50707ac3353958434d37691841839`, target vendor dispatch unknown. No original R13 stage was accessed.
