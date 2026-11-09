#!/bin/sh
# R3877.76: known-value read-only Linux userspace capability inventory.
# No mounting, installation, device I/O, network setup, or boot hooks.
set -fu
printf '%s\n' R3877_76_BEGIN
printf 'kernel=%s\n' "$(uname -r 2>/dev/null || printf unavailable)"
printf 'machine=%s\n' "$(uname -m 2>/dev/null || printf unavailable)"
features=UNAVAILABLE
if [ -r /proc/cpuinfo ]; then
  while IFS= read -r line; do
    case "$line" in
      Features*:*) features=${line#*:}; break ;;
    esac
  done < /proc/cpuinfo
fi
for feature in vfp vfpv3 vfpv3d16 neon tls thumb edsp; do
  observed=0
  for word in $features; do
    if [ "$word" = "$feature" ]; then observed=1; break; fi
  done
  printf 'cpu_feature_%s=%s\n' "$feature" "$observed"
done
for tool in chroot mount losetup initctl busybox; do
  present=0
  for dir in /bin /sbin /usr/bin /usr/sbin; do
    if [ -x "$dir/$tool" ]; then present=1; break; fi
  done
  printf 'known_path_%s=%s\n' "$tool" "$present"
done
if [ -r /proc/mounts ]; then
  root_seen=0; userstore_seen=0
  while read -r device mountpoint fstype opts more; do
    case "$mountpoint" in
      /) key=root; root_seen=1 ;;
      /mnt/us) key=userstore; userstore_seen=1 ;;
      *) continue ;;
    esac
    case "$fstype" in
      ext2|ext3|ext4|fuse.fsp|fuse|tmpfs|vfat|overlay|squashfs) : ;;
      *) fstype=OTHER_REDACTED ;;
    esac
    case ",$opts," in *,ro,*) access=ro ;; *) access=rw ;; esac
    case ",$opts," in *,noexec,*) noexec=1 ;; *) noexec=0 ;; esac
    case ",$opts," in *,nosuid,*) nosuid=1 ;; *) nosuid=0 ;; esac
    case ",$opts," in *,nodev,*) nodev=1 ;; *) nodev=0 ;; esac
    printf 'mount_%s=%s,%s,noexec_%s,nosuid_%s,nodev_%s\n' "$key" "$fstype" "$access" "$noexec" "$nosuid" "$nodev"
  done < /proc/mounts
  printf 'root_mount_seen=%s\n' "$root_seen"
  printf 'userstore_mount_seen=%s\n' "$userstore_seen"
else
  printf '%s\n' 'root_mount_seen=0' 'userstore_mount_seen=0'
fi
printf '%s\n' R3877_76_END
