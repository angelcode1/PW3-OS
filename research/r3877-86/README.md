# R3877.86 — KOReader Event module single-process probe

**Status:** R3877.85 physical FFI PASS recorded. R3877.86 packaged and host-only 18/18 synthetic PASS; **no R3877.86 Kindle execution has been reported.** `NOT_BOOTABLE` remains in force.

The first bounded genuine KOReader module candidate is `frontend/ui/event.lua`, from official KOReader tag `v2026.07.2`, 858 bytes, Git blob `3e042eb2a017e2a4e6fd27a6e4c1c7d2e388bd14` (verified from the upstream repository). Its sole responsibility is creation of event objects and it has no external `require` imports. The host preflight requires the existing R13-stage file at `opt/koreader-compat/app/frontend/ui/event.lua` to match that exact blob, or it refuses before any SSH. Source: https://github.com/koreader/koreader/blob/v2026.07.2/frontend/ui/event.lua

The downloadable **conversation artifact** `pw3-r3877-86-koreader-event-module.zip` contains the complete standalone Python driver, test suite, pinned original R81/R82/R83 ELF validators, the sanitized R85 PASS, README and checksums. Its host suite passed 18 tests; the ZIP contains no private KOReader ELF payload. The new source archive is delivered in this conversation, **not yet committed as individual source files**. Do not claim CI verification of the new archive. Never commit proprietary stage contents.

R3877.86 first runs `--review-only` on macOS, with no device connection. Upon user-approved explicit live execution it transfers the proven glibc/LuaJIT bundle and exact pinned event.lua to existing executable RAM tmpfs, validates SHA-256 on device, enforces the existing relocated loader `--list` mapping and RPATH checks, loads `require('event')` with a private Lua package.path, constructs an Event and exits. No KOReader GUI, framebuffer/input/power, mounts, chroot, firmware write, boot hook or persistent install. Cleanup after failure is unverified. A pass proves only this single module, not the full runtime.

Next: obtain the R3877.86 **offline** JSON. If the local stage diverged from the pinned upstream Event source, investigate rather than replacing a staged file. Independent boot and restore remain unverified.
