# PW3-OS R3877.88.1 — targeted KOReader source provenance (host only)

**Status: Mac-only regression package ready; real user-stage result PENDING. NOT_BOOTABLE.** No SSH, device execution, OS/boot modifications or stage writes.

R3877.88 reported **7/8** exact v2026.07.2 KOReader module pins matching. Staged `ui/geometry.lua` is 10,735 bytes while upstream is 10,734 bytes (Git blob SHA-1 `dc8362ae455d3fddce2513865d340b482a9bdc53`). A one-byte *length* difference is not proof that exactly one byte was inserted.

The root tag's `base` submodule is pinned at [KOReader-base 6e4bc81](https://github.com/koreader/koreader-base/tree/6e4bc81af4e04f78d81677a323a780a71b29702a). Its [`ffi/serpent.lua`](https://github.com/koreader/koreader-base/blob/6e4bc81af4e04f78d81677a323a780a71b29702a/ffi/serpent.lua) is 8,979 bytes, Git blob `812668de60aefeedfad1cbfca211a877a7dcaea0`. The local candidate `opt/koreader-compat/app/ffi/serpent.lua` must be checked against that exact pin before attempting WidgetContainer.

The companion package `pw3-r3877-88-1-provenance-audit.zip` (provided in the conversation) contains read-only source, 18 passing synthetic host tests, the exact unchanged previous R3877.88 source, a checksum manifest, a sanitized R88 report and full Mac commands. ZIP SHA256: `261144a23888e52c672fe5975314fde319cf99f3b3e5ed2d08b2467ddb7ac83e`.

The new tool tries every single-byte omission **in memory**, checking if the resulting blob equals the precise upstream Git SHA-1, while leaving the stage byte-for-byte unchanged. Its public JSON describes position(s) and character class, not source excerpts. It hashes the local Serpent candidate against the base submodule pin. Never automatically delete an extra newline or substitute upstream source in the original stage.

Even if one-byte drift is explained and Serpent matches, the source pin hold remains active until reviewed; the older R26 stage count mismatch, full dynamic closure, GUI/e-ink, recovery and boot stay unverified.

**No native Kindle test has been authorized or run for this milestone.** The runnable source is distributed in the tested ZIP; this research record intentionally contains no proprietary stages or runtime binary payloads.
