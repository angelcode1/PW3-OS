# Future optional puzzle pack — Alpine/PW3-OS dependency reservation

**2026-11-03 • PLANNING ONLY • no implementation, binaries, firmware writes or stage changes • `NOT_BOOTABLE`.**

This document records a **possible future feature** requested for the separate independent Kindle PW3 Alpine userspace. It must **not** be interpreted as evidence that the R13 staged rootfs, R26 inventory, KOReader application or R40 trace currently contains these puzzle programs. They are not part of the current required-core closure or the 347 observed-open regular files. Preserve unobserved files without guessing they are expendable; future feature-specific files would need their own content and runtime evidence before being classified.

## Verified upstream architecture (reference, not integrated code)

At Inkwell Git commit [`cac76f465518a771486689fd3f41a9fe45a4b614`](https://github.com/pragyaangaur/Inkwell/commit/cac76f465518a771486689fd3f41a9fe45a4b614):

- [`src/ui/chess.c`](https://github.com/pragyaangaur/Inkwell/blob/cac76f465518a771486689fd3f41a9fe45a4b614/src/ui/chess.c) implements a self-contained C chess engine and Easy/Medium/Hard modes; it saves in `/mnt/us/chess`. **Chess exists in Inkwell, not verified as installed in our PW3-OS stage.**
- [`src/ui/home.c`](https://github.com/pragyaangaur/Inkwell/blob/cac76f465518a771486689fd3f41a9fe45a4b614/src/ui/home.c) parses `/etc/own/apps` entries as `Label|icon|command`, with a 16-entry limit; the [current apps file](https://github.com/pragyaangaur/Inkwell/blob/cac76f465518a771486689fd3f41a9fe45a4b614/src/rootfs/etc/own/apps) has 13 entries. The `page` icon exists, so `Puzzles|page|/usr/local/bin/puzzles` is *a future Inkwell example*, **not an approved PW3-OS launcher edit**.
- [`tools/kcc`](https://github.com/pragyaangaur/Inkwell/blob/cac76f465518a771486689fd3f41a9fe45a4b614/tools/kcc) targets static ARMv7 `armv7-alpine-linux-musleabihf` C via clang/lld, and [`build-ui.sh`](https://github.com/pragyaangaur/Inkwell/blob/cac76f465518a771486689fd3f41a9fe45a4b614/build-ui.sh) builds the individual UI executables. [`build-rootfs.sh`](https://github.com/pragyaangaur/Inkwell/blob/cac76f465518a771486689fd3f41a9fe45a4b614/build-rootfs.sh) copies those programs into `/usr/local/bin`; a future puzzle integration would need an explicit build and image-install rule rather than just an app entry.
- [`src/ui/ui.h`](https://github.com/pragyaangaur/Inkwell/blob/cac76f465518a771486689fd3f41a9fe45a4b614/src/ui/ui.h) has touch/layout primitives. [`src/ui/eink.h`](https://github.com/pragyaangaur/Inkwell/blob/cac76f465518a771486689fd3f41a9fe45a4b614/src/ui/eink.h) directly accesses framebuffer, EPDC ioctls and input; **do not import or execute this hardware layer under PW3-OS's present NO_DEVICE_ACCESS hold**.
- Inkwell's repository license is MIT; reused code must include attribution. Third-party included fonts/assets may carry independent notices.

**Architectural separation:** Inkwell's standalone framebuffer application and the current KOReader/glibc-compat synthetic PW3-OS application are *different integrations*. An optional static musl puzzle process is a build candidate only after a safe, separately audited interface exists; it is **not** an additional library to insert inside KOReader or a reason to alter the current R13 stage.

## Feature dependency matrix (design targets, all NOT IMPLEMENTED)

| Game | Engine candidate | Build/runtime candidates | Optional data / state | Priority |
|---|---|---|---|---|
| Sudoku | Simon Tatham **Solo** (MIT) | C engine, integer-grid renderer, touch and input abstraction, RNG; possible `libm` depending on actual linked symbols | Small puzzle seeds/save | 1 |
| KenKen | Simon Tatham **Keen** (MIT) | C arithmetic-cage engine, same grid/input/render adapter | Seeds and saved state | 1 |
| Crosswords | Compact custom solver/UI or separately licensed implementation | C grid/clue editor, text-entry UI, existing glyph/font support | Pre-generated clue/answer packs, **each with provenance and redistribution rights** | 2 |
| Mahjong Solitaire | Custom board/tile matching | C static tile layouts, grayscale tile renderer, hit-testing | Validated, solvable layout data | 3 |
| Bananagrams-style solo tiles | Custom word-placement logic | Shared C dictionary lookup, tile UX, save state | Filtered offline wordlist, data license notices | 4 |
| Scrabble-style Word Tiles | Reuse local word-game engine | Score/turn/optional AI logic, shared dictionary | Letter distribution and rules data | 5 |
| Chess | Inkwell's existing C chess engine if integrating Inkwell | No *second engine* planned; preserve its existing fonts and saves | Existing `/mnt/us/chess` within Inkwell only | Existing, optional shortcut |

Target a **single optional, exit-on-close static ARMv7 musl executable** with a shared renderer and text-input adapter, using fixed-size game state; no SDL, GTK, browser, Python GUI, daemon, or extra background service as a *design requirement*. Its actual executable size, peak RAM, `DT_NEEDED`, asset size and performance must be **measured after a real build**. The proposed 1–3 MB pack budget excluding already shared fonts is an **unmeasured engineering target**, not a demonstrated property or a reason to discard assets.

## Dependencies to reserve for future closure

1. **Native engine and support:** optional `/usr/local/bin/puzzles` and selected C implementations, static musl ABI/toolchain inputs, compile-time portability configuration, any actually linked math/native support. Record ELF interpreter, float ABI, sections, symbols, `DT_NEEDED`, build hashes, actual memory/size. Static linkage does not eliminate kernel ABI and device-interface concerns.
2. **Presentation/interaction:** grayscale/partial-update-safe board rendering, touch/button/key navigation, on-screen keyboard and fonts/glyphs **provided by the chosen future host UI**, not automatically by the existing KOReader process. E-ink screen and touch must be simulated offline until separately authorized hardware validation.
3. **Content assets:** license-reviewed puzzle seed packs, tile layouts, fonts and optional dictionaries (possibly compressed sorted or DAWG/trie). Word-game lookup should share **one offline dictionary**, not require SQLite at runtime unless empirically justified. Choose explicit language/dialect and normalize case/accent/apostrophe behavior.
4. **Persistent user state:** optional `/mnt/us/puzzles/` is a *proposed* path taken from Inkwell's userstore pattern, **not proof of an available, safe mounted filesystem in our PW3-OS image**. Require verified permissions, mount ownership, atomic save/rename, corrupt-save recovery, backup policy and no stock userstore writes in the present research phase.
5. **Licensing:** Simon Tatham's collection licenses Solo and Keen under MIT: https://www.chiark.greenend.org.uk/~sgtatham/puzzles/ . ESDB/SCOWL: https://github.com/en-wl/wordlist ; keep the file `Copyright` and its conditions, **including additional Australian-English and large-wordlist notices when applicable**. Distinguish the engine's license from each crossword clue pack, font and dictionary; do not bundle a proprietary Scrabble/Bananagrams trademark, tile graphics or wordlist on the strength of generic game rules.

## R40+ evidence contract

- Add `OPTIONAL_FUTURE_PUZZLES_NOT_BUILT` to the **planning manifest only**. Never insert absent files into the R26 inventory or mark them `OBSERVED_RUNTIME`, `ESSENTIAL_OS` or safe-to-delete.
- Mark puzzle scenarios `NOT_TESTED_HOLD` until an independently built executable exists and an isolated read-only synthetic UI adapter can drive its start, Sudoku/Keen game creation, touch/navigation, solve/check, save/reopen, keyboard and clean exit **without a device**. Later add crossword/tile/word scenarios separately.
- For every supported scenario, pin binaries and asset contents, capture runtime opens and failed lookups as with R40.0.2, reconcile static and dynamic dependencies and preserve unobserved assets under `UNKNOWN_HOLD`. Verify no new network, unexpected writes or native ABI compatibility assumptions.
- Future **optional** feature coverage is tracked separately from the **core** KOReader/Ink Away milestone: R40.4 can advance on its already-planned core scenarios while this puzzle feature stays explicitly `NOT_TESTED_HOLD`. Conversely, do not claim a complete **featureful** rootfs when promised puzzle components have not been built or tested.
- No installation, app-menu edits, image generation/boot, pruning, device access or firmware writes are authorized. No source code, binary, dictionary or data asset has been imported from Inkwell or the other upstream projects in this change.

**Immutable:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Preserve all previously observed and unobserved R13/R26 stage files (including 976 original `UNKNOWN_HOLD` entries). Research and educational purposes only.
