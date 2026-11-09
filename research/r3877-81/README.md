# R3877.81 — KOReader LuaJIT transitive glibc ELF preflight (Mac-only)

**Research / educational purposes only. `HOLD / NOT_BOOTABLE`.** This is a read-only local ELF metadata audit, not an install or Kindle device test.

## Device and application evidence already established

- R3877.77: physical Kindle ran a minimal static ARM EABI5 `write`/`exit` process from a pre-existing executable tmpfs. No boot changes.
- R3877.78.1: physical Kindle ran pinned Alpine 3.24.2 armv7 **musl** loader plus BusyBox echo. The tmpfs cleanup was reported successful. This does **not** validate glibc or KOReader.
- R3877.79: Mac found one staged native LuaJIT executable at `opt/koreader-compat/app/luajit`, an ARM EABI5 glibc ELF, and 83 ELF objects overall.
- R3877.80: Mac identified `e_flags=0x05000200` (explicit ARM EABI soft-float), interpreter `/lib/ld-linux.so.3`, direct `DT_NEEDED` names `libm.so.6`, `libdl.so.2`, `libgcc_s.so.1`, `libc.so.6`, and RPATH present / RUNPATH absent. Each of the four needed names and `ld-linux.so.3` had one ordinary-file name match in the staged tree. Name matches do not verify dynamic loader resolution or any symbol versions. The scan counted 1,446 regular files vs R26's recorded 1,448; stage identity is not reverified.

## New R3877.81 test

The Python standard-library-only tool reads the **same user-staged R13 rootfs on the Mac**, not the Kindle. It parses actual ARM ELF32 EABI5 program/dynamic headers of the selected LuaJIT executable and the uniquely matched loader/direct and transitive dependencies. It checks for additional names required by those libraries, incompatible explicit float ABI flags, unexpected interpreters, wrong ELF types, symlink-only providers, duplicated provider basenames, and classifies RPATH/RUNPATH without disclosing their raw absolute values.

The result contains stage-relative candidate locations and their controlled dependency names, but never file bytes or paths outside the stage. **Do not upload raw libraries, firmware, R26 inventory, original rootfs, private SHA lists, or device images to GitHub.** Review the summary before sharing.

This static name-based exploration is **not** a proof of the real glibc loader's directory search, symbol-version compatibility, `.ARM.attributes` ABI tags, stage fidelity against R26, software execution, KOReader UI, display/input support, standalone boot or independent restore.

## Next action on the Mac

Extract the ZIP under `~/Downloads`, then run:

```zsh
cd ~/Downloads
unzip -oq pw3-r3877-81-glibc-closure.zip -d ~/Downloads
cd ~/Downloads/pw3-r3877-81
shasum -a 256 -c SHA256SUMS_R3877_81.txt
python3 -B -m unittest -q test_r3877_81.py

STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
if [ ! -d "$STAGE" ]; then
  echo 'R3877_81_STAGE_NOT_FOUND: stop, do not substitute a live device path'
else
  setopt pipefail
  python3 -B pw3_r3877_81_glibc_closure.py \
    --stage "$STAGE" \
    --acknowledge-host-only-glibc-dependency-audit \
    | tee r3877_81_result.json
  printf 'R3877_81_EXIT_CODE=%s\n' "$?"
fi
```

Expected result is *always* `HOLD` and exit code **2**, even when the dependency-name graph resolves. If the report has `review.unresolved_or_ambiguous` entries, preserve them verbatim for the next analysis. A report with `all_needed_names_unique_regular=true` still does **not** authorize a live LuaJIT experiment. It only establishes a narrower set of candidate glibc files and unmet runtime checks.

### Current safety boundaries

- No device connection, root SSH, e-ink access, application execution, symlink traversal, external commands, or stage modification.
- No chroot, mount, partition/bootloader changes, firmware writes or startup modifications.
- Source/host CI tests synthetic-only and do not download proprietary binaries or contact the Kindle.
- Before a future device test: separately verify symbol/version requirements and a bounded, checksum-pinned set of stage-local ELF files, including the loader. Any device execution must be single-shot in existing executable tmpfs, with explicit user authorization, cleanup checks and stock OS/SSH retained.
