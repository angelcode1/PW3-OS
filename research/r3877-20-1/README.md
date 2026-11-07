# R3877.20.1 — distinguish pseudo-rootfs from the live block-backed root
**Research and educational only. Immutable hold: `NOT_BOOTABLE`. No device writes or boot trials.**

## Source evidence
The user-reported authorized read-only R3877.20 inventory from a PW3 running Linux `3.0.35-lab126` shows two `/proc/mounts` root records (`rootfs|rootfs|rw` and `/dev/root|ext3|ro`), but **one** live `/proc/self/mountinfo` entry for `/` (`179:1|ext3|/dev/root|/|ro`). The sysfs mapping `mmcblk0p1|179:1` confirms that this filesystem device identity belongs to `mmcblk0p1`. The independent `/var/local` ext3 mount maps to `179:3` / `mmcblk0p3`.

The previous R3877.20 analyzer incorrectly required **exactly one** root record in `/proc/mounts`. The extra early virtual `rootfs` entry caused a false ambiguity. It is not a second conflicting block-backed root.

## Fix
The corrected `pw3_r3877_20_analyze.py` ignores at most one `rootfs|rootfs` pseudo record for the block-root crosscheck. It still requires exactly one live mountinfo root with an ext2/3/4 filesystem, one nonpseudo proc-root record with the same filesystem and ro/rw access, and the identical major:minor from sysfs. Duplicate, inconsistent, missing, nonstandard or redacted records **do not** prove a physical root. The kernel's `root=` hint is recorded but never used as a positive root proof.

Reanalysis of the sanitized user-provided fixture returns `PASS_MOUNT_MAPPING_METADATA_ONLY`, `root_backing_partition_verified=true`, `root_partition_supported_by_direct_live_mount_metadata=mmcblk0p1`, `root_metadata_ambiguous=false`. This is **metadata-only**, not proof of partition bytes, rootfs backup, bootloader, recovery or Alpine execution.

## Reproduce without Kindle access

```bash
cd research/r3877-20-1
python3 -B -m unittest -q test_r3877_20.py test_r3877_20_1.py
python3 -B pw3_r3877_20_analyze.py R3877_20_USER_OBSERVED_MOUNT_METADATA.txt
```

The 47 offline tests include the original 28 and 19 new dual-root and fail-closed regressions. `pw3_r3877_20_readonly_mount_mapping.sh` is retained for reproducibility but does not need to run again. CI is offline only and never accesses a Kindle.

All firmware, bootloader, backup, recovery, Linux 3.0.35 syscall/musl and KOReader runtime gates remain **unverified**. Do not infer a recovery partition identity from partition numbers and do not read raw flash or change mounts.

Specification: https://www.kernel.org/doc/html/latest/filesystems/proc.html
