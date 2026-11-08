# PW3 R3877.52 — Pinned musl ARM TLS/private syscall and older-kernel fallback source audit

**Research and educational use only. Immutable `NOT_BOOTABLE`.** No Kindle access, SSH, Docker, QEMU, firmware/boot actions, root or installation. The Python program reads only local public text sources and previously sanitized R3877.51.3 evidence. The separate fetch script uses HTTPS to retrieve **public** GitHub source files onto your Mac, with exact Git blob verification **after** download.

## Previous baseline

- R3877.49.3: real offline Colima user-mode QEMU executes ARMv7/musl BusyBox applets, 55 selected syscall records, 14 distinct names, no observed `ENOSYS` in those applets; `trace_output_separation_verified=false`. This is **not** the Kindle kernel.
- R3877.50: public `linux-3.0.35-lab126` mirror dispatch-source entries exist for those 14 names.
- R3877.51.3: user-reported successful *read-only* `/proc/config.gz` transfer and Mac-side gzip integrity/decode. 18 selected live config flags reported (`CONFIG_AEABI`, `CONFIG_CPU_V7`, `CONFIG_BINFMT_ELF`, `CONFIG_FUTEX`, `CONFIG_VFP`, `CONFIG_NEON` enabled; `CONFIG_SECCOMP`, `CONFIG_SMP` disabled). A previous live `/proc/kallsyms` receipt has 14 matching names. Only selected values are shipped, never raw config or kernel addresses.
- R3877.23 already inspected upstream source functions for `clock_gettime64`, `futex_time64`, `fstatat/statx` and the direct `getrandom` wrapper. R3877.26.1–27 pinned the Alpine aports `1.2.6-r3` patches and a patched source-tree fingerprint, **not** a rebuilt signed loader. R3877.52 expands the source path review to ARM-specific thread setup, the ARM-private TLS kernel dispatch handler, `clock_nanosleep`, and `getentropy` callers.

## New pinned source links and findings

GitHub connector examination matched **13 exact Git blob identities**: 10 upstream musl v1.2.6 sources and three public Lab126 mirror files at commit `7ac2585f384573da8cbdcc987a3503e2e6ff1fb4`. The full names and blob IDs are in `R3877_52_PINNED_SOURCE_MANIFEST.json`.

1. `src/thread/arm/__set_thread_area.c` uses `__syscall(0xf0005, p)`. Public Lab126 `arch/arm/include/asm/unistd.h` defines `__ARM_NR_set_tls` as base + 5 and `arch/arm/kernel/traps.c` contains `case NR(set_tls)` to store the thread pointer. This **ARM-private path was omitted from the ordinary syscall crosswalk**.
2. ARM `clone.s` uses legacy syscall number 120; `pthread_create.c` passes `CLONE_THREAD`, `CLONE_SETTLS`, and related flags. The ARM thread pointer has a CP15-read path. This is source-path compatibility **only**: running thread creation, clone flags, atomic operations and TLS are not verified on the Kindle.
3. `clock_gettime.c`, `clock_nanosleep.c` and `__timedwait.c` carry legacy time32 and futex fallbacks under guarded conditions. The fallback may clamp timeouts/ranges; behavior after 2038, VDSO branches, and runtime failure paths remain unverified.
4. `fstatat.c` has a guarded `statx` to old `fstatat_kstat` fallback. The kernel build conditions, application-specific `statx` use, and metadata edge cases remain unverified.
5. `getrandom.c` directly calls `SYS_getrandom` and `getentropy.c` calls `getrandom`, retries `EINTR`, and otherwise breaks. Neither wrapper internally falls back to `/dev/urandom`. Since Linux 3.0 predates mainline `getrandom`, application-level entropy fallback is a **specific unresolved gate**. We do not replace secure entropy with an unsafe source or infer any app's behavior.

**Important limits:** This analysis uses upstream musl v1.2.6 and public Lab126 sources, not bytes from the signed patched Alpine `musl 1.2.6-r3` binary or a proved-identical running Kindle kernel build. Alpine's downstream `src/env/__init_tls.c` patch is not directly re-applied or audited by R52. No runtime ABI compatibility is claimed. Public mirroring alone does not establish the exact Kindle kernel binary.

## Mac commands — no Kindle connection

```zsh
mkdir -p ~/Downloads/pw3-r3877-52
unzip -oq ~/Downloads/pw3-r3877-52-musl-arm-tls-source.zip -d ~/Downloads/pw3-r3877-52
cd ~/Downloads/pw3-r3877-52
shasum -a 256 -c SHA256SUMS_R3877_52.txt
python3 -B -m unittest -q test_r3877_52.py
# With no arguments, the auditor deliberately returns HOLD / exit 2.
python3 -B pw3_r3877_52_musl_arm_tls_fallback_audit.py
```

Fetch precisely the 13 public, version-controlled source files (HTTPS TLS verification remains enabled):

```zsh
sh FETCH_R3877_52_PUBLIC_SOURCES.sh sources
setopt pipefail
python3 -B pw3_r3877_52_musl_arm_tls_fallback_audit.py \
  --source-dir sources \
  --r51-report R3877_51_3_SELECTED_USER_PASS.json \
  | tee r3877_52_result.json
printf 'R3877_52_EXIT_CODE=%s\n' "$?"
```

The fetch script merely downloads public text to your Mac; the **auditor is offline**, checks exact Git blob IDs before analyzing patterns and refuses changed or missing files. Missing HTTPS trust, network failures, changed tags, unexpected blob bytes or altered selected R51 evidence cause HOLD. Do not bypass TLS errors or weaken the pin. On success the narrow result will be `PASS_PINNED_UPSTREAM_MUSL_ARM_TLS_AND_OLDER_KERNEL_FALLBACK_SOURCE_ONLY` with exit 0, while `NOT_BOOTABLE` remains in force.

## CI and next gates

The GitHub Actions workflow runs only local synthetic tests, verifies the release checksums, compiles the source for syntax and checks a no-input HOLD. It does **not** download source files, run ARM code, inspect Kindle, or promote a source-only result into live kernel compatibility. Full real public source comparison requires the Mac commands above; its result is pending until user runs it.

Next: audit the exact Alpine patched `__init_tls.c` and musl compile-time configuration against the signed loader, inspect application entropy requirements and target kernel ABI behavior safely, separately establish verified recovery, and only then review the immutable boot restriction. No boot or firmware modifications are proposed.
