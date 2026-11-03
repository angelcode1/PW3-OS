# PW3-OS R40.4.0 — local ELF/Lua static candidate graph

**2026-11-03. Host tested only. R40.4 ARM/QEMU NOT RUN. NOT_BOOTABLE.**

This source-only release is the first executable step of R40.4. It is a **read-only local analysis** of the same immutable R13/R26 staged rootfs whose hashes matched the original R26 manifest in R40.3. It does *not* replay the ARM guest, alter the kernel or firmware, install games, boot a new rootfs, build a binary, remove files, or open any device interface.

## Exact prerequisites / source pins

- R39.4.11 original synthetic two-PDF application PASS, R40.0.2 traced scenario PASS. No new guest evidence is claimed.
- R40.1 private absolute-path stage crosswalk and counts-only public summary, R40.2 private CWD crosswalk and public summary. Original R40.3 read-only verifier is bundled unchanged as `r403/union_inventory.py`, pinned SHA256 `7f750452a520807bca6dd6084bf410e226c7bcb8e9f5fb227c4ee8ed72c4900c`.
- Original local `R26-INVENTORY.json` and stage rootfs. The previous verified **R40.3 R26 SHA report** `R40.3-R26-HASH-SUMMARY.json` is source-pinned SHA256 `bf029bfffc7f64cd4c9d7d010acc7d7d267546ed0ee9c4ee94b379362ab38771`. A copy of the **counts-only** report is shipped under `tests/fixtures` solely for portable host regressions; no private filenames.
- Exact original R40.2 public/private SHA pins are checked by the unchanged R40.3 source. All 2,070 outer-stage records (1,448 regular, 287 directories, 335 symlinks) are rescanned and all 1,448 original regular SHA256 values reverified by R40.3 before the graph is built. No symlinks are followed.
- No third-party Python modules are required. Python 3.9+ stdlib. No `ldd`, ELF execution, network access, hardware access or stage mutation.

## What the analyzer actually collects

1. Locally reconstruct exactly **347 distinct regular staged files observed opened** from the original verified R40.1 and R40.2 private crosswalks. Preserve 1,101 unobserved regular files as `UNKNOWN_HOLD`, not a removal list.
2. Parse ELF32/ELF64 program headers *from bytes*, including `PT_INTERP`, `PT_DYNAMIC`, `DT_NEEDED`, `DT_SONAME`, `RPATH`, `RUNPATH` and recorded ARM hard/soft-float **flags**. Build candidate library name matches across the **entire existing staged tree**, including unresolved/ambiguous names and symlink holds. The ELF program-header parser is source-only and bounded; malformed/oversize objects are recorded as **parse holds**.
3. Scan UTF-8-decoded `.lua` regular files for **approximate literal** `require`, `dofile`, `loadfile` references, then list filename-suffix candidates locally. This is a lexical approximation, not a full Lua parser, runtime `package.path` resolver, proof of actual module loads, or proof of absence of indirect/dynamic `require`/FFI loads.
4. Emit `R40.4.0-PRIVATE-STATIC-GRAPH.json` containing local filenames, ELF/Lua references, candidates and evidence classifications (**PRIVATE, do not share**). Emit `R40.4.0-SUMMARY.json` containing only aggregate counts, source-pin hashes, scenario status, digest of the private output and strict immutable holds (**shareable**).
5. The optional Inkwell-inspired puzzle pack remains `FUTURE_OPTIONAL_NOT_BUILT_NOT_TESTED_HOLD`, separate from KOReader/Ink Away core dependency closure. No puzzle engine, code, dictionary or licensed asset is imported. The bundled scenario matrix explicitly holds five new traces, including puzzles.

**Critical limits:** A static basename or suffix candidate is not the runtime loader's actual resolution. This tool cannot detect every computed Lua load, `dlopen`, transitive resource, firmware request, kernel/EPDC dependency, font fallback, hardware startup or boot dependency. It is not an exhaustive transitive closure and not permission to trim the existing R13 stage. It complements—not replaces—the original R26 inventory and R40.0.2 trace.

## Step 1 — unzip into a new directory and check source integrity

```sh
cd "$HOME/Downloads"
SRC="$HOME/Downloads/pw3-os-r40.4.0-static-dependency-graph"
mkdir -p "$SRC"
unzip -q pw3-os-r40.4.0-static-dependency-graph.zip -d "$SRC"
cd "$SRC"
shasum -a 256 -c SHA256SUMS-R4040
python3 -m unittest discover -s tests -q
```

