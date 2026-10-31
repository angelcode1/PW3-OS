# PW3-OS — independent Kindle Paperwhite 3 userspace research

**Checkpoint:** R21.5 — `R21_ARM_FILEMANAGER_CORE_PASS` (user-provided Docker/QEMU ARM log; nine probes passed).

Goal: a minimal Alpine ARMv7 userspace with official KOReader `kindlepw2` and Ink Away, isolated GNU compatibility runtime, and a standalone PW3 device adapter. Current validation is **host-only**. The real FileManager and Ink Away canvas have passed synthetic ARM userspace tests, but independent boot and physical hardware integration have **not** been demonstrated.

**Safety:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NOT_BOOTABLE`. Do not change the Kindle's existing firmware, partitions, bootloader, startup, or hardware state.

- [`docs/HANDOVER.md`](docs/HANDOVER.md): verified milestone, prerequisites, limitations and R22 continuation.
- [`tools/collect_pw3_readonly.py`](tools/collect_pw3_readonly.py): opt-in, read-only SSH collection into a **local** ZIP (never uploads a Kindle dump to GitHub).
- [`docs/COLLECTION.md`](docs/COLLECTION.md): data handling and collection instructions.
- Full offline test-code handoff and historical release ZIPs: downloadable as `pw3-os-r21-handoff-complete.zip` from the ChatGPT handoff message; the collected proprietary runtime/firmware must remain local.

The source and test packages may be expanded from the full offline handoff; they are not included in this initial GitHub bootstrap commit. No physical-device functionality is implied.

For research and educational purposes only.
