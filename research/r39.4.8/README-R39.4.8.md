# R39.4.8 — versioned experimental source

R39.4.7's actual ARM run FAILed at the first genuine FileManager-side metadata read. KOReader calls `DocumentRegistry:getProvider` during original `FileManager:openFile`, while the returned FM is still active; the earlier synthetic guard incorrectly required that FM singleton to be nil. The second `ReaderUI:init` read instead occurs after FileManager is closed.

This experimental R39.4.8 snapshot splits those two lifecycle phases without changing the original R25, R39.4, R39.4.5, R39.4.6 or R39.4.7 strict reviewers, production KOReader, device drivers or hardware. It contains the complete revised Lua guard, source checker, separate independent reviewer, 16 new negative/host tests and pinned baseline. Full source release ZIP is separately distributed in the research chat and includes all inherited harness files, Docker runner, fixture and a detailed `README-R39.4.8.md`.

**Status:** 478 host regressions PASS, source checksum and syntax PASS; new ARM/QEMU run PENDING. This repository version is not a bootable image.

Safety: `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Preserve the 976 `UNKNOWN_HOLD` files. Research and educational purposes only.
