# PW3-OS R3877.51 — Selected live stock-kernel metadata, read-only

**Research/education only. Immutable `NOT_BOOTABLE`.** The R3877.50 result verifies 14/14 observed QEMU syscall names against a *public-source* ARM EABI header and `calls.S` table; it does not verify what the running Kindle's vendor kernel implements.

This milestone does **not** execute new binaries on Kindle or alter firmware, kernel, bootloader, partitions, root filesystem, services, power settings or hardware configuration. The optional, explicitly authorised one-time SSH collection **does execute existing stock shell/uname/awk/zcat/gzip/cat utilities to read metadata**. Do not use this on a device you do not administer. Never run it during an update/firmware operation. No raw kernel addresses, raw `/proc/kallsyms` content, full config, secrets, device serial, or host identifiers are output.

## What is checked

- `uname -r` must be `3.0.35-lab126`; `uname -m` must be `armv7l`.
- Up to 18 configuration flags are read from `/proc/config.gz`, if stock `zcat` or `gzip` is available, or `/proc/config` as fallback. Only `y`, `m`, `n`, or `UNKNOWN` are published.
- Fourteen selected handler **symbol-name** presences from `/proc/kallsyms` are reduced to `PRESENT`, `ABSENT`, `UNKNOWN` by stock AWK; addresses never leave the Kindle.
- A symbol absent from kallsyms **does not prove an absent syscall**; aliases, compiled symbols, hidden names and disabled kallsyms can all produce false negatives.
- The input parser rejects unexpected lines, duplicate fields, oversized inputs, unexpected values and mismatched release/architecture.

A possible `PASS_SELECTED_LIVE_KERNEL_CONFIG_AND_SYMBOL_NAMES_METADATA_ONLY` proves that the chosen stock kernel metadata was observed and parsed. It **cannot** authenticate the running kernel binary to the mirror, verify dispatch-table wiring, demonstrate musl syscall semantics, attest hardware drivers or permit OS boot. If kernel config is unavailable the result is `HOLD`, and there is no automatic workaround or new kernel read.

## Verify release locally (no SSH)

```zsh
mkdir -p ~/Downloads/pw3-r3877-51
unzip -oq ~/Downloads/pw3-r3877-51-live-kernel-metadata.zip -d ~/Downloads/pw3-r3877-51
cd ~/Downloads/pw3-r3877-51
shasum -a 256 -c SHA256SUMS_R3877_51.txt
python3 -B -m unittest -q test_r3877_51.py
python3 -B pw3_r3877_51_kernel_metadata.py > r3877_51_preflight.json
print "R3877_51_PREFLIGHT_EXIT_CODE=$?"  # expected 2 / HOLD, no SSH
```

## Explicit optional one-time stock-Kindle read-only metadata collection

Set the **actual known SSH target** of your own Kindle. This is NOT the IP address of another device. The user must decide whether to run these stock-system reads:

```zsh
cd ~/Downloads/pw3-r3877-51
KINDLE_SSH='root@YOUR_KINDLE_IP'
setopt pipefail
python3 -B pw3_r3877_51_kernel_metadata.py \
  --authorize-readonly-kindle-ssh \
  --target "$KINDLE_SSH" | tee r3877_51_result.json
print "R3877_51_EXIT_CODE=$?"
```

`ssh` is invoked as a single argument vector, with `BatchMode=yes`, strict known-host verification, no prompt for unknown host keys, and a bounded 45-second timeout. The local program passes an embedded fixed read-only shell script into a single `sh -s` session. It neither uses `su` nor installs a binary or remote script file. In the report, `physical_device_access_performed=true` and `kindle_ssh_sessions=1` on a complete successful receipt. On SSH failure it reports `UNKNOWN_ON_FAILURE` rather than guessing if a session was established. The target address and SSH stderr are not included in output. This is not an attestation that a compromised host could not change state; it describes the requested operations.

If you previously acquired a sanitized R51 receipt from the same script, you can instead run an **entirely offline parse**:

```zsh
python3 -B pw3_r3877_51_kernel_metadata.py \
  --input-receipt path/to/selected-receipt.txt | tee r3877_51_offline.json
```

Do **not** collect raw `/proc/kallsyms`, full kernel images, `/dev/mmcblk*` or boot areas, or run `dd`, mounts, debug interfaces or custom ARM executables for this milestone.

## Provenance limitations and next gate

Public reference: `katadelos/linux-3.0.35-lab126` at commit `7ac2585f384573da8cbdcc987a3503e2e6ff1fb4`; public ARM header blob `2c04ed5efeb50707ac3353958434d37691841839` and dispatch table blob `80f7896cc0164ad6f74469f1e777b90c1f306443`. Previous R3877.21 user metadata reported basic syscall-related Kconfig features as built-in. This R51 test independently reads selected **current** flags if available; it does not replace source/build provenance. A matching release or kallsyms-name set is not a kernel binary hash, trusted source attestation, or a functional syscall test. Even on PASS, `actual_vendor_syscall_dispatch_verified=false` and `running_kernel_matches_public_source_verified=false` remain mandatory.

**Authoring validation:** synthetic host-only Python tests; shell syntax check; no physical Kindle connection. GitHub CI must never invoke `--authorize-readonly-kindle-ssh` or contact a device.
