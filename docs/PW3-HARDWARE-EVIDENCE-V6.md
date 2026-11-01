# PW3 hardware interface evidence — read-only v6 checkpoint

**Date:** 2026-11-01, Australia/Brisbane. **Evidence:** user-supplied local SSH capture `pw3-readonly-evidence-v6.zip` (not published).

## Verification

- Collector revision `PW3-V6-HOSTCAP-20261101`; all 17 diagnostics captured, no reported collector errors.
- Archive passed ZIP integrity and all 17 per-entry SHA-256 manifest validations.
- Collector's eight local tests also passed. This is **read-only enumeration**, not a framebuffer, input, power or boot test.
- Two entries (`/proc/mtd` output and `/etc/init.d` listing) are empty; because commands suppress errors, do **not** infer missing hardware or configuration from empty output.

## Hardware interfaces observed

| Subsystem | Observed interface | Remaining unknown |
| --- | --- | --- |
| Kernel | Linux `3.0.35-lab126`, ARMv7 | Kernel config and standalone rootfs boot |
| E-ink | `/dev/fb0`, `mxc_epdc_fb` module, `/sys/class/graphics/fb0` | Pixel format, EPDC ioctl and waveform behavior |
| Touch | Cypress `cyttsp4_mt`, `/dev/input/event1` | ABS axis ranges, touch coordinate mapping |
| Power key | `max77696-onkey`, `/dev/input/event0` | Event semantics |
| Frontlight | `/sys/class/backlight/max77696-bl` | Readable properties and safe control semantics |
| Battery and charger | `max77696-battery`, `max77696-charger`, `max77696-eh`, `max77696-uic` | Property values, suspend/power policy |
| Init | `/etc/init` symlink to `/etc/upstart`, `/sbin/init` | Job ordering/dependencies and minimal replacement |
| Storage | Root `/dev/root` ext3 mounted read-only; `/var/local` on `/dev/mmcblk0p3` ext3; `/mnt/us` served by FUSE (`fsp`), with loop-backed vfat at `/mnt/base-us` | Raw user-storage partition mapping, safe independent mount design |
| Libraries | `libc.so.6`, `libpthread-2.20.so`, `liblipc.so`, `libeinkViewer.so`, `libpdc.so`, `libpowerutil.so` listed | ABI compatibility and actual required subset |

Upstart filenames include `display.conf`, `touch.conf`, `powerd.conf`, `lipcd.conf`, `framework.conf`, `chroot.conf`, `filesystems.conf`, and `sshd.conf`. File **names alone** do not establish dependencies or authorize deleting any component.

## Implications and next gates

1. Target the observed stock kernel interfaces with **host-side synthetic adapters** first; do not send ioctls or read live event streams in this milestone.
2. R22 remains a **separate offline ARM/QEMU application gate**: genuine KOReader PluginLoader → FileManager → Ink Away canvas open, stroke, save, close, return. Device inventory does not count as R22 PASS.
3. For a later individually reviewed read-only collection, narrow requests to framebuffer metadata, touch axis capabilities, battery/frontlight property names and selected Upstart text files. Exclude secrets, identifiers and user files.
4. Do not assume `/mnt/us` is directly `/dev/mmcblk0p4` based on this snapshot; it is mounted through FUSE.

**Safety holds:** `NO_FIRMWARE_WRITES_HOLD; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. The raw archive and any proprietary firmware remain local.
