# PW3 R3877.53 — Public ARM Linux 3.0 entropy ABI versus musl call paths

**Research/educational use only. Immutable `NOT_BOOTABLE`.** This is an off-Kindle source audit on macOS, not a runtime compatibility test. It uses no SSH, Docker, QEMU, ARM guest, firmware, boot action, networking within the Python auditor, or private configurations. It never publishes raw kernel configuration or security-sensitive device material.

## Motivation and precise scope

R3877.52.1 user-reported Mac execution passed all 13 pinned musl/ARM/Lab126 public source Git-blob checks, confirming source-level TLS, legacy clone and older-kernel fallbacks. The **application entropy dependency** remained unproven. R3877.53 narrows that question to six **different** exact public-source Git blobs:

- Pinned public `3.0.35-lab126` ARM `unistd.h` and `calls.S`: inspect the ordinary ARM EABI syscall header and dispatch table for **lack of a `getrandom` syscall entry**. Absence in these two public files is not attestation of an installed vendor binary or proof of every possible vendor backport.
- Pinned upstream musl 1.2.6 `getrandom.c` and `getentropy.c`: verify the direct `getrandom` syscall wrapper and that `getentropy` retries only `EINTR` then propagates other errors, **with no `/dev/urandom` fallback in these two functions**. This says nothing about other musl components or applications.
- Pinned upstream musl 1.2.6 libc startup and stack-canary code: verify **`AT_RANDOM` auxiliary-vector seeding**, which is not the `getrandom` syscall; this allows normal libc startup to use kernel-provided auxv randomness without making a `getrandom` call. The source also contains a weak fallback if that auxv pointer is absent. The kernel's actual AT_RANDOM bytes and canary strength are **not** measured.

The output must retain `running_vendor_kernel_getrandom_availability_verified=false`, `application_level_entropy_fallback_verified=false`, `musl_binary_equivalent_to_pinned_source_verified=false`, `target_musl_linux_3_0_35_compatibility_verified=false`, and `NOT_BOOTABLE` regardless of source findings. A PASS does not mean the Kindle lacks an entropy source or that Alpine applications would fail; it only describes these exact public files. Later work should audit actual Alpine application call sites and, separately, a controlled runtime path.

## Mac instructions — no Kindle connection

Extract the ZIP into `~/Downloads/pw3-r3877-53`, then:

```zsh
cd ~/Downloads/pw3-r3877-53
shasum -a 256 -c SHA256SUMS_R3877_53.txt
python3 -B -m unittest -q test_r3877_53.py
```

The default preflight is intentionally `HOLD`, exit 2, and performs no network access:

```zsh
python3 -B pw3_r3877_53_entropy_source_audit.py
```

Fetch **only** the six public source text files from the pinned repository commits. HTTPS verification remains enabled, downloads are to local Mac files, and the next step independently verifies each raw Git blob SHA-1:

```zsh
sh FETCH_R3877_53_PUBLIC_SOURCES.sh sources
setopt pipefail
python3 -B pw3_r3877_53_entropy_source_audit.py \
  --source-dir sources \
  --r52-report R3877_52_1_USER_REPORTED_SELECTED_PASS.json \
  | tee r3877_53_result.json

echo "R3877_53_EXIT_CODE=$?"
```

Expected **only if the real Mac source audit passes**:

`PASS_PINNED_PUBLIC_LINUX3_ENTROPY_ABI_AND_MUSL_CALLPATH_SOURCE_ONLY` / exit `0`.

If any fetch, hash, source-structure or provenance check fails, **HOLD / exit 2**; do not substitute unpinned files or relax the policy. No complete kernel configuration or other device data should be uploaded. Share only `r3877_53_result.json` and the exit code.

## GitHub Actions verification boundary

The accompanying workflow runs only Python offline synthetic tests, checksum checks, shell syntax validation and default no-input HOLD. It does **not** fetch public source files or run a full pinned source audit inside CI, nor touch Docker or Kindle. Passing tests cannot substitute for the reported Mac source audit.

## Existing evidence retained, not promoted

The earlier R3877.51.3 live kernel config: 18 selected known values; earlier `/proc/kallsyms`: 14 selected names present. Neither guarantees that arbitrary binaries built against recent musl work on Linux 3.0.35, that the exact public source represents the running binary, or that a boot/recovery path is safe. Existing `NOT_BOOTABLE` remains immutable.
