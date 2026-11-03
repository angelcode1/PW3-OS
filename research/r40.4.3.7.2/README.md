# R40.4.3.7.2 — source-bound split-assertion native plugin event trial

**HOST TESTED ONLY; ARM/QEMU PENDING; NOT_BOOTABLE. Research and educational purposes only.**

The prior user's R40.4.3.7.1 public diagnostic reports QEMU exit 1 after the original R40.4.3.6 project reload checkpoint but before any R37 plugin event checkpoint. It does not identify which of the two R37 pre-route Lua assertions failed and does not reclassify the earlier R36 synthetic save PASS.

This release reuses the original SHA-pinned R40.4.3.7 guard with exactly one replacement: a combined FileManager/active-plugin/handler/UIManager/menu assertion is split into the same five original condition checks, each printing one static checkpoint upon success. It does not bypass or weaken any original assertion. The unchanged R37 original event `UIManager:sendEvent(Event:new('InkAwayOpen'))` is only reached if all five checks pass. It is not a real menu click, hardware action or physical touch.

Source preflight validates the original R37 source release, old R36/R353/R35 prereqs and the unchanged staged InkAway main/KOReader UIManager sources. The original R35 preflight rechecks the previous 2,070 R26 inventory entries and 13 staged private Lua sources. The original R37 strict reviewer, including its R36 → R353 → R35 original reviewer chain, remains mandatory; additional strict checks require ordered split checkpoint markers, zero QEMU exit and decoded scratch-only mutations. On failure the new public JSON reports only predeclared checkpoint names, counts and flags. Guest stdout, QEMU stderr, private source and stage paths remain local.

**Standalone ZIP**: `pw3-os-r40.4.3.7.2-boundary-checkpoints.zip`, SHA-256 `804915595b6bf2c20980ca42f052df9d081b3a7c8b360db9fc2f8ad5a8fe2cfc`; 36,859 bytes, 11 files (10 checksummed payloads). Clean extraction, ZIP CRC and every manifest SHA-256 verified. **18/18 host tests PASS**; shell syntax PASS. The full sources, additional reviewer, exact Mac commands and one-command launcher reside inside the versioned ZIP in `README-R40.4.3.7.2.md`.

Execute on user's Mac from `~/Downloads` after extracting:
```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.2-boundary-checkpoints.zip -d pw3-os-r40.4.3.7.2-boundary-checkpoints
SRC="$HOME/Downloads/pw3-os-r40.4.3.7.2-boundary-checkpoints"
sh "$SRC/RUN-R404372-MAC.sh" test
sh "$SRC/RUN-R404372-MAC.sh" trial
```

The trial uses a **fresh output directory** and the existing prebuilt offline Docker image only, with rootfs bind readonly, network disabled, dropped capabilities, unprivileged user and disposable tmpfs HOME; no physical PW3 access. Share only `R404372-REVIEW.json` and, if generated on strict PASS, `R404372-SUMMARY.json` from `~/Downloads/pw3-os-r40.4.3.7.2-event-boundary-first-run`. If the preflight fails before a review is produced, share only the final fixed terminal marker. Do not share `trace/`, private staged sources or raw paths.

No runtime R372 result exists yet. QEMU syscall decoder incomplete, 347 historic stage opens **not recomputed**, 1,101 unobserved regular staged files and 976 historic UNKNOWN_HOLD retained; provenance and complete dependency closure remain unknown. **NOT_BOOTABLE; no device, firmware, hardware, boot, pruning or file removal authorized.**
