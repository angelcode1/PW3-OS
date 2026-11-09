# PW3 R3877.73 — kernel serial metadata / recovery hardware readiness

**Research/educational use only. `HOLD / NOT_BOOTABLE` remains unchanged.**

R3877.72 user-provided Mac output confirmed structural consistency of the private
normal and diagnostics uImages with U-Boot commands (both CRCs valid). It showed
embedded `bootdelay=0` and `bootdelay=1` markers, **not** the live U-Boot environment,
UART access, a booted diagnostics mode, or an independent restore.

This milestone stops recursive archive/firmware scans. The next practical gate is
serial recovery-access readiness. A live, attended **read-only proc/sys metadata
check** can establish what the running Linux kernel advertises. It cannot prove
bootloader serial interactivity, pin assignment, correct electrical logic level,
or recoverability.

## Safety properties

- The SSH-side POSIX shell script reads `uname`, `/proc/cmdline`, `/proc/consoles`,
  `/sys/class/tty/*` existence and eMMC boot-area `ro`/`force_ro` attributes.
- Only allowlisted/redacted console *classes* and boot flags are emitted. The
  complete command line, MAC address, device serial, SSH key, content and passwords
  are never printed.
- It never opens `/dev/tty*`, raw block devices or a serial adapter. It does not
  mount, remount, boot, reboot, execute a custom binary, set environment variables,
  write sysfs/procfs, or flash anything.
- The host analyzer parses redacted results; malformed and incomplete data fail
  closed. It **always returns exit code 2**, `HOLD / NOT_BOOTABLE`.
- CI runs synthetic host tests only; no network contact to the Kindle.

## Mac steps (zsh, known authorized SSH session)

```zsh
cd ~/Downloads/pw3-r3877-73
shasum -a 256 -c SHA256SUMS_R3877_73.txt
python3 -B -m unittest -q test_r3877_73.py
sh -n pw3_r3877_73_readonly_serial_metadata.sh

setopt pipefail
ssh -T -o ConnectTimeout=15 -o ConnectionAttempts=1 \
  -p 2222 root@192.168.8.102 'sh -s' \
  < pw3_r3877_73_readonly_serial_metadata.sh \
  | tee r3877_73_kernel_metadata.txt
printf 'SSH_EXIT_CODE=%s\n' "$?"

python3 -B pw3_r3877_73_analyze.py r3877_73_kernel_metadata.txt \
  | tee r3877_73_result.json
printf 'R3877_73_EXIT_CODE=%s\n' "$?"
```

If SSH fails, **stop**. Do not reuse truncated output as evidence. In a structurally
valid result, `review.kernel_console_metadata_parsed` is true. A reported
`IMX_UART0_115200` console is only a Linux-side boot-argument marker, not proof
that U-Boot is accessible on the physical serial pads. Read-only flags are
observations, not permissions to disable write protection.

## Optional Mac-only USB serial adapter inventory

With a USB-to-UART device plugged into the Mac, run:

```zsh
python3 - <<'PY'
from glob import glob
patterns = ['/dev/cu.usbserial*', '/dev/cu.usbmodem*',
            '/dev/cu.SLAB_USBtoUART*', '/dev/cu.wchusbserial*']
nodes = set(p for pattern in patterns for p in glob(pattern))
print('USB_SERIAL_DEVICE_NODES=' + str(len(nodes)))
print('1_8_V_LOGIC_COMPATIBILITY_VERIFIED=false')
print('PW3_UART_PAD_PINOUT_VERIFIED=false')
print('SERIAL_CONNECTION_OPENED=false')
PY
```

Do not infer 1.8 V electrical compatibility from a macOS device node. No wiring,
reboot, U-Boot keystrokes, diagnostics boot, or flash is authorized in R3877.73.

The community recovery route for PW3-era Kindles requires a **1.8 V** USB UART
adapter and usually `115200 8N1`: https://kindlemodding.org/jailbreaking/Legacy/backing-up/restoring.html
The PW3 board-level wiring is documented by an independent walkthrough:
https://blog.soumilh.com/electronics/2020/07/12/jailbreaking-my-kindle-paperwhite-3.html
Do not connect a generic 3.3 V/5 V adapter directly to 1.8 V pads.

## Remaining gates

- Hardware-specific, safely wired passive **receive-only** serial capture;
  without adapter TX or VCC connected and only after pinout/voltage verified.
- Actual U-Boot recovery access and independent restore validation.
- Existing live-copied images are snapshots of the user's Kindle, not proven
  factory-original stock. p3 and p4 are not backed up; live writes can make
  their raw snapshots inconsistent.
- Vendor Linux 3.0.35 compatibility of the experimental userspace and real
  application runtime closure is separately unverified.

Do not publish raw firmware images, complete serial logs, passwords, or private
block-device hashes in public GitHub issues or repositories.
