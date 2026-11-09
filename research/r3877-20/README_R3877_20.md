# PW3 R3877.20 — read-only root mount mapping

**Research and educational purposes only. `NOT_BOOTABLE` is immutable.** This package does **not** access block-device contents, raw eMMC boot areas, the bootloader, books, settings, or original R13 stage. No writes, remounts, firmware changes, new device binaries, or boot attempts.

## Prior evidence and motivation

The user-reported R3877.19.1 static inventory returned `PASS_STORAGE_METADATA_ONLY` against the Kindle's Linux `3.0.35-lab126` kernel and `armv7l` machine. It recognized `/proc/partitions` entries for `mmcblk0`, `mmcblk0p1..p4`, and two distinct eMMC boot-area devices `mmcblk0boot0`, `mmcblk0boot1`. The root was shown as `rootfs` and was **not** mapped to a physical root partition. The collected inventory was metadata only, not a backup or recovery proof.

The Linux `/proc/self/mountinfo` format includes major:minor, mount root, mountpoint, mount options, filesystem, and mount source. See https://docs.kernel.org/filesystems/proc.html and https://www.kernel.org/doc/html/v5.9/filesystems/proc.html. Linux `rootfs` can be an early virtual root mount; it does not, by itself, identify the underlying block device. See https://www.kernel.org/doc/html/v6.4/filesystems/ramfs-rootfs-initramfs.html.

## Safety and privacy

The target shell script only reads `/proc/cmdline` (extracting and redacting `root=`; never prints the complete line), `/proc/mounts` (root entries only), `/proc/self/mountinfo` (root and selected standard system mounts only), `/sys/class/block/mmcblk0p1..p4/dev`, and runs the existing `uname` command. No `dd`, `mount`, `cat` of block files, `su`, writable redirection, or firmware commands appear in the script. Output filters out arbitrary mount names and all non-`root=` kernel parameters. The script contains no network usage; it is sent over **existing authorized SSH**. The Mac writes the resulting sanitized text and JSON locally.

No serial numbers, full boot command lines, filesystem UUIDs, or user files should be collected. For unrecognized `root=` values, the script emits `OTHER_REDACTED`, `UUID_PRESENT`, or `PARTUUID_PRESENT`, as appropriate.

## Run on Mac (known SSH port 2222)

```bash
mkdir -p ~/Downloads/pw3-r3877-20
unzip -oq ~/Downloads/pw3-r3877-20-root-mount-map.zip -d ~/Downloads/pw3-r3877-20
cd ~/Downloads/pw3-r3877-20
shasum -a 256 -c SHA256SUMS_R3877_20.txt
python3 -B -m unittest -q test_r3877_20.py
set -o pipefail
ssh -T -p 2222 -o ConnectTimeout=20 -o ConnectionAttempts=1 \
  root@192.168.8.102 'sh -s' < pw3_r3877_20_readonly_mount_mapping.sh \
  | tee r3877_20_mount_raw.txt
echo "R3877_20_SSH_EXIT_CODE=$?"
python3 -B pw3_r3877_20_analyze.py r3877_20_mount_raw.txt \
  | tee r3877_20_result.json
echo "R3877_20_ANALYZER_EXIT_CODE=$?"
```

Expected successful **metadata-only** classification is `PASS_MOUNT_MAPPING_METADATA_ONLY`, with the immutable `NOT_BOOTABLE` hold; the result may legitimately have `root_backing_partition_verified=false`. If SSH returns nonzero, do not treat an interrupted inventory as an auditable result. Run the analyzer only on a complete capture. Do not attempt repeated SSH sessions if the transport is unstable.

## Interpretation and intentional limits

- `boot_root_hint` is informational and **never** proves which partition currently backs `/`.
- `mountinfo` major:minor identifies the mount's kernel filesystem device ID (`st_dev`); the root may be a pseudo-root (`0:x`) and offer no physical partition identity.
- A physical root partition is marked supported only for a **single** root mount where mountinfo, `/proc/mounts`, and `/sys/class/block/mmcblk0pN/dev` consistently identify `/dev/mmcblk0pN` and a non-pseudo filesystem. If ambiguous, leave `root_backing_partition_verified=false`.
- Even a successfully identified root partition would **not** verify bootloader location, recovery, a correct backup, safe deployment, bootability, IFUNC resolver behaviour, KOReader runtime loading, or musl syscall compatibility on Linux 3.0.35.
- The next work should be a non-destructive recovery feasibility and backup attestation review, plus separate Alpine/musl syscall research; **do not start boot/write trials**.

## Tests

28 offline regression tests cover pseudo-root versus physical-root inference, differing mount sources, duplicate/unknown metadata, unredacted boot parameters, unexpected mountpoint disclosure, malformed sysfs IDs, and missing or interrupted sentinels. A simple local-host script smoke run confirms output format, but **the physical Kindle test has not been performed by the assistant**.
