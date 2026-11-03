# R40.4.3.7.4 — live Ink Away event-handler method lookup diagnostic

**2026-11-04. HOST TESTED; ARM/QEMU PENDING. Research and educational purposes only; NOT_BOOTABLE.**

The user's uploaded R40.4.3.7.3 report places the failure after original R36 project reload and R372 plugin registration, before `R404373_HANDLER_FUNCTION_PRESENT`. The original staged `plugins/ink-away.koplugin/main.lua` declares `onInkAwayOpen`, but a declaration alone does not establish its availability on the current live plugin instance. The previous R373 source identity check is not weakened or overridden.

The new guest differs from the original source-pinned R373 guard only by adding a **non-mutating, fixed-enumeration method-lookup observation** immediately before the existing `local entry_handler=owned_plugin.onInkAwayOpen` assertion. It examines raw instance fields, indexed lookup, Lua metatable/prototype membership and `__index` type without invoking or replacing the handler. Its public review exports only one bounded category: `FUNCTION_DISTINCT`, `ALIASED_TO_OPEN_CANVAS`, `INSTANCE_SHADOWED`, `PROTOTYPE_FUNCTION_UNRESOLVED`, `PROTOTYPE_NONFUNCTION`, `FUNCTION_INDEX_NO_HANDLER`, `NO_LIVE_HANDLER`, or `NO_VALID_STATE_RECORDED`. No original source filename, path, exception text or private guest output is exported. The unchanged original R373 assertion, native UIManager event, and R373→R372→R37→R36→R353→R35 reviewer chain are still mandatory for any ARM PASS.

Standalone conversation ZIP `pw3-os-r40.4.3.7.4-live-method-classifier.zip`, SHA-256 `d34e80327bfa44e85d52cb313f2d16bc467f73f93f50715dee1e43c1d473cef0`, 36,956 bytes, 11 files (10 checksummed entries). CRC and every SHA-256 digest verified, clean extraction and **20/20 host tests PASS**, three shell syntax checks PASS. Full executable code and Mac instructions are inside `README-R40.4.3.7.4.md` and `RUN-R404374-MAC.sh` in the standalone ZIP, not on GitHub. No private staged Lua sources, inventory or raw traces are committed.

Mac execution:

```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.4-live-method-classifier.zip -d pw3-os-r40.4.3.7.4-live-method-classifier
SRC="$HOME/Downloads/pw3-os-r40.4.3.7.4-live-method-classifier"
sh "$SRC/RUN-R404374-MAC.sh" test
sh "$SRC/RUN-R404374-MAC.sh" trial
```

The local trial uses a fresh `~/Downloads/pw3-os-r40.4.3.7.4-handler-lookup-first-run`; share only `R404374-REVIEW.json`, and optionally `R404374-SUMMARY.json` if strict PASS. Keep all private QEMU files and staged sources local. Original R26 2,070-item preflight, 13-file private capture, earlier source pins, existing offline prebuilt Docker image, no network, read-only stage/release, nonprivileged UID and disposable tmpfs HOME remain mandatory. Original partial QEMU syscall decoding cannot prove complete mutation coverage.

**Hard holds:** no device/firmware/hardware access or boot, no stage modifications, file deletion or pruning. The historical 347 stage regular-file open union was not recomputed; retain all 1,101 unobserved regular stage entries, 976 historical UNKNOWN_HOLD, and optional puzzle-pack hold. Complete dependency closure and R26 provenance are unproven; **NOT_BOOTABLE**.


## R40.4.3.7.4.1 host-manifest repair after user Mac failure (2026-11-04)

The user's Mac ran `test_r404374.R374Tests.test_archive_manifest` and encountered `verify.Refusal: manifest line count mismatch`. This was independently reproduced in a fresh extracted copy of the originally distributed ZIP when an ordinary Python import wrote `__pycache__/*.pyc`: the original `verify.manifest()` treated generated files as unlisted source contents. The old `shasum -a 256 -c` digests did not thereby fail. The corrected release counts generated `__pycache__/*.pyc`, macOS `.DS_Store`, and AppleDouble `._*` as **ignorable local metadata only**, while still checking every manifest-listed digest, refusing unlisted nonmetadata files, and rejecting modified payloads. It adds three adversarial manifest regression tests. The original Lua guest, original native event assertion, R373→R372→R37→R36→R353→R35 reviewer, QEMU probe, Docker runner, and source pin/reference file remain **byte-for-byte identical** to original R374.

The user's earlier `R404374_EXISTING_OFFLINE_IMAGE_UNAVAILABLE` occurred **after original source/R26 preflight PASS, before Docker execution**. The prior Docker image-inspect guard conflates Docker daemon/context errors with absent image. R374.1 therefore ships a separate **read-only** `CHECK-R404374-DOCKER.sh` that distinguishes missing Docker CLI, unreachable daemon and missing `pw3-r394-reopen-trial` image in the active context, without pulling, importing, retagging, building or changing Docker state. Source-stage and boot holds unchanged.

Corrected standalone ZIP: `pw3-os-r40.4.3.7.4.1-host-fix.zip`, SHA-256 `b6aa5f169be296a4fe469b0649fdb0f3c9741ab410ecfbfc3ea7ecc5d2160119`, 39,093 bytes, 12 members (11 SHA-256 manifest entries). All ZIP CRC and member hashes PASS; fresh extraction runs **23/23 host tests PASS** with Python bytecode generation enabled, again PASS with generated caches left in place, and the original Mac wrapper's `test` mode PASS. Full code and commands supplied as a separate conversation ZIP; no private files are committed. ARM/QEMU remains **PENDING** until the prebuilt image is found; no R374 handler-classifier result exists yet. **NOT_BOOTABLE**, no device/firmware/hardware writes, boot, removal, or pruning.