Expected host suite: `Ran 62 tests ... OK`. This is host verification, **not an ARM/QEMU pass**.

## Step 2 — analyze the original stage without modifying it

The tool can be run from any working directory because the script locates its vendored pinned verifier automatically.

```sh
python3 "$HOME/Downloads/pw3-os-r40.4.0-static-dependency-graph/r404/static_graph.py" \
  --stage "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --r26-inventory "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-INVENTORY.json" \
  --r401-private "$HOME/Downloads/R40.1-PRIVATE-CROSSWALK.json" \
  --r401-summary "$HOME/Downloads/R40.1-SUMMARY.json" \
  --r402-private "$HOME/Downloads/R40.2-PRIVATE-CWD-CROSSWALK.json" \
  --r402-summary "$HOME/Downloads/R40.2-SUMMARY.json" \
  --r403-hash-summary "$HOME/Downloads/R40.3-R26-HASH-SUMMARY.json" \
  --private-out "$HOME/Downloads/R40.4.0-PRIVATE-STATIC-GRAPH.json" \
  --summary-out "$HOME/Downloads/R40.4.0-SUMMARY.json"

cat "$HOME/Downloads/R40.4.0-SUMMARY.json"
```

The two output files must be **new** and outside the staged tree, with existing non-symlink parent directories. The analyzer **refuses overwrite**, symlinked inputs, stage/source pin drift, different source/trace stage roots, mismatched old R26 content and unexpected entry counts. On any refusal, keep the previous evidence and do not circumvent the hold or prune the stage.

### What to share

Upload only **`R40.4.0-SUMMARY.json`**. Keep `R40.4.0-PRIVATE-STATIC-GRAPH.json`, R26 raw inventory, private R40.1/2 crosswalks and QEMU path-level logs local. The summary's SHA-256 of the private output may be used later for non-disclosing consistency verification; it does not authenticate firmware provenance.

## Scenario coverage

See `SCENARIO-MATRIX-R4040.json`. It distinguishes the **previously verified** double-PDF runtime trace from *not-yet-run* FileManager-only, Ink Away, EPUB/text, fallback and future puzzle scenarios. A static graph does not earn any additional ARM scenario PASS.

**Safety (unchanged):** `NO_DEVICE_ACCESS`, `NO_FIRMWARE_WRITES`, `NO_HARDWARE_ACTIONS`, `NO_BOOT`, `NO_PRUNING`, `NOT_BOOTABLE`. All 1,101 unobserved staged regular files and 976 older `UNKNOWN_HOLD` entries remain preserved; these categories refer to different evidence sets and are not added together. Research and educational purposes only.

## User's local R40.4.0 source execution (2026-11-03)

The user reported `Ran 62 tests in 0.022s — OK`, then executed the unchanged source-bound R40.4.0 graph on the original R13 rootfs. Public verdict: `R40_4_0_STATIC_CANDIDATE_GRAPH_OBSERVED_NOT_CLOSED`. R26 **2,070** entries rehashed, comprising **1,448 regular files, 287 directories and 335 symlinks**. ELF: **83** found and parsed, **0** parse/size holds, **26** opened in the earlier synthetic runtime trace; **209** DT_NEEDED edges plus 98 ambiguous name candidates, 111 single candidate edges not runtime proven, 12 interpreter absent at expected stage path and 7 interpreter stage regular not runtime-proven. Lua: **823 files scanned**, **272** previously observed opened, **6,272** literal reference edges with 1,705 candidate-only, 270 no staged lexical candidates and 4,297 unresolved/nonmodule holds. R39.4.11 ARM PASS and R40.0.2 traced PDF PASS are historical controls, **not** new R40.4.0 ARM evidence. No new FileManager-only, Ink Away canvas, EPUB/text, resource fallback or puzzle scenario has been executed under R40.4.

The user kept the complete static graph private. These **static candidates do not establish actual loader resolutions** and do not change the 347 observed runtime regular opens or the protected 1,101 unobserved regular files. The R26 source inventory is locally content-matched but still `r26_provenance_authenticated=false`. New standalone FileManager-only trial source is prepared separately as [R40.4.1](../r40.4.1/README.md).
