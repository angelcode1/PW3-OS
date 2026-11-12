# Codex NetSurf → PW3 one-shot e-ink preview

Status: TEST BUILD. This does not add a live interactive browser or Home tile.

## Test architecture

1. ARMv7 NetSurf renders a local HTML/CSS page in SDL/Xvfb, and GitHub Actions validates its screenshot pixels.
2. The screenshot is converted to a fixed 1072 × 1448 8-bit grayscale P5 PGM. It is letterboxed rather than cropped.
3. The standalone ARMv7 tool **codex-browser-panel-preview** can inspect this file without device writes, self-test framebuffer stride/restore in RAM, or show it briefly on an actual PW3 when explicitly permitted.

The display tool inherits the pinned upstream Home's **72-byte Kindle EPDC update ABI** and ioctl number 0x4048462E. It enforces the physical PW3's observed 1072 × 1448, 8bpp grayscale, stride >= 1072, hardware rotate=3 (FB_ROTATE_CCW), zero visible offsets, packed/static-pseudocolor mode, and bounded framebuffer size before attempting any hardware change. No software rotation or FBIOPUT_VSCREENINFO occurs; the driver reports portrait xres/yres with rotate=3. Other rotation values fail closed. This configuration is based on real PW3 read-only diagnostics and matching KOReader Kindle framebuffer handling; physical panel output remains unverified. It snapshots the existing screen bytes, sends a GC16 full refresh, holds the screenshot for five seconds, restores the previous pixels and requests a second full refresh.

Neither tool calls NetSurf's live libnsfb framebuffer backend. This is a deliberately reversible intermediate test, not proof that tapping, navigation, scroll, HTTPS or the keyboard work on the Kindle.

## CI assets

The Codex NetSurf offscreen workflow should produce the artifact **codex-netsurf-armv7-offscreen-visual**. It contains baseline.png, netsurf-sdl.png, codex-browser-pw3-preview.pgm, and log files. Its host job compiles the PW3 preview tool and exercises RAM-only selftests and the refusal to display without the explicit hardware gate.

The separate full Alpine build publishes codex-browser-panel-preview in the **pw3os-apps-overlay** artifact, without requiring a new OS installation.

## New: true headless NetSurf rendering path (no X server)

NetSurf's Alpine framebuffer binary embeds libnsfb, so no external
`libnsfb-dev` package exists. The tested alternative intercepts its
**dynamically linked SDL 1.2 framebuffer** using
`build/pw3os/codex-sdl-live-capture.c`. It captures the browser's actual
`SDL_Surface`, then validates local HTML/CSS pixels and converts the
result into a PW3 grayscale image.

The ARMv7 test has already confirmed direct SDL capture under Xvfb.
A further CI test renders through `SDL_VIDEODRIVER=dummy` without X11;
read `.github/workflows/codex-netsurf-offscreen.yml` for its exact status.
The current full-image builder stages the dynamically linked ARMv7
`/usr/local/lib/codex/libcodex-sdl-capture.so` and its Python validator
alongside `/usr/local/bin/codex-browser`. They are **not** started at boot.

An *attended* headless dry run on existing Alpine, after successful build
and runtime compatibility checks, uses:

```sh
CODEX_BROWSER_ATTENDED=EXPLICIT codex-browser --capture-offscreen
```

Run from an interactive terminal (for SSH, request a TTY). It uses only
the local HTML fixture and the SDL dummy driver, then exits after a
bounded duration. The output is
`/run/codex-browser/codex-browser-live-pw3.pgm`. It does **not** alter
the Kindle screen or open evdev. This is the next meaningful on-device
compatibility gate, not an interactive browser.

## Optional attended test — existing Alpine on a confirmed PW3 only

Do not run on stock Kindle OS or while another app is refreshing the screen. This test changes the visible screen temporarily. Require a confirmed framebuffer preflight before enabling it.

Download the two CI artifacts, extract locally, transfer **codex-browser-panel-preview**, **codex-display-probe**, **codex-browser-touch-probe**, and **codex-browser-pw3-preview.pgm** to a private temporary directory on the existing Alpine system. Do not overwrite the installed Home or boot image.

First, from that directory:

    chmod +x ./codex-browser-panel-preview ./codex-display-probe
    ./codex-browser-panel-preview --selftest
    ./codex-browser-panel-preview --inspect codex-browser-pw3-preview.pgm
    ./codex-display-probe --read-only /dev/fb0

Only if the read-only probe confirms 1072 × 1448, bpp=8, grayscale=1, rotation=3, stride=1088, x/yoffset=0, the selftest/PGM inspection succeed, the screen is awake and no other app is actively refreshing, and the operator chooses to test the panel, run the following in an INTERACTIVE SSH terminal:

    CODEX_BROWSER_PANEL_TRIAL=EXPLICIT ./codex-browser-panel-preview --display-once codex-browser-pw3-preview.pgm --confirm-pw3

