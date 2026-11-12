# Codex NetSurf → PW3 one-shot e-ink preview

Status: TEST BUILD. This does not add a live interactive browser or Home tile.

## Test architecture

1. ARMv7 NetSurf renders a local HTML/CSS page in SDL/Xvfb, and GitHub Actions validates its screenshot pixels.
2. The screenshot is converted to a fixed 1072 × 1448 8-bit grayscale P5 PGM. It is letterboxed rather than cropped.
3. The standalone ARMv7 tool **codex-browser-panel-preview** can inspect this file without device writes, self-test framebuffer stride/restore in RAM, or show it briefly on an actual PW3 when explicitly permitted.

The display tool inherits the pinned upstream Home's **72-byte Kindle EPDC update ABI** and ioctl number 0x4048462E. It enforces PW3 1072 × 1448, 8bpp, unrotated framebuffer geometry before attempting any hardware change. It snapshots the existing screen bytes, sends a GC16 full refresh, holds the screenshot for five seconds, restores the previous pixels and requests a second full refresh.

Neither tool calls NetSurf's live libnsfb framebuffer backend. This is a deliberately reversible intermediate test, not proof that tapping, navigation, scroll, HTTPS or the keyboard work on the Kindle.

## CI assets

The Codex NetSurf offscreen workflow should produce the artifact **codex-netsurf-armv7-offscreen-visual**. It contains baseline.png, netsurf-sdl.png, codex-browser-pw3-preview.pgm, and log files. Its host job compiles the PW3 preview tool and exercises RAM-only selftests and the refusal to display without the explicit hardware gate.

The separate full Alpine build publishes codex-browser-panel-preview in the **pw3os-apps-overlay** artifact, without requiring a new OS installation.

## Optional attended test — existing Alpine on a confirmed PW3 only

Do not run on stock Kindle OS or while another app is refreshing the screen. This test changes the visible screen temporarily. Require a confirmed framebuffer preflight before enabling it.

Download the two CI artifacts, extract locally, transfer **codex-browser-panel-preview**, **codex-display-probe**, and **codex-browser-pw3-preview.pgm** to a private temporary directory on the existing Alpine system. Do not overwrite the installed Home or boot image.

First, from that directory:

    chmod +x ./codex-browser-panel-preview ./codex-display-probe
    ./codex-browser-panel-preview --selftest
    ./codex-browser-panel-preview --inspect codex-browser-pw3-preview.pgm
    ./codex-display-probe --read-only /dev/fb0

Only if the read-only probe confirms 1072 × 1448, bpp=8, rotation=0, the selftest/PGM inspection succeed, and the operator chooses to test the panel, run the following in an INTERACTIVE SSH terminal:

    CODEX_BROWSER_PANEL_TRIAL=EXPLICIT ./codex-browser-panel-preview --display-once codex-browser-pw3-preview.pgm --confirm-pw3

The screenshot should appear for about five seconds and the previous screen should return. Record orientation, legibility, ghosting and refresh behaviour. On successful completion it prints CODEX_PW3_BROWSER_SCREEN_RESTORED.

**Limitations:** Restore is best-effort, not a crash-proof watchdog. SIGKILL, power loss or an EPDC ioctl failure can leave the screen showing the test image even if pixel memory was restored. If that happens, STOP testing and use only the known-good Home/KOReader refresh or established rollback method; do not loop refresh commands blindly.

## Next milestone

After a successful on-device preview, connect NetSurf's actual libnsfb surface to the grayscale compositor and PW3 refresh adapter, then connect Cypress touch input and on-screen keyboard with a reliable exit-to-Home lifecycle. Browser menu exposure and further games integration are gated on those tests. Keep NetSurf GPL and upstream MIT attributions.
