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
