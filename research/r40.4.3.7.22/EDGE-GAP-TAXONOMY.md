# R40.4.3.7.22 — complementary ELF/Lua static reference gap taxonomy

This is a **separate read-only analysis** alongside the existing R3722 ELF symlink/interpreter candidate audit, not a replacement. User Mac run pending; **NOT_BOOTABLE**.

Package: `pw3-os-r40.4.3.7.22-edge-gap-taxonomy-readonly.zip` SHA-256 `d8292bb50e2cba1d30436c672ceac32d0df243deaf7901a0da01bd16efa817eb` (7,352 bytes, four members), source `R4043722-EDGE-GAP-TAXONOMY-READONLY.py` SHA-256 `058bdb086437f038a8ad3dbe3c585a3367977454df8187295cbb158f7e0c4417`. Clean extraction 26/26 stdlib tests PASS, per-file manifest PASS, ZIP CRC PASS.

Pins original R3721.1 source SHA `c7a987b16ccfe119a0fac5388d20c28a4050bcd7bff5f4dad7d0b457a3c864b4` and inherits exact R3720 trace replay and R26 rehash. Requires parent 492 observed regular staged files, 29 ELF observed, 379 Lua observed, 209 ELF DT_NEEDED edges and 6306 Lua lexical edges to match original exact counts. Splits 14/188/7 ELF no/single/multiple static name-candidate edges by observed source ELF and observed target; splits 4589/1256/461 Lua lexical no/single/multiple edges by observed source Lua, `require`/`dofile`/`loadfile`/`ffi.load`, and target observation. Any mismatch HOLD. Only fixed-category aggregate stdout; no private paths or strings.

Static candidates are not verified runtime library loading, computed Lua resolution or FFI binding. Original R26 source provenance unauthenticated; 956 current-scenario not-observed staged regular files and separate 976 old UNKNOWN_HOLD remain protected. Historical 347-file union path overlap unproven. No stage modification, QEMU run, device access, deletion, boot, firmware action or pruning. **NOT_BOOTABLE**.
