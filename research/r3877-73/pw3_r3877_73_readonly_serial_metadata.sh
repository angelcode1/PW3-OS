#!/bin/sh
# PW3 R3877.73 -- Kindle-side proc/sys metadata only. No writes or serial I/O.
set -fu
printf '%s\n' 'R3877_73_BEGIN'
printf 'kernel=%s\n' "$(uname -r 2>/dev/null || printf UNAVAILABLE)"
printf 'machine=%s\n' "$(uname -m 2>/dev/null || printf UNAVAILABLE)"
if [ -r /proc/cmdline ]; then
  IFS= read -r cmdline < /proc/cmdline || :
  console_count=0
  console_class=NONE
  for token in $cmdline; do
    case "$token" in
      console=*)
        console_count=$((console_count+1))
        case "${token#console=}" in
          ttymxc0,115200|ttymxc0,115200n8) console_class=IMX_UART0_115200 ;;
          ttymxc1,115200|ttymxc1,115200n8) console_class=IMX_UART1_115200 ;;
          tty0|tty1) console_class=LOCAL_TTY ;;
          *) console_class=OTHER_REDACTED ;;
        esac
        ;;
    esac
  done
  if [ "$console_count" -gt 1 ]; then console_class=MULTIPLE_REDACTED; fi
  printf 'cmdline_console_count=%s\n' "$console_count"
  printf 'cmdline_console_class=%s\n' "$console_class"
else
  printf '%s\n' 'cmdline_console_count=UNAVAILABLE' 'cmdline_console_class=UNAVAILABLE'
fi
if [ -r /proc/consoles ]; then
  imx0=0; imx1=0; other=0
  while read -r name rest; do
    case "$name" in
      ttymxc0) imx0=1 ;;
      ttymxc1) imx1=1 ;;
      *) other=$((other+1)) ;;
    esac
  done < /proc/consoles
  printf 'active_console_imx0=%s\n' "$imx0"
  printf 'active_console_imx1=%s\n' "$imx1"
  printf 'active_console_other_count=%s\n' "$other"
else
  printf '%s\n' 'active_console_imx0=UNAVAILABLE' 'active_console_imx1=UNAVAILABLE' 'active_console_other_count=UNAVAILABLE'
fi
for name in ttymxc0 ttymxc1; do
  if [ -e "/sys/class/tty/$name" ]; then value=1; else value=0; fi
  printf 'sysfs_tty_%s_present=%s\n' "$name" "$value"
done
for name in mmcblk0boot0 mmcblk0boot1; do
  if [ -r "/sys/block/$name/force_ro" ]; then
    IFS= read -r value < "/sys/block/$name/force_ro" || :
    case "$value" in 0|1) : ;; *) value=INVALID ;; esac
  else
    value=UNAVAILABLE
  fi
  printf 'boot_%s_force_ro=%s\n' "$name" "$value"
  if [ -r "/sys/block/$name/ro" ]; then
    IFS= read -r value < "/sys/block/$name/ro" || :
    case "$value" in 0|1) : ;; *) value=INVALID ;; esac
  else
    value=UNAVAILABLE
  fi
  printf 'boot_%s_ro=%s\n' "$name" "$value"
done
printf '%s\n' 'R3877_73_END'
