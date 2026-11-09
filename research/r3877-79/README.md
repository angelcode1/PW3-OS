# R3877.79 — KOReader native entrypoint discovery (Mac-only)

**Research only. HOLD / NOT_BOOTABLE. No Kindle connection, execution, mount, chroot, boot or firmware changes.**

## Current device checkpoint

R3877.78.1 returned `PASS_ALPINE_3_24_2_MUSL_BUSYBOX_SINGLE_PROCESS`, SSH exit `0`, successful cleanup reported. This proves one dynamically linked Alpine musl+BusyBox invocation against the stock Linux 3.0.35 kernel; it does **not** prove that KOReader's GNU/glibc runtime works, that the e-ink display works, or that independent restore is available.

## Purpose

Inspect the **existing local R13 KOReader stage** for ARM ELF entrypoint candidates (especially LuaJIT) without executing anything. For candidates, report only stage-relative names, ARM EABI/float flags, ELF type and a restricted interpreter category. Avoid system-private paths, raw library files and full manifests in GitHub.

This is a candidate inventory only, not a pinned R26 content-hash revalidation or full dependency closure. The R13 rootfs stage can be different from the fresh Alpine 3.24.2 minirootfs already tested. Do not substitute a newly downloaded rootfs or the installed Kindle OS.

## macOS next test

Unzip `pw3-r3877-79-koreader-entrypoint.zip` under `~/Downloads`, then:

```zsh
cd ~/Downloads/pw3-r3877-79
shasum -a 256 -c SHA256SUMS_R3877_79.txt
python3 -B -m unittest -q test_r3877_79.py

STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
if [ ! -d "$STAGE" ]; then
  echo 'R3877_79_STAGE_NOT_FOUND: do not replace with Kindle root or live mounts'
else
  setopt pipefail
  python3 -B pw3_r3877_79_koreader_entrypoint.py \
    --stage "$STAGE" \
    --acknowledge-local-readonly-stage-inspection \
    | tee r3877_79_result.json
  printf 'R3877_79_EXIT_CODE=%s\n' "$?"
fi
```

The scan **always exits 2** and retains `NOT_BOOTABLE`, including with a candidate found. Share only the JSON summary, preferably after reviewing the handful of stage-relative candidate paths. If the stage is unavailable, stop and report that instead of scanning an unrelated path. It reads local ELF headers only, skips symlinks, does not use `ldd`, does not execute ELF files, and has no network or device functionality.

## Follow-up

If a suitable staged **native LuaJIT** ELF exists, the next separate task is to identify its pinned interpreter and dependency tree and plan a one-shot non-graphical `-v` or equivalent test from a temporary Kindle RAM-backed filesystem. No KOReader GUI, framebuffer, input, Wi-Fi, boot hooks, mount, chroot or changes to the stock system are authorized by this milestone. A library named `libluajit` by itself is not an executable entrypoint. If only libraries are identified, stop and determine which binary the QEMU-stage harness actually runs.
