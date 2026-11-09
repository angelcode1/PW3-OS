# PW3 R3877.56 — BusyBox installed package record and package-generated applet list

**Research/education only. `NOT_BOOTABLE` is immutable.** This stage does not contact the Kindle, execute ARM guest code, write firmware, or attempt boot/recovery. The default command never starts Docker. It is safe to discontinue at any HOLD.

## Why

The user-reported Mac R3877.55 run passed the pinned Alpine BusyBox 1.37.0-r31 upstream-source and configuration audit (five public Git blobs). The source recipe disables the `seedrng` applet. R3877.54 had already checked pinned ARMv7 BusyBox and musl-loader ELF identities, but source version is **not installed package identity**, and ELF strings are not compiled-app inventory evidence.

This step examines a cached immutable Alpine ARMv7 parent image in a **stopped-only** Docker guest and reads its `/lib/apk/db/installed` package record and `/etc/busybox-paths.d/busybox` package-generated applet list. It also revalidates the exact BusyBox ELF SHA-256 (`df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c`) and musl loader ELF SHA-256 (`2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990`), interpreter linkage, and selected entropy indicators using the byte-pinned R3877.48/R3877.54 auditors.

**Important distinction:** The APK-generated applet-path file is metadata produced during Alpine packaging, *not* an independent inspection of the compiled applet dispatch table and not proof that any applet was executable on Linux `3.0.35-lab126`. It may be absent from the cached image; absence is HOLD. A matching package version does not prove a reproducible build of the pinned source recipe. This auditor never prints the entire package database or complete applet list.

## Mac test commands

```zsh
mkdir -p ~/Downloads/pw3-r3877-56
unzip -oq ~/Downloads/pw3-r3877-56-busybox-package-inventory.zip -d ~/Downloads/pw3-r3877-56
cd ~/Downloads/pw3-r3877-56
shasum -a 256 -c SHA256SUMS_R3877_56.txt
python3 -B -m unittest -q test_r3877_56.py

# Expected deliberate HOLD / exit 2, zero Docker access.
python3 -B pw3_r3877_56_busybox_package_inventory.py > r3877_56_preflight.json
printf 'PREFLIGHT_EXIT_CODE=%s\n' "$?"

# Explicit authorization for STOPPED-only, networkless cached image inspection.
setopt pipefail
python3 -B pw3_r3877_56_busybox_package_inventory.py \
  --authorize-stopped-image-audit | tee r3877_56_result.json
printf 'R3877_56_EXIT_CODE=%s\n' "$?"
```

The original image **must** match `sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a`. The disposable guest uses `--network none --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 32` and a benign `/bin/true` entrypoint that is **never started**. The script checks stopped isolation after create and each copy, removes the guest, then checks parent-image identity again. No image pull, update, run, privileged containers, volumes, or host mounts. Docker `create` and `cp` affect only the temporary container and local Mac files, not the original image.

Successful narrow result **only if all actual checks pass**: `PASS_PINNED_BUSYBOX_APK_METADATA_AND_PACKAGE_GENERATED_APPLET_LIST_ONLY`, exit `0`. If the APK version/arch is not pinned, applet file missing, checksum differs, image changes, or cleanup cannot be verified: `HOLD`, exit `2`. Do not patch or recreate the original parent image to force a PASS.

The CLI also has a local-only mode if the four source files have already been collected through a separate authorized procedure:

```zsh
python3 -B pw3_r3877_56_busybox_package_inventory.py \
 --installed-db /path/to/installed.db \
 --applet-list /path/to/applet-list \
 --busybox /path/to/busybox \
 --loader /path/to/loader
```

## What remains HOLD

- The applet listing is packaging metadata, not a direct compiled applet-table disassembly or executed feature test.
- The exact installed BusyBox binary-to-source reproducibility is not verified.
- Generic `syscall` import means direct entropy syscalls cannot be ruled out.
- Neither `/dev/urandom` string nor applet-list content proves actual `ENOSYS` fallback behavior.
- Vendor kernel dispatch and musl compatibility on the actual Kindle are untested.
- Recovery, boot, and firmware changes remain prohibited: `NOT_BOOTABLE`.

**Send `r3877_56_result.json` and `R3877_56_EXIT_CODE`. Do not share the full `/lib/apk/db/installed` database.**
