# R3877.82 — KOReader LuaJIT GNU symbol versions, ARM attributes and $ORIGIN

**Research and educational use only.** `HOLD / NOT_BOOTABLE`. No Kindle connection, native ELF execution, flashing, mount, chroot, boot hook, device/display action, or cleanup/pruning of the staged rootfs.

## Why this test

R3877.81 (user-reported) confirmed exactly one regular file for LuaJIT's interpreter `/lib/ld-linux.so.3` and four `DT_NEEDED` providers, all ARM EABI5 with the explicit **soft-float ELF flag**. The providers form the following candidate transitive chain:

- `libm.so.6 -> libc.so.6`
- `libdl.so.2 -> libc.so.6, ld-linux.so.3`
- `libgcc_s.so.1 -> libc.so.6`
- `libc.so.6 -> ld-linux.so.3`

LuaJIT is `opt/koreader-compat/app/luajit` and its known provider files are under `opt/koreader-compat/gnu/lib/`. The previous report classified its RPATH as `VARIABLE_EXPANSION_REVIEW_NEEDED`, without resolving `$ORIGIN`. Three glibc DSOs contain `PT_INTERP` metadata. **That segment is not by itself evidence that a DSO is incompatible**: it is mainly relevant to directly executing an ELF; only real runtime loader resolution can settle the loaded-library behavior. Retain it as a warning, not an automatic boot blocker.

The earlier R26 catalog reported 1,448 regular files while R3877.81's scanner counted 1,446. Different scan scopes or stage changes are both possible; this tool **does not** authenticate the existing stage against the R26 hashes and cannot settle the discrepancy.

## What it checks (host-only)

- Reuses the **unchanged, SHA-pinned R3877.81 source** to select one ordinary-file provider for each direct and transitive `DT_NEEDED` name. Refuses missing, duplicated or symlink-only providers and any expected provider not in the staged GNU library directory.
- Parses `.ARM.attributes`, including `Tag_ABI_VFP_args = 28` for the entrypoint and five provider objects. A missing or ambiguous attribute remains unverified rather than silently assuming the hard/soft-float calling convention. The ELF `e_flags` status is preserved separately.
- Parses GNU `.gnu.version_r` and `.gnu.version_d` section records and reports static **version-name** matches, missing versions or absent version-definition tables. Name presence does **not** prove per-symbol binding, relocations or runtime loader compatibility.
- Resolves restricted `$ORIGIN/...` RPATH entries relative to the original stage's LuaJIT directory, detecting whether they point at the staged `gnu/lib` directory and refusing unsafe/escaping paths. Raw RPATH values and Mac absolute paths are not printed.

The scanner uses the Python standard library only. It never invokes `readelf`, `ldd`, `ssh`, `mount`, `chroot` or the ELF loader. Stage files are opened read-only, with no-follow checks for all six known objects.

## Run on your Mac

This package unpacks into `pw3-r3877-82/` under `~/Downloads`. The original R13 stage is required, **not** the Alpine 3.24.2 minirootfs archive.

```zsh
cd ~/Downloads
unzip -oq pw3-r3877-82-glibc-symbol-version-audit.zip -d ~/Downloads
cd ~/Downloads/pw3-r3877-82
shasum -a 256 -c SHA256SUMS_R3877_82.txt
python3 -B -m unittest -q test_r3877_82.py

STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
if [ ! -d "$STAGE" ]; then
  echo 'R3877_82_STAGE_NOT_FOUND'
else
  setopt pipefail
  python3 -B pw3_r3877_82_version_abi_audit.py \
    --stage "$STAGE" \
    --acknowledge-mac-only-review \
    | tee r3877_82_result.json
  printf 'R3877_82_EXIT_CODE=%s\n' "$?"
fi
```

Exit code **2** with `HOLD / NOT_BOOTABLE` is intentional even when static checks succeed. Send only the printed JSON after review. `result.json` contains bounded stage-relative objects, ABI tags and GNU version names, not local directory names or file hashes; keep all proprietary binaries, complete stage, device images and private R26 catalog off public GitHub.

## Next decision

If the `$ORIGIN` search path reaches the selected GNU directory, no ARM VFP calling-convention conflicts appear, and all available GNU version names match, the next **separately authorized** experiment can be an attended, one-shot glibc **loader resolution** test using a checksum-pinned temporary bundle in an existing executable Kindle tmpfs. The first live loader test should not start the KOReader GUI, change init, interrupt firmware services, mount any partition, or replace the stock Kindle UI.

Missing attribute records, version tables, untrusted RPATH, or mismatched version names remain explicit reasons to investigate rather than guess. Full symbol binding and old-kernel runtime compatibility will remain unverified until the actual loader is exercised. Standalone boot and independent recovery remain unverified in all cases.

## References

- Arm ELF ABI build attribute `Tag_ABI_VFP_args`: https://github.com/ARM-software/abi-aa/blob/main/addenda32/addenda32.rst
- GNU ELF dynamic loader, `$ORIGIN`, `--list`: https://man7.org/linux/man-pages/man8/ld.so.8.html
- R3877.81 host audit: `research/r3877-81/README.md` in the PW3-OS research branch.