A first physical test reported `PW3 EPDC WAIT_FOR_UPDATE_COMPLETE: No error information` twice and visibly blinked. It proved only that SEND_UPDATE was accepted, not a verified preview or restoration. This came from treating nonzero ioctl returns as failure, even though WAIT can return a **positive number indicating successful completion** (remaining timeout jiffies). The corrected tool uses `rc < 0` for both SEND and WAIT and logs `CODEX_PW3_EPDC_UPDATE_COMPLETE` with raw return codes; any negative rc remains a hard failure and triggers a best-effort pixel restore. Do not classify positive rc as an error or skip the five-second hold. The next attended trial must explicitly confirm visible upright image and a restored Codex Home screen.

The screenshot should appear for about five seconds and the previous screen should return. Press the Kindle power button briefly to wake before the trial; do not try while it is actively asleep or while another application is drawing. The preview maps the already-portrait 1072x1448 PGM directly into visible 1088-byte-stride rows; `rotate=3` is checked but not modified. If it displays sideways, do not try flipping the image blindly. Record orientation, legibility, ghosting and refresh behaviour. On successful completion it prints CODEX_PW3_BROWSER_SCREEN_RESTORED.

**Limitations:** Restore is best-effort, not a crash-proof watchdog. SIGKILL, power loss or an EPDC ioctl failure can leave the screen showing the test image even if pixel memory was restored. If that happens, STOP testing and use only the known-good Home/KOReader refresh or established rollback method; do not loop refresh commands blindly.

## Read-only touch capability test

The separate ARMv7 `codex-browser-touch-probe` executable is also included
in the app overlay. Its default `--read-only` probe enumerates event0..15,
identifies a device with ABS_MT X/Y and tracking-id capabilities, and prints
actual axis ranges. It uses only O_RDONLY and ioctl GET queries; never
EVIOCGRAB, event injection, framebuffer writes, or system configuration.

    ./codex-browser-touch-probe --selftest
    ./codex-browser-touch-probe --read-only

For an **attended** eight-second touch-only sample, use a true SSH terminal:

    CODEX_BROWSER_TOUCH_TRIAL=EXPLICIT ./codex-browser-touch-probe --sample-seconds 8

It prints normalized pointer DOWN/MOVE/UP positions for later comparison
with live NetSurf. This is observational only: it neither controls the
browser nor takes exclusive touch ownership. Do not claim touchscreen
integration until actual input evidence and a connected libnsfb surface pass.

## Next milestone

After a successful on-device preview, connect NetSurf's actual libnsfb surface to the grayscale compositor and PW3 refresh adapter, then connect Cypress touch input and on-screen keyboard with a reliable exit-to-Home lifecycle. Browser menu exposure and further games integration are gated on those tests. Keep NetSurf GPL and upstream MIT attributions.

## Experimental 30-second live SDL-to-e-ink + touch bridge

The bounded live test is now compiled and distributed as an *optional small
app overlay*, with no change to boot hooks, image checksums or the Home menu.
It is **not** yet verified as a live interactive browser on the physical PW3.
The offscreen NetSurf renderer, one-shot panel refresh/restore, Cypress
read-only movement and host-side coordinate/event ABI tests have passed.

- \`codex-browser-live-trial\` requires \`CODEX_BROWSER_LIVE_TRIAL=EXPLICIT\`,
  exactly \`--run\`, and a true interactive TTY. It explicitly opens only
  \`file:///usr/share/codex/browser-smoke.html\`, not remote URLs.
- The standard verified \`libcodex-sdl-capture.so\` atomically exports live
  SDL BMP frames to private RAM. \`codex-browser-live-frames.py\` validates
  each 600x800 BMP and atomically publishes 1072x1448 PGM frames.
- \`codex-browser-panel-preview --follow-pgm ... --confirm-pw3\` is the
  sole framebuffer owner in this trial. It snapshots visible pixels,
  accepts exactly the previously measured PW3 geometry and EPDC ABI,
  refreshes at most every 1.8s using GC16, stops after 30 seconds and
  attempts a full restore. No \`FBIOPUT_VSCREENINFO\` is used.
- \`libcodex-sdl-touch-input.so\` is an optional LD_PRELOAD hook on SDL 1.2
  \`SDL_PollEvent\` and \`SDL_WaitEvent\`. It opens read-only Cypress
  \`/dev/input/event1\`, ignores other slots, injects tap as SDL left-click,
  and swipe as SDL wheel events. It does **not** grab or reconfigure evdev.
  Its mouse ABI, coordinates and viewport mapping are host-tested, but
  physical browser interaction still requires attended validation.
- The launcher temporarily stops the Home process to avoid competing
  panel updates, then resumes and terminates that process on exit; the
  existing init supervisor restarts Home and redraws the front page.
- This is intentionally not an unattended daemon, a public browsing
  implementation, an onscreen keyboard or a Home tile. The physical
  e-ink panel may be slow, ghost, or fail to restore on power loss.

The output of the first trial should record \`CODEX_BROWSER_LIVE_FRAME_DISPLAYED\`,
\`CODEX_BROWSER_SDL_POLL_HOOK_ACTIVE\`, \`CODEX_BROWSER_SDL_TAP\` /
\`CODEX_BROWSER_SDL_SCROLL\`, \`CODEX_BROWSER_LIVE_SCREEN_RESTORED\`,
and an awake Codex Home screen. If the presenter reports a negative EPDC
ioctl or the screen does not restore, stop; do not repeat blindly.
