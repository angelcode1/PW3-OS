# R40.4.3.7.3 — original InkAway handler source identity diagnostic/candidate correction

**Research and educational purposes only. HOST TESTED, ARM/QEMU PENDING; NOT_BOOTABLE.**

The user-uploaded R372 public review (SHA-256 `9ee80181f1688d36e10faffef4cf4c4a26596f9a4997b4e397144c542e4093ab`) shows original R36 project reload, original FileManager restore and live plugin registration checkpoints completed, but failure before `R404372_PLUGIN_HANDLER_SOURCE`. The strict reviewer correctly records a HOLD, not a new plugin entry PASS. Private QEMU raw stdout/stderr/exit were not independently replayed. The prior bounded R36 drawing/save public PASS remains historical and not invalidated.

The collected private, staged original InkAway `main.lua` defines both `onInkAwayOpen` and `openCanvas`. R372 used a suffix-based `debug.getinfo` test for the live `onInkAwayOpen` handler. The new source-pinned R373 guard replaces *only that single test* with two fail-closed checks. First the live handler must be a distinct Lua function; second it must share the identical original Lua source with the previously authenticated `openCanvas`, whose original source suffix was already established in R34 and whose stage SHA-256 is pinned in R37 preflight. The check never creates/replaces/wraps a handler. The unchanged genuine `UIManager:sendEvent(Event:new('InkAwayOpen'))` is dispatched only after all original R372 conditions pass.

New fixed markers: `R404373_HANDLER_FUNCTION_PRESENT` then `R404373_HANDLER_SAME_PINNED_SOURCE`. If either fails, the public report names only the failure boundary. If both pass, the guest may attempt the original event and second-view lifecycle. The old R372 reviewer and its unchanged R37→R36→R353→R35 strict reviewer chain are **mandatory**; source or host PASS cannot produce ARM PASS by itself. No actual Tools menu click, physical touch, stylus or device boot is tested.

**Standalone conversation ZIP:** `pw3-os-r40.4.3.7.3-handler-provenance.zip`, SHA-256 `87118ff69cf2aee75a609126f2d8c3cc0633333e7678b358719e49622bd5c776`, 37,813 bytes, 11 ZIP members (10 checksummed payloads). Clean extraction, ZIP CRC, all member digests, three shell syntax tests and **24/24 host tests PASS**. Full runnable code, Mac wrapper and exact command documentation are in `README-R40.4.3.7.3.md` inside the archive. Private original staged Lua and raw paths/trace are not committed.

Mac procedure after extracting earlier releases under their original directory names in `~/Downloads`:

```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.3-handler-provenance.zip -d pw3-os-r40.4.3.7.3-handler-provenance
SRC="$HOME/Downloads/pw3-os-r40.4.3.7.3-handler-provenance"
sh "$SRC/RUN-R404373-MAC.sh" test
sh "$SRC/RUN-R404373-MAC.sh" trial
```

The trial requires original R372/R37/R36/R353/R35 releases and original R26 2,070-item stage preflight, original 13-file private staged source recheck, the existing **prebuilt** offline Docker image, stage bind read-only, network off, dropped capabilities, nonprivileged user, isolated tmpfs HOME and prior decoded mutation guard. It refuses an existing output directory. On guest success plus unchanged strict review PASS it writes identical public `R404373-REVIEW.json` and `R404373-SUMMARY.json`; on failure, share only the public review or categorical terminal refusal. Keep private `trace/` and staged sources local.

**Immutable holds:** no authenticated R26 provenance, no complete dependency closure, QEMU syscall decoder incomplete, historic 347 staged regular-file opens *not recomputed*, 1,101 unobserved stage regular files and 976 old UNKNOWN_HOLD preserved. `NOT_BOOTABLE`; no device/firmware/hardware writes, real menu/physical touch/boot or file pruning authorized.
