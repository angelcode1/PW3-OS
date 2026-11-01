# PW3-OS — independent Kindle Paperwhite 3 userspace research

**Checkpoint:** R23.4 — `R23_4_UI_IMPORT_ARM_PASS` (user-supplied offline ARM/QEMU, genuine `reader.lua` through Bidi and UIManager import, synthetic input handshake). Prior R22.1 genuine PluginLoader → Ink Away and R23.2 premigration bootstrap also PASS. **Full `reader.lua` FileManager startup, device operation and independent boot remain unverified.**

Goal: a minimal Alpine ARMv7 userspace with official KOReader `kindlepw2` and Ink Away, isolated GNU compatibility runtime, and a standalone PW3 device adapter. Application validation remains **offline ARM/QEMU with synthetic UI**. Genuine FileManager → PluginLoader → Ink Away menu, canvas, stroke/save/return and clean close are covered by the user's R22.1 log. The separate v6 physical interface inventory was read-only; independent boot and physical hardware operation have **not** been demonstrated.

**Safety:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NOT_BOOTABLE`. Do not change the Kindle's existing firmware, partitions, bootloader, startup, or hardware state.

- [`docs/HANDOVER.md`](docs/HANDOVER.md): verified milestone, prerequisites, limitations and R22 continuation.
- [`docs/R22-CANDIDATE-STATUS.md`](docs/R22-CANDIDATE-STATUS.md): R22.0 teardown regression resolved in R22.1; **three ARM gates and fail-closed reviewer PASS in the user-supplied log**. R21 + R22 host regressions: 42 tests passed; no Kindle device execution.
- [`docs/R23-PLAN.md`](docs/R23-PLAN.md): genuine `reader.lua` startup roadmap. [R23.4 status](docs/R23.4-STATUS.md): user-reported **R23.4 ARM UIManager-import PASS** with prior R23.3 failure preserved; no FileManager/event-loop execution yet.
- [`docs/PW3-MINIMAL-USERSPACE-ROADMAP.md`](docs/PW3-MINIMAL-USERSPACE-ROADMAP.md): long-term independent Alpine ARMv7 + KOReader rootfs strategy; dependency tracing, manifest-based allowlist, kernel/firmware essentials and recovery gates. Not a boot/install plan.
- [`docs/NETSURF-EINK-BROWSER-PLAN.md`](docs/NETSURF-EINK-BROWSER-PLAN.md): optional separate-process NetSurf framebuffer browser, cross-compile/memory-surface-first workflow and InkSurf research reference; no hardware access or browser ARM result claimed.
- [`docs/R24.2-R25.2-STATUS.md`](docs/R24.2-R25.2-STATUS.md): user's R24.1 ARM run **FAILED** at guarded `/proc/meminfo` read; the corrected R24.2/R25.2 synthetic-memory retry passes **110 local host tests** (ARM pending). R24/R24.1 failures preserved. Run R24.2 before R25.2.
- [`tools/pw3_collect_v6_hostcap.py`](tools/pw3_collect_v6_hostcap.py): **preferred, device-verified v6** opt-in, read-only SSH collector with Mac-side output caps; writes only a local ZIP. The earlier `tools/collect_pw3_readonly.py` is superseded and should not be used on old Kindle BusyBox.
- [`docs/COLLECTION.md`](docs/COLLECTION.md): v6 data handling and collection instructions.
- [`docs/PW3-HARDWARE-EVIDENCE-V6.md`](docs/PW3-HARDWARE-EVIDENCE-V6.md): sanitized 2026-11-01 real Kindle read-only inventory; **17/17 probes**, EPDC/Cypress/MAX77696/Upstart interface names established (not hardware operations).
- Full offline test-code handoff and historical release ZIPs: downloadable as `pw3-os-r21-handoff-complete.zip` from the ChatGPT handoff message; the collected proprietary runtime/firmware must remain local.

The full R21/R22 source-only test packages and R23 preflight remain separately downloadable conversation artifacts; this GitHub repository includes sanitized documentation and selected patches, not the private staged runtime. No physical-device functionality is implied.

For research and educational purposes only.

**Validation boundary:** The R21.5/R22.1 application work remains offline ARM/QEMU-only; R23 is source preflight only. The v6 physical Kindle collection was observational over already-enabled SSH; independent boot, framebuffer refresh, input events, frontlight operation, suspend and on-device KOReader remain untested.
