# Codex NetSurf browser — staged implementation

## Current implementation

The Codex Alpine image builder now requires the exact `netsurf-framebuffer 3.11-r1` package from Alpine **v3.24/community/armv7**. It resolves package dependencies using the project's APKINDEX resolver and stages the browser into the Alpine image. It fails closed if the expected package is missing or changes version. The builder validates the installed binary is ELF32 little-endian ARM and that `/usr/share/netsurf` resources exist. The build manifest records `browser.state=staged-unverified`.

The `/usr/local/bin/codex-browser` launcher supports `--diagnose` and `--offscreen-test`. The latter runs NetSurf using its **RAM-only** libnsfb surface against the local `/usr/share/codex/browser-smoke.html` HTML/CSS/link/form fixture. A RAM surface does not provide a visible browser and requires deliberate termination in automated tests. All other invocations are refused. The browser is not added to the Home app menu yet, since that would imply a usable display/input backend.

The source also includes `codex-eink-compositor.c/.h`: pure offscreen RGBA-byte to grayscale conversion, bounded 64x64 dirty tile grouping, a 45% full-refresh threshold, and a 12-partial-refresh full refresh rule. The host C regression covers color quantization, changed tiles, edge clipping, and refresh choice. **It does not drive any Kindle EPDC ioctl** and does not assert that libnsfb's pixel layout is RGBA bytes. Pixel format matching and gamma/dithering require evidence before the interface is connected.

## Synthetic touch adapter

`codex-touch-bridge.c/.h` now translates bounded raw touchscreen coordinates to logical absolute pointer motion, press, release and cancel events, with optional axis swap and inversion. Its host test covers tap, drag, overlapping-touch rejection, cancellation, rotation and malformed calibration. This is **not** the real Cypress evdev reader, and no NetSurf `nsfb_event_t` hook or Kindle device node is opened by this code. The future NetSurf surface must explicitly map pointer motion to `NSFB_EVENT_MOVE_ABSOLUTE` and press/release to the mouse-button key events using the exact pinned libnsfb ABI.

## CI

`.github/workflows/codex-netsurf-offscreen.yml` runs Python builder tests, the host C compositor and touch-bridge tests and an Alpine ARMv7/QEMU Docker smoke test with the browser's `-f ram` surface. The smoke test asserts the NetSurf process stays alive long enough for a bounded offline startup check; this is **not proof of rendered pixel correctness or successful navigation**. Do not claim PASS until Actions reports a passing run.

## Missing before device browser can be enabled

1. Confirm the full Alpine package dependency closure, dynamic linker and old Linux 3.0.35 syscall compatibility in ARM execution against the *built* rootfs, not only a separate Alpine container.
2. Connect NetSurf/libnsfb's actual pixel buffer format to the grayscale compositor and test deterministic rendered screenshots/content, drawing invalidation and memory use under ARM/QEMU.
3. Implement a PW3-specific EPDC output interface with validated refresh commands, safe dirty-region updates and a fallback to the stock UI. Never treat generic SDL/FB writes as sufficient refresh.
4. Translate actual Cypress touch events to libnsfb pointer/keyboard events, integrate on-screen keyboard, toolbar/back/forward/scroll and prove return-to-home input lifecycle.
5. Verify HTTPS CA roots, TLS, time, Wi-Fi and download safety; bound memory and cache usage. NetSurf lacks full modern browser JavaScript compatibility.
6. Complete unattended boot/fallback evidence before publishing a user-facing browser option.

**No device writes, firmware updates, or Kindle display access were performed for this milestone.** Preserve the original upstream MIT code attribution and NetSurf's GPL-2.0-or-later obligations; distributing a full browser image entails source/licence compliance.

The upstream six footer phrases have been replaced with the user's **five local wisdom verses**. The Codex home build rotates them by local calendar day, uses `text_wrap` for long verses, and does not perform any network request. The rebuilt `home` executable is included in the small live-app overlay for attended deployment.

## Sources

- [Project plan](NETSURF-EINK-BROWSER-PLAN.md)
- [Alpine NetSurf package recipe](https://github.com/alpinelinux/aports/blob/master/community/netsurf/APKBUILD)
- [NetSurf framebuffer guide](https://github.com/netsurf-browser/netsurf/blob/master/docs/building-Framebuffer.md)
- [NetSurf framebuffer usage](https://github.com/netsurf-browser/netsurf/blob/master/docs/using-framebuffer.md)

## Read-only framebuffer evidence helper

`codex-display-probe` is compiled for the ARM target and staged in the Alpine image and small overlay. It has a no-device `--selftest`, and only an explicitly invoked `--read-only /dev/fb0` path (O_RDONLY and framebuffer GET VSCREENINFO/FSCREENINFO queries) for a later attended session. It never maps, writes, triggers refresh, or opens touchscreen input. A successful query is **not** EPDC compatibility proof. 
