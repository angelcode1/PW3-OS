# R3877.80 — KOReader LuaJIT glibc dependency preflight (Mac-only)

**Research and educational purposes only. `HOLD / NOT_BOOTABLE`.** No Kindle network connection, program execution, mount, chroot, boot hook, firmware write, file pruning or live loader invocation is performed by this preflight.

## Confirmed input

R3877.79 user-provided offline scan reported one native candidate at `opt/koreader-compat/app/luajit`: ELF32 ARM EABI5 executable, glibc ARM loader, PT_DYNAMIC present, ARM ELF hard-float bit absent. That **does not** prove soft-float ABI: the static check must read the exact `e_flags`. The stage reported 1,446 regular files, against 1,448 cataloged previously by R26. These are distinct observations, not proof of a two-file deletion or proof of content preservation.

R3877.78.1 user-provided *device* test previously verified one Alpine 3.24.2 ARMv7 musl loader + BusyBox `echo` invocation, SSH exit zero and temporary cleanup. That says nothing about the separate KOReader **glibc** runtime or its float calling convention.

## Purpose

Inspect **only the original local R13 staged rootfs**, extracting the fixed LuaJIT executable's ELF32 ARM EABI flags, exact glibc interpreter (`PT_INTERP`), direct `DT_NEEDED` list and presence of `RPATH`/`RUNPATH`. Search the staged filesystem for objects whose **basenames** match the interpreter or direct dependencies, counting regular files and symlinks without following the symlinks. These are source *candidates only*, not a resolved runtime loader graph.

The tool intentionally avoids the original application's GUI, devices, LuaJIT execution, third-party `ldd`, all network connections and full path catalogs. It does not decode `.ARM.attributes` or GNU symbol versions; it therefore cannot conclude complete float ABI compatibility, glibc version compatibility or full dependency closure. Existing R26/R40 source-pinned stage hash verification remains an independent required gate.

## On your Mac (zsh)

```zsh
cd ~/Downloads
unzip -oq pw3-r3877-80-luajit-abi-audit.zip -d ~/Downloads
cd ~/Downloads/pw3-r3877-80

shasum -a 256 -c SHA256SUMS_R3877_80.txt
python3 -B -m unittest -q test_r3877_80.py

STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
if [ ! -d "$STAGE" ]; then
  echo 'R3877_80_STAGE_NOT_FOUND — stop; do not substitute an unrelated stage'
else
  setopt pipefail
  python3 -B pw3_r3877_80_luajit_abi_audit.py \
    --stage "$STAGE" \
    --acknowledge-host-only-elf-audit \
    | tee r3877_80_result.json
  printf 'R3877_80_EXIT_CODE=%s\n' "$?"
fi
```

A successfully parsed audit still returns exit code **2**, `HOLD`, `NOT_BOOTABLE` and a `review` field. A refusal returns `HOST_ELF_OR_STAGE_REVIEW_REFUSED` with no `review`. Do not bypass the refusal by copying a binary into `/mnt/us`, overwriting the stock interpreter or running a GUI.

## Next decision

- If exact interpreter and directly required library names have staged candidates, **separately** verify actual target glibc loader, symbol versions, floating-point ABI attributes and all transitive dependencies before constructing any temporary rootless LuaJIT test.
- If any object is missing, a symlink-only candidate, or the ABI remains ambiguous, continue offline investigation. Do **not** use the Alpine musl loader as a substitute for a glibc-built LuaJIT.
- If the stage's file count differs from R26, do not infer deleted files; the full original R26 SHA verification must be repeated separately before asserting identical stage provenance.

The next eventual device experiment, if approved after these gates, must be a single non-GUI LuaJIT version command in an existing executable tmpfs with no framebuffer, input, wireless changes or startup modifications.

**Standalone boot and independent physical restore remain unverified.**
