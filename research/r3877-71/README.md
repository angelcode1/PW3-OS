# R3877.71 — device-derived boot evidence and recovery hold

**Research/educational use only. NOT_BOOTABLE remains mandatory.** This directory
records user-reported live Kindle evidence and offers a local read-only structural
verifier. This repo contains **no original firmware images**, partition contents,
private checksums, UUIDs, passwords, serial numbers or SSH configuration.

## Established observations

- Authorized root SSH identified a PW3 running 3.0.35-lab126 on armv7l.
- The eMMC user area has 7,634,944 512-byte sectors; p1 starts at sector 65,536.
  The initial 32 MiB Mac copy matches the device SHA-256, per operator output.
- The 32 MiB image has two U-Boot-format ARM Linux kernels at 0x41000
  (normal) and 0xE41000 (diagnostics), with valid header and payload CRC32.
- p1 (450 MiB) and p2 (64 MiB) were each compared to a live Kindle SHA-256
  value with matching results. Both have EXT3 filesystem signatures. The p2
  userspace is consistent with Lab126 diagnostics, but it has not been booted.
- eMMC boot0 and boot1 (4 MiB each) matched their live SHA-256 values, per
  operator output. boot0 contains U-Boot 2009.08-lab126 strings and commands
  for both kernels; boot1 is zero-filled.
- p3 (persistent state) and p4 (user storage) were not backed up.

These are backups of the **current device state**, not independently authenticated
factory stock. A matching digest or kernel CRC does not prove recoverability.
No serial access, forced diagnostics boot, restore, flash, vendor-kernel
compatibility or replacement OS boot has been tested.

## Mac-only verification

Keep the image originals outside GitHub, in ~/Downloads/pw3-device-backup.
Copy the two Python files from this directory to a local folder, then run:

    python3 -B -m unittest -q test_r3877_71.py
    python3 -B pw3_r3877_71_offline_verify.py \
      --image-dir "$HOME/Downloads/pw3-device-backup" \
      --acknowledge-readonly-offline-images > r3877_71_report.json
    printf 'R3877_71_EXIT_CODE=%s\n' "$?"
    cat r3877_71_report.json

It reads four required fixed filenames and p1 if available; if p1 is missing,
the report explicitly says p1 was not checked and the image set is incomplete.
It never outputs private paths, hashes, UUIDs or file content. It performs
no Kindle SSH, network, mounts, writes or guest execution. It **always exits 2**
with HOLD and NOT_BOOTABLE, even after successful structural checks.

## Next recovery gate

1. Retain private duplicate copies and checksum manifests off public GitHub.
2. Test non-destructive recovery-console access using suitable **1.8 V**
   hardware, initially receive-only. Do not connect 3.3 V/5 V logic; do not
   interrupt boot, change boot variables, invoke fastboot, or flash anything.
3. Determine an independently workable restore path and whether a consistent
   private backup of p3/p4 is needed.
4. Separately validate vendor Linux 3.0.35 ABI and application compatibility.

Until then, experimental OS release and boot remain blocked.
