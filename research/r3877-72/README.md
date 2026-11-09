# PW3 R3877.72 — offline boot-chain and UART recovery-access preflight

**Research/education only. `NOT_BOOTABLE` remains a strict hold.**

This milestone follows user-reported device-derived copies and structural evidence
in R3877.71. It does not boot or flash a Kindle, open a serial port, mount images,
write a device, or claim recovery has been demonstrated. Raw eMMC images, UUIDs,
private SHA-256 checksums, and device identifiers remain outside the public repo.

## Findings confirmed using uploaded private images

- eMMC boot0 contains embedded `U-Boot 2009.08-lab126` version markers.
- It contains `bootcmd=bootm 0x41000` and `bootcmd_diags=bootm 0xE41000`.
- It contains `baudrate=115200` and `bootdelay=0` and `bootdelay=1` strings.
- Both matching ARM Linux 3.0.35 U-Boot-format kernels in the first 32 MiB
  have valid header and payload CRCs.
- The runtime U-Boot configuration and its ability to accept serial input are
  **not verified**. Multiple embedded boot-delay values do not prove whether
  boot interruption is possible.
- The diagnostics filesystem was identified by earlier private-image inspection,
  but no actual diagnostics boot or restore was performed.

## macOS local-only check

Run against only the existing private backup images:

```zsh
cd ~/Downloads/pw3-r3877-72
python3 -B -m unittest -q test_r3877_72.py
python3 -B pw3_r3877_72_boot_chain_preflight.py \
  --image-dir "$HOME/Downloads/pw3-device-backup" \
  --acknowledge-readonly-offline-boot-chain \
  > r3877_72_result.json
printf 'R3877_72_EXIT_CODE=%s\n' "$?"
cat r3877_72_result.json
```

Without the opt-in flag the script never reads any image.
A good structural review still returns `HOLD` with exit code `2`.
The tool requires `mmcblk0boot0.img` and `mmcblk0-first32MiB.img` at their
expected sizes and never emits raw boot strings, serial numbers or digests.
It checks structural consistency, not a live U-Boot environment or recoverability.

## Safest next physical recovery test: passive receive-only UART

The PW3-era community recovery guide describes a **1.8 V UART** connection,
usually **115200 baud**, as a possible U-Boot and diagnostics route:
https://kindlemodding.org/jailbreaking/Legacy/backing-up/restoring.html

This is **not authorization to make hardware connections or reboot**.
A known PW3-compatible pinout, electronics skill and a verified 1.8 V
logic-level interface are prerequisites, not 3.3 V or 5 V-only logic.

For any subsequently attended, explicitly approved passive check:
- Kindle TX -> adapter RX, plus shared ground.
- Leave **adapter TX unconnected** and **VCC/3.3 V/5 V disconnected**.
- Use 115200 baud, 8 data bits, no parity, 1 stop bit (8N1), receive only.
- Observe ordinary boot output; do not interrupt boot, send keystrokes,
  alter variables, invoke diagnostics/fastboot or flash anything.

Even passive wiring has physical/electrical risks. If the voltage or
pads are unverified, stop rather than guess. A readable serial log,
interactive console access, actual diagnostics boot and independent
restore remain unverified.

## Other holds

p1, p2, eMMC boot0/boot1 and the 32 MiB pre-partition region were
user-verified by SHA-256 device-to-Mac comparison. They represent
the unit's current contents, **not independently authenticated factory
stock**. p3/p4 have not been backed up, and live raw reads of writable
partitions cannot be presumed consistent.

Experimental OS release and boot remain blocked until independent
restore access, vendor-kernel ABI compatibility and boot safety gates
have all been verified.
