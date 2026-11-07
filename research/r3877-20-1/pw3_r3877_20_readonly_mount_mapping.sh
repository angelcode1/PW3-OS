#!/bin/sh
# R3877.20: read only kernel proc/sys mount metadata. No device reads/writes.
# The complete kernel boot command line and arbitrary mount paths are NEVER printed.
set -fu
printf '%s\n' 'R3877_20_MOUNT_MAPPING_BEGIN'
printf 'kernel_release=%s\n' "$(uname -r 2>/dev/null || printf UNKNOWN)"
printf 'machine=%s\n' "$(uname -m 2>/dev/null || printf UNKNOWN)"

if [ -r /proc/cmdline ]; then
  IFS= read -r cmdline < /proc/cmdline || :
  n=0
  hint=NOT_PRESENT
  # shell word-splitting: no command evaluation; wildcard expansion is disabled.
  for t in $cmdline; do
    case "$t" in
      root=*)
        n=$((n+1))
        case "${t#root=}" in
          /dev/mmcblk0p[1-4]|/dev/root|rootfs) hint=${t#root=} ;;
          PARTUUID=*) hint=PARTUUID_PRESENT ;;
          UUID=*) hint=UUID_PRESENT ;;
          *) hint=OTHER_REDACTED ;;
        esac ;;
    esac
  done
  if [ "$n" -gt 1 ]; then hint=MULTIPLE_REDACTED; fi
  printf 'boot_root_hint=%s\n' "$hint"
  printf 'boot_root_hint_count=%s\n' "$n"
else
  printf '%s\n' 'boot_root_hint=NOT_EXPOSED' 'boot_root_hint_count=0'
fi

if [ -r /proc/mounts ]; then
  n=0
  while read -r dev mnt fs options more; do
    [ "$mnt" = / ] || continue
    n=$((n+1))
    case "$dev" in
      /dev/mmcblk0p[1-4]|/dev/root|rootfs|none|tmpfs|overlay) : ;;
      *) dev=OTHER_REDACTED ;;
    esac
    case "$fs" in
      rootfs|ext2|ext3|ext4|squashfs|vfat|tmpfs|overlay|jffs2|ubifs|ramfs) : ;;
      *) fs=OTHER_REDACTED ;;
    esac
    case ",$options," in *,ro,*) ro=ro ;; *) ro=rw ;; esac
    printf 'proc_mount_root=%s|%s|%s\n' "$dev" "$fs" "$ro"
  done < /proc/mounts
  printf 'proc_mount_root_count=%s\n' "$n"
else
  printf '%s\n' 'proc_mount_root_count=NOT_EXPOSED'
fi

if [ -r /proc/self/mountinfo ]; then
  total_root=0
  selected_count=0
  while IFS= read -r line; do
    # Parse a kernel-owned record into positional shell tokens, never execute it.
    set -- $line
    [ "$#" -ge 10 ] || continue
    # Field 5 is the mountpoint, field 3 is major:minor.
    case "$5" in
      /|/mnt/us|/var/local|/mnt/root|/mnt/mmc|/mnt/secondary|/mnt/base-us) ;;
      *) continue ;;
    esac
    mountpoint=$5
    mm=$3
    inroot=$4
    options=$6
    # Locate the documented '-' separator; optional fields may precede it.
    shift 6
    sep_found=0
    while [ "$#" -gt 0 ]; do
      if [ "$1" = '-' ]; then sep_found=1; shift; break; fi
      shift
    done
    [ "$sep_found" -eq 1 ] && [ "$#" -ge 2 ] || continue
    fstype=$1
    source=$2
    case "$mm" in
      *[!0-9:]*|'') mm=OTHER_REDACTED ;;
    esac
    case "$inroot" in /) : ;; *) inroot=OTHER_REDACTED ;; esac
    case "$fstype" in rootfs|ext2|ext3|ext4|squashfs|vfat|tmpfs|overlay|jffs2|ubifs|ramfs) : ;; *) fstype=OTHER_REDACTED ;; esac
    case "$source" in
      /dev/mmcblk0p[1-4]|/dev/root|rootfs|none|tmpfs|overlay|/dev/mmcblk0) : ;;
      *) source=OTHER_REDACTED ;;
    esac
    case ",$options," in *,ro,*) ro=ro ;; *) ro=rw ;; esac
    if [ "$mountpoint" = / ]; then
      total_root=$((total_root+1))
      printf 'mountinfo_root=%s|%s|%s|%s|%s\n' "$mm" "$fstype" "$source" "$inroot" "$ro"
    elif [ "$source" != OTHER_REDACTED ]; then
      selected_count=$((selected_count+1))
      printf 'selected_mount=%s|%s|%s|%s\n' "$mountpoint" "$mm" "$fstype" "$source"
    fi
  done < /proc/self/mountinfo
  printf 'mountinfo_root_count=%s\n' "$total_root"
  printf 'selected_mount_count=%s\n' "$selected_count"
else
  printf '%s\n' 'mountinfo_root_count=NOT_EXPOSED' 'selected_mount_count=NOT_EXPOSED'
fi

for name in mmcblk0p1 mmcblk0p2 mmcblk0p3 mmcblk0p4; do
  path="/sys/class/block/$name/dev"
  if [ -r "$path" ]; then
    IFS= read -r mm < "$path" || :
    case "$mm" in
      *[!0-9:]*|'') : ;;
      *) printf 'sysfs_map=%s|%s\n' "$name" "$mm" ;;
    esac
  fi
done
printf '%s\n' 'R3877_20_MOUNT_MAPPING_COMPLETE'
