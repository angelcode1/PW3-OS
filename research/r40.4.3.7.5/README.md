# R40.4.3.7.5 — authenticated native KOReader HandlerSandbox plugin event trial

**Research and educational purposes only. Host tested; ARM/QEMU pending. NOT_BOOTABLE.**

The uploaded R374 public diagnostic reports `PROTOTYPE_NONFUNCTION` after original R36 draw/save/reload and live Ink Away plugin registration. Inspection of tagged KOReader v2026.07.2's `pluginloader.lua` and `eventlistener.lua` identifies a plausible concrete cause: `sandboxPluginEventHandlers` wraps original `onInkAwayOpen` from a Lua function into a callable `HandlerSandbox` table with original `.f` and metatable `__call`. A bare `type(handler)=='function'` assertion in the previous guest necessarily fails if that same staged behavior applies. No prior R37–R374 plugin-event PASS is claimed and no raw trace replay was performed.

R375 is a single exact guest-block replacement relative to the SHA-pinned R374.1 original guard: authenticate the live plugin class member, original KOReader `__call` function source, wrapper `context/fname/log_stacktrace` and the actual inner Lua function `.f` from the identical source as the previously authenticated Ink Away `openCanvas`. It never calls, replaces or unwraps the plugin handler. The original `UIManager:sendEvent(Event:new('InkAwayOpen'))`, original second-view lifecycle, and original **independent** strict R373→R372→R37→R36→R353→R35 review chain remain mandatory for any result. The prior R373 checkpoint names are retained only after the stronger wrapper/inner-function checks, so their semantic meaning is explicitly documented. The old R374 **diagnostic-only function-state PASS requirement** is superseded, not used to bypass the older real lifecycle reviewers.

Before any QEMU execution a new static source check reads the original staged `frontend/pluginloader.lua`, `frontend/ui/widget/eventlistener.lua`, and `frontend/ui/widget/widget.lua` and refuses missing or differing wrapper construction, metatable `__call`, handler sandboxing or native event dispatch. The original R26 2,070-item and 13-file private staged Lua preflight and all original prior source pins remain mandatory. The stage and original release bind read-only; Docker uses the existing prebuilt offline image only, network off, privileges dropped, unprivileged UID/GID, disposable tmpfs HOME. The check is fail-closed; it does not mutate any original sources or boot hardware.

**Standalone versioned conversation ZIP:** `pw3-os-r40.4.3.7.5-handler-sandbox-fix.zip`. SHA-256 `a350aa9dd854dd3365a0c06678b0b35d7ac3afbdd3d6b7a5a2cca0def8041366`, 41,370 bytes, 12 archive members, 11 checked manifest payloads. Clean extraction, ZIP CRC and all SHA-256 entries PASS. **22/22 host tests PASS**, including replay gate refusal, nonzero exit, duplicate/missing markers, sandbox source contract, unlisted/tampered source, symlink refusal and metadata-cache handling; tests passed twice after a clean extraction, Mac-style test wrapper PASS; four shell syntax checks PASS. The executable release, full source, checksums and exact Mac commands are in the versioned conversation ZIP; original private staged Lua/source paths/traces have not been committed.

Mac commands:

```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.5-handler-sandbox-fix.zip -d pw3-os-r40.4.3.7.5-handler-sandbox-fix
SRC="$HOME/Downloads/pw3-os-r40.4.3.7.5-handler-sandbox-fix"
sh "$SRC/RUN-R404375-MAC.sh" test
sh "$SRC/RUN-R404375-MAC.sh" stage-check
sh "$SRC/CHECK-R404374-DOCKER.sh"
# Only when checks pass, with a *fresh* output:
sh "$SRC/RUN-R404375-MAC.sh" trial
```

The new run directory defaults to `~/Downloads/pw3-os-r40.4.3.7.5-sandbox-handler-first-run`. Share only public `R404375-REVIEW.json` and, on strict PASS, `R404375-SUMMARY.json`; keep the private `trace/`, R26 inventory and original staged sources local. **ARM/QEMU R375 not run yet**. No physical touch/stylus or genuine Tools-menu tap. Prior 347-file stage observed-open union **not recomputed**; retain all 1,101 unobserved staged regular files and 976 old UNKNOWN_HOLD records. Decoder incomplete, R26 provenance unauthenticated, dependency closure unproven; boot, device/firmware/hardware writes, file removal and pruning remain prohibited. **NOT_BOOTABLE.**


## User-uploaded R40.4.3.7.5 public ARM review PASS (2026-11-04)

The uploaded `R404375-REVIEW.json` and `R404375-SUMMARY.json` are byte-for-byte identical; SHA-256 `4c203e95ba6b94d9391e2a7e63817891750e522ff3f255b24cc340e6706431b9`. The review reports `R40_4_3_7_5_ORIGINAL_SANDBOX_HANDLER_AND_NATIVE_PLUGIN_EVENT_ARM_PASS`, zero guest exit, original callable KOReader HandlerSandbox and its underlying pinned Lua function authenticated, genuine UIManager `InkAwayOpen` dispatch, a second original InkAwayView opened/closed, and the earlier R36 draw/save/reload completed in the **same run**. The original R373→R372→R37→R36→R353→R35 strict review chain reports PASS. This is a bounded synthetic ARM/QEMU PASS reported in the two matching **public records**, not independent replay of private raw stdout/stderr/exit. Incomplete syscall decoder and residual isolation uncertainty remain.

The original FileManager Tools-menu *widget callback* was **not exercised**; direct native event proof cannot substitute for that UX path or physical touch/pen. Next evidence should source-pin original FileManager menu registration and menu-widget event handling, and exercise the real menu callback through the original application path without mocks or a direct plugin-method call. Historical observed stage-open union 347 **not recomputed**, all 1,101 unobserved regular stages and 976 historical UNKNOWN_HOLD retained. Complete dependency closure and R26 provenance unproven; no real PW3/firmware/hardware access, boot, file removal, or pruning authorized. **NOT_BOOTABLE**.
