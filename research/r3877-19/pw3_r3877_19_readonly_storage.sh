#!/bin/sh
# Research-only: rootfs/partition metadata; no storage device I/O or writes.
# Runs via an existing authorized SSH session, e.g. ssh root@PW3 'sh -s'.
set -u
printf '%s\n' 'R3877_19_READ_ONLY_STORAGE_BEGIN'
printf 'kernel_release=%s\n' "$(uname -r 2>/dev/null || printf UNKNOWN)"
printf 'machine=%s\n' "$(uname -m 2>/dev/null || printf UNKNOWN)"
if [ -r /proc/mounts ]; then
  found=0
  while read -r dev mount_point fstype opts rest; do
    if [ "$mount_point" = / ]; then
      case "$dev" in
        /*|rootfs) : ;;
        *) dev=OTHER ;;
      esac
      printf 'root_device=%s\n' "$dev"
      printf 'root_fstype=%s\n' "$fstype"
      case ",$opts," in *,ro,*) printf '%s\n' 'root_mount_read_only=true' ;; *) printf '%s\n' 'root_mount_read_only=false' ;; esac
      found=1
      break
    fi
  done < /proc/mounts
  [ "$found" -eq 1 ] || printf '%s\n' 'root_mount_status=NOT_FOUND'
else
  printf '%s\n' 'root_mount_status=NOT_EXPOSED'
fi
if [ -r /proc/partitions ]; then
  printf '%s\n' 'partitions_status=AVAILABLE'
  while read -r major minor blocks dev extras; do
    case "$dev" in
      mmcblk[0-9]*|mmcblk[0-9]*p[0-9]*|mtdblock[0-9]*|sd[a-z]|sd[a-z][0-9]*)
        case "$major:$minor:$blocks" in *[!0-9:]*|'') continue ;; esac
        printf 'partition=%s,%s,%s,%s\n' "$dev" "$major" "$minor" "$blocks" ;;
    esac
  done < /proc/partitions
else
  printf '%s\n' 'partitions_status=NOT_EXPOSED'
fi
if [ -r /proc/mtd ]; then
  printf '%s\n' 'mtd_status=AVAILABLE'
  # No raw flash reads: only lines from the kernel's /proc/mtd text listing.
  while read -r dev size erase name extra; do
    case "$dev" in
      mtd[0-9]*:)
        case "$size:$erase" in *[!a-fA-F0-9:]*|'') continue ;; esac
        # Never print partition names (which may contain custom labels).
        printf 'mtd=%s,%s,%s\n' "${dev%:}" "$size" "$erase" ;;
    esac
  done < /proc/mtd
else
  printf '%s\n' 'mtd_status=NOT_EXPOSED'
fi
for dev in mmcblk0 mmcblk1; do
  p="/sys/block/$dev/ro"
  if [ -r "$p" ]; then
    IFS= read -r v < "$p" || :
    case "$v" in 0|1) printf 'block_readonly=%s,%s\n' "$dev" "$v" ;; esac
  fi
done
printf '%s\n' 'R3877_19_READ_ONLY_STORAGE_COMPLETE'
