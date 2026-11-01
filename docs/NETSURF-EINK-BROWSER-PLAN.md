# Optional NetSurf browser — offline proof before PW3 e-ink backend

**Status:** Design/research only. No NetSurf binary built, no browser ARM/QEMU success, no physical Kindle framebuffer/input operation, and no permission to install/boot. Core PW3-OS remains KOReader + Ink Away. The current application gate is R24.2 ARM pending, followed by R25.2 only after a verified R24.2 pass.

## Choice

Prefer **NetSurf's existing framebuffer frontend** and `libnsfb` over a Chromium/WebKit port for the resource-constrained PW3. The NetSurf upstream [framebuffer guide](https://github.com/netsurf-browser/netsurf/blob/master/docs/building-Framebuffer.md) documents `make TARGET=framebuffer`, native pixel surfaces, FreeType and input abstraction; the [quick start](https://github.com/netsurf-browser/netsurf/blob/master/docs/quick-start.md) documents cross compilation. Implement a new e-ink adapter at the *display/input interface*, not a browser engine rewrite.

Use NetSurf as a **separate process**, not in KOReader's LuaJIT process. Offer a launcher/exit-return path after native KOReader UI lifecycle is verified. Preserve a fallback lightweight text/links browser (for example, a reviewed portable component from Inkwell if present and appropriately licensed).

Existing precedent: [InkSurf](https://github.com/pihokkerr/InkSurf), a NetSurf + KOReader e-ink plugin for **newer MTK/hwtcon_v2 Kindles**, already implements touch toolbar, keyboard integration and page browsing. Study architecture/code/licences; **its MTK display backend must not be treated as PW3 EPDC-compatible**.

## Progressive offline milestones

1. **Pinned build/provenance:** acquire pinned NetSurf and complete `libnsfb`, HTML/CSS/DOM, image, font, TLS and `libcurl` dependencies; verify GPL/source obligations. Cross-build separately against pinned **Alpine ARMv7/musl** sysroot (do not silently mix with KOReader's isolated glibc/soft-float-compatible runtime). Verify ELF ABI, PT_INTERP, transitive `NEEDED`, TLS certificates and old Linux 3.0.35 syscall compatibility. A successful Alpine desktop package does not establish availability of a compatible ARMv7 framebuffer APK.
2. **Offscreen-only baseline:** run `nsfb` using a memory surface in ARM/QEMU, render local static HTML/CSS, links, fonts, images, forms; capture bitmaps, dirty regions and memory high-water. No framebuffer device, network or physical input.
3. **E-ink compositing model:** output a 1072×1448 memory surface; quantize RGB to grayscale (correct gamma, dither and contrast), coalesce dirty rectangles, rate-limit incremental/partial refresh, and schedule full refreshes to limit ghosting. Validate using simulated frame sequences; **no actual EPDC ioctl/refresh** until explicitly authorized after adapter evidence.
4. **Input:** translate synthetic Cypress-style coordinate/touch phases into NetSurf pointer events; map power/keys and on-screen keyboard, long press to context/navigation, tap-to-follow, and e-ink-focused page-at-a-time scroll. Introduce a high-contrast touch toolbar.
5. **Network later:** a separately bounded, isolated host-network test for HTTPS/TLS, certificate validation, redirects, downloads and forms after offline rendering passes. In the current no-network Docker gate do **not** enable network. Check clock/CA state and robust cancellation.
6. **Memory and regression:** measure idle/load/large-page memory, repeated navigation and image-heavy pages, cache boundedness, no leaks, input responsiveness, CPU use and failure recovery. Keep simple/reader-mode pages as primary test cases; NetSurf JavaScript/modern-site coverage is limited and should not be represented as Chromium-equivalent.
7. **Dependency manifest:** capture all required shared libraries, fonts, CA roots and runtime files for the minimal Alpine rootfs allowlist. Retain a text-based fallback and expose the browser as an optional module removable without impacting KOReader.

## Hard boundaries

- `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.
- Neither an existing NetSurf Kindle plugin nor a reference implementation authorizes physical PW3 display calls.
- No moving or deleting files from stock firmware. Review each future build artifact for proprietary blobs/credentials before publishing.
- Browser is **separate from R24/R25 validation** and must not weaken its Ink Away-only plugin discovery tests. The optional browser can be staged later behind a separate test profile.

## References

- https://github.com/netsurf-browser/netsurf/blob/master/docs/building-Framebuffer.md
- https://github.com/netsurf-browser/netsurf/blob/master/docs/quick-start.md
- https://www.netsurf-browser.org/webmasters/
- https://github.com/pihokkerr/InkSurf
- https://pkgs.alpinelinux.org/packages?branch=v3.23&name=netsurf-framebuffer
