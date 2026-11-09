# R3877.75 — physical recovery access decision gate

**Research only — `HOLD / NOT_BOOTABLE`. No Kindle writes, boot changes, or serial experiments authorized.**

## Observed state

R3877.74's user-run Mac-only probe returned zero recognized candidate USB
serial port names, exit 2, and no UART I/O. This is an absence of **recognized
/dev naming candidates** at the time of the scan; it is not proof that the Mac
has no USB serial hardware and says nothing about whether the Kindle exposes a
UART. The running PW3 Linux kernel previously identified
`ttymxc0`, 115200 baud, as the active console. Active U-Boot access is
unverified. The captured eMMC boot areas reported `ro=0` and
`force_ro=0`, so care is essential to avoid accidental writes.

## Hardware prerequisites — no further software scan substitutes for these

1. Locate a USB-to-UART adapter that **explicitly supports 1.8 V logic-level
   inputs and outputs** (or an appropriately designed, separately powered
   bidirectional level shifter with a UART bridge). An adapter marketed only
   as 3.3 V / 5 V, or an RS-232 cable, is unsuitable for direct connection.
   Confirm the actual I/O level in the device manual and, ideally, measurement.
2. Identify the **exact adapter model** and serial-device interface on the Mac.
   A /dev entry may only mean the OS enumerates a bridge; it does not
   establish logic voltage, wiring, or Kindle compatibility.
3. Establish a reliable PW3-specific board connection diagram. A
   model-appropriate, verified pinout and a qualified electrical assessment
   are required before any Kindle wiring. No assumptions from other models.
4. For a separately approved, attended first capture, prefer **receive only**:
   Kindle TX -> adapter RX, common GND, with adapter TX and VCC
   disconnected. Never apply USB 5 V, 3.3 V TTL or RS-232 voltages to the
   Kindle serial input. Confirm that the adapter's receive input safely
   recognizes 1.8 V high levels.
5. Do not reboot solely for this preflight, interrupt U-Boot, force diags,
   install alternative bootloaders, change `force_ro`, or flash any partition.

## Source-backed connection choices

- Conventional motherboard-pad UART: a PW3-specific teardown documents
  exposed board pads, 1.8 V serial and the need for suitable level
  conversion.
  https://blog.soumilh.com/electronics/2020/07/12/jailbreaking-my-kindle-paperwhite-3.html
- Unusual micro-USB serial mode: barebox documents that Kindle generation
  6/7 can switch data lines to UART when a 30 kOhm sense-pin-to-ground
  arrangement is present. This is a custom cable/electrical project, **not**
  standard USB console access and not a bypass of voltage verification.
  https://github.com/barebox/barebox/blob/master/Documentation/boards/imx/amazon-kindle-6-7.rst
- Recovery prerequisites: https://kindlemodding.org/jailbreaking/Legacy/backing-up/restoring.html

## Next user action

If a possible USB serial adapter is physically available, connect it to
the **Mac only** (not to Kindle), identify its exact printed model and
I/O-voltage documentation, then repeat the existing R3877.74 inventory
and share the result. If no adapter exists, acquire **verified 1.8 V
logic-compatible UART hardware** before attempting recovery access.
Do not begin wiring or opening the Kindle on the basis of port-name
enumeration alone.

## Remaining blockers

Physical serial capture, active U-Boot access, a proven independent restore
procedure, and vendor Linux 3.0.35 ABI/runtime compatibility are unverified.
The backups are device-state evidence, not authenticated stock factory images
or proof of successful restoration.
