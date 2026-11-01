# PW3-OS — independent Kindle Paperwhite 3 userspace research

**Checkpoint:** R21.5 — `R21_ARM_FILEMANAGER_CORE_PASS` (user-provided Docker/QEMU ARM log; nine probes passed).

Goal: a minimal Alpine ARMv7 userspace with official KOReader `kindlepw2` and Ink Away, isolated GNU compatibility runtime, and a standalone PW3 device adapter. Current validation is **host-only**. The real FileManager and Ink Away canvas have passed synthetic ARM userspace tests, but independent boot and physical hardware integration have **not** been demonstrated.

**Safety:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NOT_BOOTABLE`. Do not change the Kindle's existing firmware, partitions, bootloader, startup, or hardware state.

- [`docs/HANDOVER.md`](docs/HANDOVER.md): verified milestone, prerequisites, limitations and R22 continuation.
- [`docs/R22-CANDIDATE-STATUS.md`](docs/R22-CANDIDATE-STATUS.md): Initial R22 ARM run **FAILED** after plugin registration, because the fixture bypassed genuine FileManager teardown. R22.1 corrects the lifecycle and passes **42 local host tests (32 R21 + 10 R22)**; **ARM rerun is pending**. No boot or on-device execution is authorized.
- [`tools/pw3_collect_v6_hostcap.py`](tools/pw3_collect_v6_hostcap.py): **preferred, device-verified v6** opt-in, read-only SSH collector with Mac-side output caps; writes only a local ZIP. The earlier `tools/collect_pw3_readonly.py` is superseded and should not be used on old Kindle BusyBox.
- [`docs/COLLECTION.md`](docs/COLLECTION.md): v6 data handling and collection instructions.
- [`docs/PW3-HARDWARE-EVIDENCE-V6.md`](docs/PW3-HARDWARE-EVIDENCE-V6.md): sanitized 2026-11-01 real Kindle read-only inventory; **17/17 probes**, EPDC/Cypress/MAX77696/Upstart interface names established (not hardware operations).
- Full offline test-code handoff and historical release ZIPs: downloadable as `pw3-os-r21-handoff-complete.zip` from the ChatGPT handoff message; the collected proprietary runtime/firmware must remain local.

The source and test packages may be expanded from the full offline handoff; they are not included in this initial GitHub bootstrap commit. No physical-device functionality is implied.

For research and educational purposes only.

**Validation boundary:** The R21.5/R22 application work remains offline ARM/QEMU-only. The v6 physical Kindle collection was observational over already-enabled SSH; independent boot, framebuffer refresh, input events, frontlight operation, suspend and on-device KOReader remain untested.
