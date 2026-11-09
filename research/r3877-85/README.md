# R3877.85 — Native LuaJIT FFI libc/libm ABI smoke on Kindle PW3

**Research / educational purposes only.** This preserves `NOT_BOOTABLE`, no permanent installation, no boot/config change, no GUI/e-ink actuation and no UART dependency.

## What R3877.83 proved

The user reported `PASS_GLIBC_LUAJIT_SINGLE_PROCESS`, SSH exit `0`, original six-file glibc bundle integrity and loader mappings verified, and successful ephemeral cleanup. This proves only a bounded native LuaJIT `io.write` invocation, not the KOReader application runtime. A previous SSH exit `255` occurred but a later successful run superseded that as the latest device result; the original failure cause remains unknown.

## New, single-process workload

Keep the exact R3877.83 ELF bundle (one native LuaJIT executable, the glibc loader, four dependent libraries), original SHA-pinned R81/R82 parsers, RPATH inhibition and loader `--list` mapping checks. Once the same *existing executable tmpfs* and all six SHA-256 values have been verified, start one **non-graphical** LuaJIT process. It uses its built-in FFI to call `getpid()` from glibc, then explicitly opens **the bundled** `libm.so.6` via the private temporary directory and calls `cos(0.0)`. It prints exactly one marker only if both checks pass, exits and removes the temporary files on the success path.

The code does **not** import KOReader Lua modules, inspect documents, alter display/input/power/wireless devices, start firmware services, mount any filesystem, write to eMMC or touch the stock boot chain. It runs as root and invokes a native process: **not risk-free**. If SSH fails or times out, cleanup is not guaranteed, so do not automatically rerun.

## On the Mac: validate without device access

````zsh
cd ~/Downloads
unzip -oq pw3-r3877-85-luajit-ffi-abi.zip -d ~/Downloads
cd ~/Downloads/pw3-r3877-85
shasum -a 256 -c SHA256SUMS_R3877_85.txt
python3 -B -m unittest -q test_r3877_85.py
STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
setopt pipefail
python3 -B pw3_r3877_85_luajit_ffi.py \
  --stage "$STAGE" --review-only | tee r3877_85_offline.json
printf 'R3877_85_OFFLINE_EXIT_CODE=%s\n' "$?"
```

The offline review returns `HOLD / NOT_BOOTABLE`, exit **2**, with `offline_validation_passed=true` and `hold_category=HOST_FFI_TEST_READY_DEVICE_UNVERIFIED` if ready. Stop on any other category. No SSH is made.

## Optional one-shot attended device execution, ONLY after offline readiness

````zsh
python3 -B pw3_r3877_85_luajit_ffi.py \
  --stage "$STAGE" \
  --acknowledge-one-shot-kindle-ffi-test \
  --target root@192.168.8.102 --port 2222 \
  | tee r3877_85_live.json
printf 'R3877_85_LIVE_EXIT_CODE=%s\n' "$?"
```

Successful JSON: `PASS_GLIBC_LUAJIT_FFI_LIBC_LIBM_SINGLE_PROCESS`, `ffi_libc_libm_calls_verified=true`, `tmpfs_cleanup_reported_complete=true`, exit `0`. The run still says `NOT_BOOTABLE`. A successful result verifies this single FFI path only; it does not verify arbitrary C modules, full symbol binding, KOReader app startup, e-ink hardware or independently verified recovery.

**Source/evidence policy:** Do not publish the private staged ELF bytes, full original rootfs, device backups, local file names or full stage catalog. Only host-only test source and counts-only summaries belong in GitHub.
