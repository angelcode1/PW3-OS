# PW3 R3877.78 — one-shot Alpine musl runtime against Linux 3.0.35

> **R3877.78.1 correction:** The original validator expected the wrong ARMv7
> libc SONAME. Use [the corrected archive-only procedure](README_R3877_78_1.md)
> with the existing downloaded rootfs before any new Kindle execution.


**Research only. Independent boot is still `NOT_BOOTABLE`.** This performs one
manually authorized ARMv7 musl/BusyBox application command using only an
**existing** executable tmpfs on the live Kindle. It does **not** mount, chroot,
replace stock services, flash, alter boot settings, use UART, or write files to
persistent Kindle storage. The Kindle's original UI and SSH remain in place.

## Evidence leading to this test

R3877.77, as reported by the operator, passed on the real Kindle: a 312-byte
static ELF32 ARM EABI5 program performed `write` and `exit` using the stock
Linux 3.0.35-lab126 kernel. The reported SSH exit code was 0 and tmpfs cleanup
completed. That is native ELF/syscall evidence, **not** evidence that Alpine
musl's loader, hard-float ABI or BusyBox can run.

## Reproducible Alpine input

This test uses the **exact** Alpine v3.24.2 armv7 minirootfs tarball pinned by
Inkwell's own `tools/fetch.sh`. Do not replace it with an arbitrary newer
release. Download it on your Mac; the Kindle is never asked to download it.

Official Alpine archive directory:
https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/armv7/
Inkwell published input pin:
https://github.com/pragyaangaur/Inkwell/blob/main/tools/fetch.sh

```zsh
mkdir -p ~/Downloads/pw3-r3877-78
unzip -oq ~/Downloads/pw3-r3877-78-macos-musl-smoke.zip -d ~/Downloads/pw3-r3877-78
cd ~/Downloads/pw3-r3877-78

shasum -a 256 -c SHA256SUMS_R3877_78.txt
python3 -B -m unittest -q test_r3877_78.py

curl -fL --retry 2 \
  'https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/armv7/alpine-minirootfs-3.24.2-armv7.tar.gz' \
  -o alpine-minirootfs-3.24.2-armv7.tar.gz.partial
mv alpine-minirootfs-3.24.2-armv7.tar.gz.partial alpine-minirootfs-3.24.2-armv7.tar.gz

printf '%s  %s\n' \
  '5552f1ef2398cee46ef2cf733f8f1258f39a77ad065dfd47282fc0df9fe1976c' \
  'alpine-minirootfs-3.24.2-armv7.tar.gz' \
  | shasum -a 256 -c -

# No-opt-in preflight: does not read rootfs tar and makes no SSH connection.
python3 -B pw3_r3877_78_musl_runtime.py

# Explicitly opt into one brief live process. No automatic retries.
setopt pipefail
python3 -B pw3_r3877_78_musl_runtime.py \
  --rootfs-tar alpine-minirootfs-3.24.2-armv7.tar.gz \
  --acknowledge-single-process-mac-and-kindle-tmpfs \
  --target root@192.168.8.102 \
  --port 2222 \
  | tee r3877_78_result.json
printf 'R3877_78_EXIT_CODE=%s\n' "$?"
```

The pinned tar is **not** extracted onto the Mac or Kindle as a complete root
filesystem. The Python code reads the archive, validates the SHA-256 pin,
extracts into memory only `/lib/ld-musl-armhf.so.1` (following a narrowly
bounded in-archive symlink) and `/bin/busybox`, and validates:

- ELF32 little-endian ARM EABI5 and hard-float metadata on both objects;
- BusyBox requests `/lib/ld-musl-armhf.so.1` as interpreter;
- BusyBox has exactly one shared-library dependency:
  `libc.musl-armv7.so.1`;
- the staged tar contains exactly three regular files: the loader under two
  expected names and BusyBox. No archive paths, symlinks or permissions from
  the rootfs tar are carried into the staging tar.

The live SSH command refuses unless the target is the known Kindle kernel and
architecture, and an already mounted writable tmpfs at `/tmp`, `/run` or
`/dev/shm` lacks the `noexec` flag. The script creates a unique temporary
directory in that **RAM-backed** filesystem, receives only the three controlled
members, verifies SHA-256 and length for each, and directly invokes:

```
LD_LIBRARY_PATH="$work" "$work/ld-musl-armhf.so.1" \
  "$work/busybox" echo R3877_78_MUSL_BUSYBOX_OK
```

It removes the temporary objects and directory before successful return. A
transport interruption or failure can prevent cleanup, so the report does
**not** claim cleanup success on any nonzero path. Never retry blindly.

A successful result is `PASS_ALPINE_3_24_2_MUSL_BUSYBOX_SINGLE_PROCESS` / exit
0, **with `immutable_hold: NOT_BOOTABLE`**. Other results remain HOLD / exit
2. Do not interpret a passing `echo` command as proof of full Alpine, KOReader,
multithreaded TLS, graphics, mounting, real e-ink interaction, independent
recovery, or reliable stock rollback. Both inputs and outputs stay private.

No firmware binary is added to the public repository. The source and
synthetic tests may be run by GitHub Actions **without SSH, any device access,
or rootfs downloading**.
