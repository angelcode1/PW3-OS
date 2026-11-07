# R3877.19 — PW3 read-only storage and recovery prerequisite inventory

Research/educational use only. **`NOT_BOOTABLE`**. This does **not** test recovery, verify an image backup, authorize mounting a new filesystem, or establish that any partition can safely be changed.

## Why this is next

The successful R3877.18.3 device-run classified the 167 strong ELF import misses as 163 LuaJIT main-executable candidates and four `clock_gettime@GLIBC_2.4` references provided by GNU IFUNC exports in stock `librt.so.1`. This resolves a *static metadata classification*, not the live linker, KOReader dynamic-module closure or Alpine's musl ABI. The existing KOReader userspace is glibc/soft-float; the separately tested Alpine userspace is musl/hard-float, so combining their libraries in-process remains unsafe.

Before considering any deployment we need a hardware-specific storage map and a recovery approach. R3877.19 reads only **metadata**, not partitions themselves. It identifies the root filesystem entry and the names/sizes of visible block/MTD partitions. It deliberately does not read `/proc/cmdline`, raw storage, partition labels, bootloader registers, serial numbers, book files, user settings or any SSH key.

## Mac steps (existing authorized SSH only)

```bash
mkdir -p ~/Downloads/pw3-r3877-19
unzip -oq ~/Downloads/pw3-r3877-19-recovery-prereq-inventory.zip -d ~/Downloads/pw3-r3877-19
cd ~/Downloads/pw3-r3877-19
shasum -a 256 -c SHA256SUMS_R3877_19.txt
python3 -B -m unittest -q test_r3877_19.py
set -o pipefail
ssh -T -o ConnectTimeout=20 -o ConnectionAttempts=1 -p 2222 \
  root@192.168.8.102 'sh -s' \
  < pw3_r3877_19_readonly_storage.sh \
  | tee pw3_r3877_19_storage_raw.txt
echo "SSH_EXIT_CODE=$?"
python3 -B pw3_r3877_19_analyze.py pw3_r3877_19_storage_raw.txt \
  | tee r3877_19_result.json
echo "R3877_19_ANALYZER_EXIT_CODE=$?"
```

If the first SSH command fails, stop rather than retrying in a loop; do not treat the partial output as storage evidence. The analyzer refuses incomplete input, the wrong kernel/machine or missing partition and root-mount metadata.

`PASS_STORAGE_METADATA_ONLY` is the expected classification when metadata is complete. It means **only** that a filesystem and partition inventory was collected. It does **not** mean recovery is possible. A read-only kernel flag of `0` does not authorize writing the device or partition.

## What remains on HOLD

- Device recovery path, verified restore and untouched original R13 provenance.
- A safe Linux 3.0.35 ABI test of this exact Alpine musl build.
- Dynamic KOReader modules, loader global scope, symbol relocations and IFUNC resolver operation.
- Firmware writes, mounts, image deployment, or boot operations.

The original R13 stage must not be accessed or modified by this script. No new binaries are placed on the PW3. All output is plain text metadata from existing kernel procfs/sysfs interfaces.
