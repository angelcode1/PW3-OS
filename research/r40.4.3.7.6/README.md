# R40.4.3.7.6 — original FileManager Tools-menu source collector

**Research and educational purposes only; source-only, no guest run; NOT_BOOTABLE.**

The user uploaded matching `R404375-REVIEW.json` and `R404375-SUMMARY.json`, SHA-256 `4c203e95ba6b94d9391e2a7e63817891750e522ff3f255b24cc340e6706431b9`; public reviewer verdict `R40_4_3_7_5_ORIGINAL_SANDBOX_HANDLER_AND_NATIVE_PLUGIN_EVENT_ARM_PASS`. This reported offline ARM/QEMU trial authenticates the original callable HandlerSandbox and underlying Lua handler, passes genuine `UIManager:sendEvent(Event:new('InkAwayOpen'))` to open/close a second InkAwayView, and retains the original R36 drawing/save/reload and R373→R372→R37→R36→R353→R35 strict reviewer chain. The two public JSON files are identical, not independent raw trace replays; raw QEMU stderr/stdout/exit were not uploaded. **The actual visible FileManager Tools-menu widget selection has not been exercised.**

The prior **private**, locally staged R40436 source archive contains 152 Lua modules, but excludes the original FileManager menu widget and TouchMenu implementation. Before inventing an offline GUI event, this milestone bundles a **read-only collector** of nine originals: FileManagerMenu, TouchMenu, Menu, plugin loader, EventListener, Widget, and the existing InkAway main/FileManager/UIManager modules. The collector verifies the earlier 152-source archive's exact SHA-256 `0fd39fc845e390698e7688ea58ee4033cd9abcf3d8cc99e3c5e57920c250e107`, checks the three previously captured originals remain identical in the staged rootfs, refuses symlinked or invalid staged sources, then writes a separate private checksum-verified source archive and public category-only summary under new, nonexisting paths. It never executes Lua, starts Docker/QEMU, accesses a Kindle or modifies the source stage. Static source-method markers are candidates, not a semantic call graph or runtime proof.

**Standalone conversation ZIP** `pw3-os-r40.4.3.7.6-menu-source-collector.zip`: SHA-256 `a7ed49cf57dc16cf71113ffd429cd0f2be2a7d9c31d9bc5802c1fb4b2db47a53`, 9,766 bytes, 7 archive members (6 SHA256SUMS payloads). Clean extraction, ZIP CRC/member SHA256 PASS; **18/18 host tests PASS**, including source hash mismatch, symlink, unlisted-release, mismatched old archive, tampered new archive, existing-output, static contract HOLD and metadata-cache cases. Clean and cache-enabled repeat host tests PASS. Full executable Python, tests, manifests and Mac commands are inside the versioned ZIP; no original staged source files are committed.

Run on Mac:

```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.6-menu-source-collector.zip -d pw3-os-r40.4.3.7.6-menu-source-collector
SRC="$HOME/Downloads/pw3-os-r40.4.3.7.6-menu-source-collector"
sh "$SRC/RUN-R404376-MAC.sh" test
sh "$SRC/RUN-R404376-MAC.sh" collect
```

The collector reads the previously verified original R13 staged rootfs at `~/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs` and the prior R40436 private source archive in Downloads. It creates `~/Downloads/R404376-MENU-SOURCE-AUDIT-PUBLIC.json` (shareable) and `~/Downloads/R404376-MENU-SOURCES-PRIVATE.zip` (private; may be uploaded to this conversation for source analysis but **never publicly committed**). If a path already exists, collector refuses overwrite and must not be rerun into it. If source signatures differ it reports the source-only HOLD and still captures the original files. If integrity check fails it refuses before writing output.

Next **prospective** work: source-pin the actual FileManager Tools-tab registration, original TouchMenu item selection and InkAwayView activation, then implement an offline bounded QEMU test with genuinely exercised native menu-widget selection and original strict reviewer; do not simply call `menu_items.inkaway.callback()` and label it a physical tap. No actual menu-widget or physical display/pen result is claimed. Original stage regular-file observed-open union 347 *not recomputed*, 1,101 unobserved regular source files and 976 old UNKNOWN_HOLD records retained. QEMU decoder incomplete; R26 provenance unauthenticated; dependency closure unproven. **NOT_BOOTABLE; NO_DEVICE_ACCESS; NO_FIRMWARE_OR_HARDWARE_WRITES; NO_BOOT; NO_FILE_REMOVAL; NO_PRUNING.**


## User-uploaded menu source audit and private archive (2026-11-04)

The user supplied `R404376-MENU-SOURCE-AUDIT-PUBLIC.json` and `R404376-MENU-SOURCES-PRIVATE.zip`. The archive SHA-256 is `44889dbfd47a18854beaeec2c739bb11afca1033c10c125ec2f576573d568e83`, matching the public summary. Independently inspecting the ZIP confirms 9 original staged Lua files, archive CRC PASS and each member SHA-256 equals its embedded private manifest. The public report states 330,308 uncompressed source bytes and all five source-contract candidates present, while preserving original-stage integrity. **Source-only:** no original FileManager Tools-menu event, guest ARM execution, physical tap or menu selection is proved.

Source inspection of the original staged InkAway `main.lua`, FileManagerMenu and TouchMenu shows this distinct route: InkAway `init` registers a plugin widget with FileManagerMenu, FileManagerMenu builds a sorted Tools tab through original MenuSorter, and TouchMenu `onMenuSelect` evaluates the registered `inkaway` item callback. This is separate from the previously validated original native `InkAwayOpen` HandlerSandbox route. The [R40.4.3.7.7 experimental source-bound native menu-widget selection](../r40.4.3.7.7/README.md) retains the prior R375 strict review chain and tests an additional view via the original TouchMenu method. It does **not** claim original TouchMenuItem tap gestures or physical pen input. Keep the private Lua archive and stage paths off public GitHub.
