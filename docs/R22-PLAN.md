# R22 — real plugin-loader integration

**Start state:** R21.5 ARM PASS, all nine probes confirmed by the user; genuine FileManager import, FileChooser construction, 1072×1448 in-memory repaint, stock in-memory settings flush and close all verified. Plugin activation deliberately held off.

The next milestone is **actual Ink Away 4.4.0 plugin loading and navigation** through KOReader's real FileManager using the genuine `frontend/pluginloader.lua` and `plugins/ink-away.koplugin/main.lua` (not a synthetic replacement).

1. Preserve R21.5 fixture and all nine regression probes unchanged.
2. Enable **only** Ink Away via the original PluginLoader public interface and temporary settings; deny every other plugin, updater and network action.
3. Verify real instance ownership by FileManager, action registration and menu binding.
4. Open actual Ink Away view through the registered FileManager action, exercise UIManager show/paint/stroke/close, reopen the temporary drawing and confirm navigation back to FileManager.
5. Require negative controls for Amazon LIPC, filesystem escape, shell, device access, sysfs writes and network. Fail closed on any unexpected operation.
6. Keep Alpine ARMv7 musl + isolated GNU glibc 2.20 and original `kindlepw2` KOReader release. All ARM tests remain inside offline Docker/QEMU with fake screen and touch.

Follow-on: broader `reader.lua` app startup boundary; minimal rootfs dependency observations and **reviewed** allowlist, not unobserved file deletion; read-only device evidence as a separately approved task. No boot image, device installation or hardware actuation is authorized.

**Hold:** `NO_FIRMWARE_WRITES_HOLD; NO_BOOT_ACTIONS; NOT_BOOTABLE`.
