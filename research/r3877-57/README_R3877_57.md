# PW3 R3877.57 — pinned BusyBox ELF applet-name array evidence

**Research and educational purposes only. `NOT_BOOTABLE` remains immutable.**

## Why

The user-reported R3877.56 Mac result matched the pinned Alpine `busybox` package `1.37.0-r31` (`armv7`), verified `/bin/busybox` and musl interpreter hashes, and found 304 entries in Alpine's **package-generated** applet path list: `ash` present, `seedrng` absent. That metadata is not itself proof of bytes in the compiled executable.

Public BusyBox `1_37_0` `applets/applet_tables.c` (Git blob `66ef7e4ac349d0006015d1b39c8021b6e5a3ce86`) sorts applet names with `strcmp` and emits a NUL-separated array named `applet_names[]`. `libbb/appletlib.c` (Git blob `d9cc48423b35f5e5e4d7ae61cf3664a3d4233187`) references that array for applet lookup. These public source identities were checked through GitHub. They are not build provenance for the installed binary.

## Narrow test

1. Recheck the immutable R3877.48, R3877.54 and R3877.56 auditor source SHA-256 pins.
2. Verify pinned Alpine image identity and stopped-only hardened container: no networking, no host mounts or devices, read-only rootfs, capabilities dropped, no-new-privileges and PID limit 32.
3. Extract four allowlisted files **without starting the container**: `/bin/busybox`, `/lib/ld-musl-armhf.so.1`, `/lib/apk/db/installed`, `/etc/busybox-paths.d/busybox`. Verify exact BusyBox/loader SHA-256, ELF interpreter and APK package version again using unchanged R3877.56 code.
4. Derive the exact sorted NUL-delimited 304-app name array (including the extra C-string terminator) from the APK-generated applet list, pinned by SHA-256 `ad43f2888aa6679930812faef33672c45e98021d3be0d0ed08d257c1d957a968`.
5. Require **exactly one full match in file-backed ELF32 ARM PT_LOAD bytes**. No match, multiple matches, or unexpected ELF architecture/layout -> HOLD. Do not search arbitrary appended overlay bytes.
6. Remove the stopped container, verify absence and confirm the original cached image ID unchanged. Any failure retains HOLD.

A PASS would be `PASS_PINNED_BUSYBOX_ELF_APPLET_NAME_ARRAY_MATCH_ONLY`. It would confirm matching **loadable ELF applet-name data**, a stronger result than package metadata alone; it does **not** prove the function pointer dispatch table, actual applet execution, the entire compiled applet inventory, entropy fallback, musl target compatibility or source/binary reproducibility. An absent exact array is not proof the applet is absent: linker optimization or layout differences may require another analysis. **Do not modify the binary to force a pass.**

## Mac commands

Download and extract `pw3-r3877-57-elf-applet-name-array.zip` to `~/Downloads/pw3-r3877-57`:

```zsh
cd ~/Downloads/pw3-r3877-57
shasum -a 256 -c SHA256SUMS_R3877_57.txt
python3 -B -m unittest -q test_r3877_57.py
```

Default, no Docker, deliberate HOLD/exit 2:

```zsh
python3 -B pw3_r3877_57_elf_applet_names.py > r3877_57_preflight.json
printf 'R3877_57_PREFLIGHT_EXIT_CODE=%s\n' "$?"
```

Optional explicitly authorised **stopped-only** inspection, no ARM execution:

```zsh
setopt pipefail
python3 -B pw3_r3877_57_elf_applet_names.py \
  --authorize-stopped-image-audit | tee r3877_57_result.json
printf 'R3877_57_EXIT_CODE=%s\n' "$?"
```

The result JSON does not include raw package databases, executable bytes, applet names, host paths or kernel configuration. A successful narrow result and exit 0 are **not known** until actually executed against the pinned local image. GitHub Actions runs only the **synthetic** 40 tests and preflight—never Docker or Kindle.

Stop and share `r3877_57_result.json` and the exit code. A HOLD is useful evidence; it does not authorize bypassing any check or deploying to Kindle.
