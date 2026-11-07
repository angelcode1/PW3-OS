# R3877.21 — Host-only ARM kernel/syscall source-compatibility risk matrix

**Research and educational only. `NOT_BOOTABLE` remains immutable.** This is **NOT** a real syscall execution test, and is NOT a boot, deployment, kernel module, disk-image or recovery test. No target connection or device writes.

## Observed device baseline (user-reported)

The Kindle Paperwhite 3's Linux `3.0.35-lab126` ARMv7 kernel reports ARM TLS HWCAP and an existing set of Kconfig features (FUTEX, EPOLL, EVENTFD, SIGNALFD, TIMERFD, INOTIFY). The running `ext3` `/` is mapped to `mmcblk0p1` by VFS mountinfo, `/proc/mounts` and sysfs. The CPU supports VFPv3/NEON. Previous R3877.18.3 symbol audits provided **static candidates**, not successful runtime bindings. The installed KOReader uses **soft-float glibc** while the proposed Alpine userspace uses **hard-float musl**; mixing these in the same runtime is not supported by this work.

## Why this milestone

The open runtime question is whether musl and the Alpine programs rely on modern Linux operations that are not in a mainstream Linux 3.0 ABI. Musl's general kernel minimum is Linux **2.6.39**, which the PW3 exceeds, but that is not a statement that Alpine's packages work on the vendor kernel. Modern syscalls and edge cases must be evaluated individually, including whether the exact musl implementation has a suitable fallback.

This script builds a conservative **source and version evidence matrix**. It does not run a binary on the PW3 and cannot prove kernel dispatch, ABI correctness, fallback execution, full symbol relocation or recovery. Many operations were added **after** Linux 3.0 in mainline (e.g. `getrandom`, `statx`, `openat2`, `clone3`, `clock_gettime64`). **Backports to the vendor kernel were not checked**. Their presence/absence must not be asserted from the version string alone.

## Host-only commands (no SSH or Docker)

```sh
cd ~/Downloads/pw3-r3877-21
shasum -a 256 -c SHA256SUMS_R3877_21.txt
python3 -B -m unittest -q test_r3877_21.py
python3 -B pw3_r3877_21_arm_syscall_matrix.py R3877_21_USER_REPORTED_INPUT.json \
  | tee r3877_21_matrix.json
```

Expected result for the supplied evidence: `PASS_VERSION_CONFIG_RISK_MATRIX_ONLY` and `NOT_BOOTABLE`. No source header is bundled; this avoids falsely labeling the upstream table as the vendor's actual syscall dispatch table.

### Optional upstream ARM 3.0 header cross-check

On a Mac with normal public Internet access (NOT on the Kindle):

```sh
curl -fLsS --retry 0 --connect-timeout 10 \
  'https://raw.githubusercontent.com/torvalds/linux/v3.0/arch/arm/include/asm/unistd.h' \
  -o upstream-linux-v3.0-arm-unistd.h
shasum -a 256 upstream-linux-v3.0-arm-unistd.h
python3 -B pw3_r3877_21_arm_syscall_matrix.py \
  R3877_21_USER_REPORTED_INPUT.json \
  --kernel-arm-header upstream-linux-v3.0-arm-unistd.h \
  --source-label upstream_linux_v3_0 \
  | tee r3877_21_upstream_source_matrix.json
```

Expected classification: `PASS_UPSTREAM_ARM_SYSCALL_NAMES_METADATA_ONLY`. This is an upstream **v3.0** source reference, not the **v3.0.35-lab126** Kindle vendor tree or the running syscall dispatch table. If the fetch fails, don't use an unrelated kernel header or treat the missing source as a compatibility failure. For an exact kernel audit, acquire and verify provenance of the vendor's original 3.0.35-lab126 source/patch set separately.

## Evidence that remains missing

- Exact musl version, source fallback paths, and Alpine executable syscall requirements are not established by the previous BusyBox ELF metadata alone.
- Vendor kernel syscall table and any backported operations are not verified.
- Target musl **execution**, including TLS, time64 fallback, threading, DNS, file I/O, and entropy, is not verified.
- Complete KOReader dynamic-module binding, original R13 input provenance, rootfs byte-level backup and recovery are not verified.
- Even with a source-header name, an enabled kernel syscall-table entry, ABI-correct libc handling, and successful target execution are different levels of evidence.

## Reference sources

- musl supported platforms: https://wiki.musl-libc.org/supported-platforms
- musl 1.2.0 time64 transition: https://www.openwall.com/lists/musl/2020/02/21/1
- musl 1.2.3 `clock_gettime` ENOSYS/time32 fallback source: https://sources.debian.org/src/musl/1.2.3-1/src/time/clock_gettime.c
- Upstream Linux v3.0 ARM syscall definitions: https://raw.githubusercontent.com/torvalds/linux/v3.0/arch/arm/include/asm/unistd.h
- Linux API introduction history: https://www.linuxman7.org/tlpi/api_changes/index.html

**NO changes to the PW3, stock KOReader, kernel, bootloader, or original R13 files.**
