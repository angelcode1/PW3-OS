# PW3-OS R3877.91.5 — host-only relocation scope evidence

**Status:** `HOST_RELOCATION_SCOPE_MODEL_COMPLETE` (user-reported Mac run, exit 0). **Immutable hold: `NOT_BOOTABLE`.** This research note records evidence; it does not enable or authorize booting, installation, Kindle hardware access, device GUI/display/input/power operation, firmware writes, or mounts.

## Provenance

- R3877.90.4 physical Kindle native non-GUI batch: user reported 12/12 case passes, SSH exit 0, all six phases through `CLEANUP_OK`. Later read-only inventory: SSH exit 0, one tmpfs scanned, zero matching R90 temporary directories. Independent full restoration remains unverified.
- R3877.91 host-only Lua audit: all ten designated KOReader entry/app files present; 823 Lua files; 371 statically reachable under literal require scanning. This is not a complete runtime graph.
- R3877.91.1: 76 parsed ARM ELF objects, 196 DT_NEEDED edges, zero absent *filename/SONAME* candidate names (not actual loader resolution).
- R3877.91.2: within modeled GNU boundary, 64 ELF objects and 181 dependencies, zero absent candidates or opposite-float candidates. Duplicate `libstdc++.so.6` providers need search-order analysis.
- R3877.91.3: the model selected `app/libs/libstdc++.so.6` for seven consumers; checked required version names all appeared; native Lua module *candidates* found at `common/lpeg.so`, `common/mime/mcore.so`, `common/socket/score.so`.
- R3877.91.4: 320 selected C++ versioned imports statically satisfiable, 3/3 `luaopen_*` entry points exported; 64 GNU-side objects had no explicit `Tag_ABI_VFP_args`, 12 Alpine-side objects had value 1. No actual ABI binding claimed.
- R3877.91.5: user-reported report described below. All staged executables and libraries remained inert for this host-only phase.

## R3877.91.5 recorded result

| Field | Value |
|---|---:|
| GNU-boundary objects | 64 |
| `DT_NEEDED` edges modeled | 181 |
| Relocation records inspected | 68,516 |
| Unique relocated symbol imports counted per object | 5,114 |
| `MODEL_DIRECT_DEP_MATCH` | 1,107 |
| `MODEL_MATCH` | 3,266 |
| `NOT_IN_DIRECT_NEEDED_SCOPE` | 412 |
| `WEAK_OPTIONAL_IMPORT` | 329 |
| Objects without relocation sections | 0 |
| Parser errors | 0 |
| R915 local process exit | 0 |

The report includes **60** examples out of 412 `NOT_IN_DIRECT_NEEDED_SCOPE` occurrences, with **352 not shown**. All 60 shown are Lua C API names (`lua_*`, `luaL_*`), largely from `lpeg.so` and `libopenlipclua.so`. These can resolve from the LuaJIT executable's exported/global symbols without a direct `DT_NEEDED` edge. **Do not treat 412 as a count of missing native symbols.** The other 352 require additional classification; the current report does not prove their identity.

## Next bounded checks

1. Audit exported LuaJIT executable symbols against the 60 named examples and remaining 352 (obtain a complete host-only diagnostic before claiming closure).
2. Model executable/global and inherited object scopes, GNU loader launch arguments and RPATH inhibition. Symbol scopes, lazy binding, PLT/GOT relocations, loaded SONAMEs, `dlopen`, FFI, interposition and runtime conditions remain unverified.
3. Audit genuine missing names, weak bindings, resources, platform-specific initialization and real device side effects separately. Avoid executing `reader.lua`, `device:init()`, GUI, or loading new libraries on Kindle without a separately reviewed plan.
4. Independently validate recovery, stage identity, hardware/display/input/power safety before reconsidering bootability.

## Source and reproduction

Original source distribution: `pw3-r3877-91-5-relocation-scope-audit.zip`, SHA-256 `c912c455b759056c00087c06bec9412bbc2024a7c9defb3b5852555f25de3445`. The ZIP contains the R91.1–R91.5 host-only audit scripts, their five test modules, README and checksums. The archive was verified in the ChatGPT working environment: its internal checksum manifest passed and **43 synthetic tests passed**. The full auditor source ZIP remains a separate downloadable conversation artifact; **it is not included in this Git commit**. The individual file hashes are recorded in `SOURCE_MANIFEST.sha256`.

This Git branch includes a *report-shape* verifier and tests to make the research evidence reviewable. That small verifier is not a substitute for the R91.5 ELF analyzer. Given the user's source is on their Mac and no verified automated source transfer into the GitHub connector is available, never represent this branch as a complete runnable R91.5 source tree.

Example (host-only, against user's saved report):

```sh
python3 research/r3877-91-5/verify_report.py r3877_91_5_host.json
python3 -m unittest -q research/r3877-91-5/test_verify_report.py
```

No proprietary Kindle firmware, stage ELF objects, private SSH data, IP addresses, keys or user-specific paths are committed. **`NOT_BOOTABLE` persists.**
