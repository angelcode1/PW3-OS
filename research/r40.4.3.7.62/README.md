# R40.4.3.7.62 — Pinned public PW3-family Linux 3.0.35 kernel config reference

**Research and educational use only. NOT_BOOTABLE.** This is new public-source evidence, not execution of the original stage, alternate loader, QEMU or physical Kindle. No stage writes, interpreter mappings, boot, firmware action or pruning.

## Source and scope
The public community mirror [katadelos/linux-3.0.35-lab126](https://github.com/katadelos/linux-3.0.35-lab126) describes itself as a GPL release re-upload. It identifies PW3 as part of the supported device family and `imx60_wario_defconfig` as that family's reference configuration. The original mirror is not an independently authenticated device firmware source.

Commit `7ac2585f384573da8cbdcc987a3503e2e6ff1fb4`; file `arch/arm/configs/imx60_wario_defconfig`; expected Git blob SHA1 `bbc2f92713d05dfd6ea52973fc7d958e49fa6464`; byte count `59582`. The downloadable script verifies the entire file by this blob identifier **before** parsing; it never executes or modifies it.

## Public configuration flags checked
Enabled: `CONFIG_ARM`, `CONFIG_MMU`, `CONFIG_ARCH_MXC`, `CONFIG_ARCH_MX6`, `CONFIG_AEABI`, `CONFIG_BINFMT_ELF`, `CONFIG_FUTEX`, `CONFIG_EPOLL`, `CONFIG_EVENTFD`, `CONFIG_INOTIFY_USER`, `CONFIG_ARM_THUMB`, `CONFIG_VFP`, `CONFIG_VFPv3`, `CONFIG_NEON`, `CONFIG_HIGH_RES_TIMERS`.

Explicitly not set: `CONFIG_OABI_COMPAT`, `CONFIG_BINFMT_MISC`, `CONFIG_ARM_THUMBEE`, `CONFIG_SECCOMP`, `CONFIG_FHANDLE`, `CONFIG_SMP`.

Not declared in this reference: `CONFIG_TLS_REG_EMUL`, `CONFIG_KUSER_HELPERS`. Absence of a declaration is not proof the corresponding runtime facility is absent or disabled.

The 23 tracked keys describe a **public reference defconfig**, not the configuration of a specific running Kindle. No kernel ABI, ARM TLS, actual PT_INTERP path, weak symbol resolution, device recovery or boot is verified. Preserve all earlier R3758/R3760 inventory and archive checks and original R3745 HOLD.

## Download and use on Mac
The downloadable `pw3-r3762-public-kernel-reference-readonly.zip` includes the runnable Python 3 source, 32 synthetic tests, README, release metadata, workflow *example* and full SHA256SUMS. Package SHA256: `62628fb7abbf1ef97fe702c5a4d8463e925f21a0bf86a7ca56fa4e6d7118eeeb`. 32/32 standalone tests, all five manifest hashes and clean ZIP extraction verified. Earlier 972 lineage tests were **not** rerun in this independent milestone.

```sh
mkdir -p "$HOME/Downloads/pw3-r3762"
cd "$HOME/Downloads/pw3-r3762"
unzip -o "$HOME/Downloads/pw3-r3762-public-kernel-reference-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r4043762.py' -v
curl --fail --location --silent --show-error \
  'https://raw.githubusercontent.com/katadelos/linux-3.0.35-lab126/7ac2585f384573da8cbdcc987a3503e2e6ff1fb4/arch/arm/configs/imx60_wario_defconfig' \
  --output imx60_wario_defconfig
python3 -B R4043762-PUBLIC-WARIO-KERNEL-REFERENCE-READONLY.py \
  --reference-defconfig "$PWD/imx60_wario_defconfig"
```

A pin mismatch, missing/symlinked file, malformed options or incompatible header emits HOLD without a bypass. Report the JSON `result`, `reference_feature_groups`, and any `hold_category`; do not upload the user's private R13 stage. There is no R3762 GitHub Actions PASS: runnable code and the example workflow are in the downloadable ZIP, and this GitHub directory holds **release documentation only**.

**NOT_BOOTABLE.**
