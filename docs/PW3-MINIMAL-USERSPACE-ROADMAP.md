# PW3-OS — minimal independent Alpine userspace and evidence-led file inventory

**Design objective (future, not achieved):** run an independent, lean Alpine ARMv7 userspace with KOReader v2026.07.2 and Ink Away v4.4.0, using the existing PW3 Linux `3.0.35-lab126` kernel and required hardware drivers, while removing Amazon's **application/userspace** stack from the final OS image. The independent OS is **NOT BOOTABLE** and no migration, firmware write, stock boot change, partition alteration, or physical driver actuation is authorized.

The phrase 'remove all Amazon firmware except drivers' must be interpreted carefully. The retained kernel is itself a Lab126-customized kernel. Some essential board-specific boot components, DTB/ATAG-equivalent parameters, modules, firmware blobs, display waveforms, calibration data, or boot/recovery assets may also be indispensable; this cannot be settled by file-access tracing alone. Preserve a separately tested recovery path and stock backups even after a custom userspace becomes stable. Do not redistribute non-licensed blobs.

## Target stack

1. **Application:** official KOReader (kindlepw2 ARM native binaries and assets) with Ink Away plugin and a narrowly selected plugin set.
2. **Compatibility runtime:** isolated glibc 2.20 / GNU ARM runtime and precisely matching ELF interpreter, ABI, shared libraries and plugin assets; do not assume Alpine musl alone will run KOReader. Validate ARM EABI/float ABI for every ELF.
3. **Alpine userspace:** pinned Alpine ARMv7 musl minirootfs, BusyBox, a reviewed minimal init/service supervisor (OpenRC optional), storage mounting, clock/time, battery/charging/backlight services and recovery/diagnostic facilities.
4. **PW3 device adapter:** tested EPDC display update/ioctl/waveform handling, Cypress evdev coordinate conversion, power button, MAX77696 battery/charger/frontlight, power management, suspend/resume and any Wi-Fi input/firmware. The existing read-only v6 hardware inventory proves interface *names*, not operation.
5. **Stock kernel and board essentials:** Linux 3.0.35-lab126, matching module tree, firmware data and boot parameters only when proven needed. Do not assume a current Alpine armv7 release is fully compatible with this old kernel; verify system calls and dynamic ABI.

## How to locate dependencies without making dangerous deletions

Maintain a content-addressed file catalog for the **host-staged** rootfs: path, mode, owner, symlink target, SHA-256, package/source and license/provenance. Track both positive and negative evidence.

- **Static linkage:** `readelf -h -l -d`, `objdump -p`, ELF PT_INTERP, `NEEDED`, dynamic RPATH/RUNPATH, and KOReader Lua `require`/`ffi.load`/`dofile` contracts; include relative resources, fonts, locale and plugin data. Inspect `dlopen`/LuaJIT FFI paths and transitive dependencies.
- **Dynamic runtime:** only in isolated offline ARM/QEMU test stages, trace `execve`, `open/openat`, `stat`, symlink resolution, memory mapping and subprocess/network attempts with `strace -f` or equivalent. Correlate trace to precise scenario/build/runtime. A successful `open` is a use; an unsuccessful `ENOENT` may still reveal required fallback paths; a file not seen is *not* proof it is unnecessary.
- **Kernel and devices:** separately inventory built-ins vs modules, `modinfo`/modules dependencies, firmware-loader requirements, e-ink waveform and panel metadata, DTB/board params, and suspend/recovery requirements. Driver-requested blobs are not necessarily observed by application-level syscall traces.
- **Scenario matrix:** cold application start, file browser, font/fallback, EPUB/PDF, Ink Away draw/save/reopen/export, USB storage/mount transitions, Wi-Fi disabled and enabled (when authorized in a future environment), charging/battery low, frontlight brightness, power key, suspend/wake and error/recovery paths. Never perform these on a physical Kindle without a separately reviewed safety step.
- **Allowlist reconstruction:** generate new rootfs **from scratch** by copying only reviewed required files from licensed/pinned inputs and their dependency closure. Keep the original staged rootfs and test artifacts immutable; never run `rm -rf` against the stock firmware or prune unclassified files in place. Include fail-closed negative controls and symlink escape checks. Record each exclusion with reason and scenario coverage; revisit when a feature needs it.

## Evidence gates before even considering independent boot

1. **Application success:** R22.1 genuine PluginLoader/Ink Away ARM PASS (user-supplied) and R23.4 real `reader.lua` Bidi/UIManager import PASS (user-supplied). Remaining: genuine top-level FileManager event loop, clean application exit, needed migrations in an isolated clone, and complete reader startup.
2. **Userspace compatibility:** complete startup/exit inside QEMU with the target init/minirootfs; complete ELF/ABI and dynamic file-access inventory, file manifest, provenance/licensing, deterministic rebuild, and tests with at least two independent workloads. No physical device access.
3. **Peripheral adapters:** read-only hardware capability inventory extended to ioctl definitions/driver sources; safe emulator/test harness for e-ink, touch, power and suspend; no physical actuation under present hold.
4. **Recovery and boot engineering:** only after a separate explicit scope change, independently validated recovery path, reliable full-device backups and a non-destructive rollback strategy. Do not attempt bootloader change, overwrite partitions, or erase the stock OS in the current project phase.

## Dependency evidence categories

`ESSENTIAL_BOOT_KERNEL` (kernel, matching modules, platform metadata, boot firmware), `ESSENTIAL_OS` (init, configuration, device manager, mounts, runtime), `ESSENTIAL_APP` (KOReader, Ink Away, fonts/locale/assets and GNU compatibility), `OPTIONAL_FEATURE` (tested removable features), `UNUSED_CANDIDATE` (not needed in tested scenarios but unproven absent), `UNKNOWN_HOLD` (not traced / security / boot / resume), `PROPRIETARY_RESTRICTED` (must not publish). Never classify an object as safely removable solely because it was not opened by one run.

## Platform and upstream references

- Official Alpine Linux ARMv7 support and minimal boot architecture: https://wiki.alpinelinux.org/wiki/Architecture
- Alpine musl/BusyBox/OpenRC design: https://wiki.alpinelinux.org/wiki/Alpine_Linux:Overview
- `strace` file, process and network filters: https://man7.org/linux/man-pages/man1/strace.1.html
- Linux kernel `request_firmware()` API: https://kernel.org/doc/html/next/driver-api/firmware/request_firmware.html
- Lab126 modified Linux 3.0.35 kernel source reference including PW3 / `imx60_wario_defconfig`: https://github.com/katadelos/linux-3.0.35-lab126

**Safety status:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. Stock firmware, bootloader, partition images and raw captures stay private and unchanged. This is an architecture/research roadmap, **not** authorization to flash, install, boot or delete.

## Future optional feature compatibility: puzzles

Reserve a separate optional native C puzzle package in the long-term dependency map; see [optional puzzle pack dependency reservation](OPTIONAL-PUZZLE-PACK-DEPENDENCIES.md). Its build-time toolchain and possible runtime assets (dictionary, crossword clue packs, tile layouts, fonts and save storage) must be inventoried and licensed when implemented. This does **not** convert existing unknown/unobserved files into removable candidates, add games to the current R13 image, or justify direct Inkwell EPDC/framebuffer calls in synthetic PW3-OS. Any eventual minimal featureful rootfs must account for the chosen puzzle pack separately from KOReader's essential dependencies.
