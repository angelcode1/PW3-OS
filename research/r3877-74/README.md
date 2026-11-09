# R3877.74 — Mac USB-UART adapter-name inventory

**Research only. HOLD / NOT_BOOTABLE remains mandatory.**

R3877.73 live read-only metadata confirmed Linux console ttymxc0 at 115200 baud.
Both eMMC hardware boot areas returned ro=0 and force_ro=0. Never disable
protective flags, write those boot areas, or change the device boot mode.

The script enumerates local Mac /dev entry names and prints **counts only** for
common USB serial naming patterns. It never opens a serial port, sends data,
contacts the Kindle or exposes raw device paths/serial numbers. Detection is
not evidence of electrical 1.8 V suitability or working U-Boot access.

## Mac instructions

Download this folder's source files and run:

```zsh
cd ~/Downloads/pw3-r3877-74
python3 -B -m unittest -q test_r3877_74.py
setopt pipefail
python3 -B pw3_r3877_74_macos_uart_inventory.py \
  --acknowledge-local-device-name-inventory \
  | tee r3877_74_result.json
printf 'R3877_74_EXIT_CODE=%s\n' "$?"
```

Expected exit code 2, result HOLD, immutable_hold NOT_BOOTABLE.
Perform initially with the existing Mac hardware only. If a USB-UART adapter
is plugged into the Mac for comparison, leave it entirely disconnected
from the Kindle. Port-name absence does not prove no adapter is attached,
and port-name presence cannot validate the logic voltage.

## Physical recovery still untested

An appropriate route may be known PW3 motherboard UART pads and a verified
1.8 V adapter. The barebox project also documents a nonstandard micro-USB
UART arrangement using a 30 kΩ sense-pin resistor for Kindle generations 6/7.
Neither approach is authorized for immediate connection by this milestone;
verify the actual hardware and safe electrical plan separately.

Sources: https://www.barebox.org/doc/2026.03.1/boards/imx/amazon-kindle-6-7.html
https://kindlemodding.org/jailbreaking/Legacy/backing-up/restoring.html

Remaining blockers: independent recovery-console access, restore validation,
and experimental userspace compatibility with vendor kernel 3.0.35.
No private backups, private SHA-256 digests or raw serial captures in GitHub.
