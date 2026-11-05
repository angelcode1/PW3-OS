# R40.4.3.7.46 — weak PLT original-word executable-section geometry

**Host-side, read-only research; `NOT_BOOTABLE`.** No rootfs changes, symlink creation, QEMU, ELF execution, firmware, boot or pruning.

## Evidence and motivation

The user ran R3745.2 against the unchanged R13 staged rootfs. Across twelve requesting ELF objects, all 18 targeted weak `R_ARM_JUMP_SLOT` relocation slots have nonzero original words whose low bit is clear and whose numeric values fall within the same ELF's executable `PT_LOAD` memory. All twelve requesters have a `DT_PLTGOT` value within a writable `PT_LOAD`. These are **static file values**, not proven pointers, PLT stubs, binding behavior or symbol resolution. There are 9 local-index-zero weak entries with a six-provider export name candidate, 7 local-index-zero weak PLT sites with no such name candidate, and 2 unversioned weak PLT sites with no name candidate. The user confirmed `NOT_BOOTABLE` and no staged writes.

## R3746 classification

The tool requires SHA-256 of the unchanged R3745.2 script `82ea5da0c3031b3310564b483936c74a5a661405730722558c30ac2b6f8413f1` and replays its exact 12-requester/6-provider/18-PLT-site baseline, inherited source hashes and historical R3745 parser HOLD. It reads only bounded ELF32 ARM headers, dynamic `DT_JMPREL` relocation records, file-backed slot words and ELF **section headers** via the pinned nofollow file-reading helper.

For each of the 18 unrelocated words, R3746 checks only:

- Whether the value's numeric address is within a unique allocated executable `SHT_PROGBITS` section and whether that section's **in-memory section name** is `.plt`, `.plt.sec`, `.iplt`, `.text`, another name or unavailable; ambiguous or missing section containment gets a review category rather than a guessed match.
- Whether the candidate numeric address is 4-byte aligned and the section-mapped 32-bit original word is zero/nonzero, or not uniquely file backed. **No instruction decoding, simulation, address rebasing or pointer proof.**
- Whether multiple targeted weak PLT sites share the same initial numeric word **within one requester and group**. Only aggregate counts leave the program; no original words, offsets, names, file paths or symbols are exported.

The ELF section names are *hints* and are not used by all loaders. A `.plt` match does not establish lazy PLT binding; a `.text` match does not imply execution there. The ELF word may be an addend or stub-specific value, **not an address**. Inherited unresolved weak-symbol semantics, ARM TLS relocation handling, real guest interpreter path, original R26 provenance, historical file hashes, kernel/runtime ABI, loader namespace/search/interposition and full transitive closure remain on hold. OpenSSH, SFTP and rsync remain deferred to a separate validated image.

## Test verification

Synthetic tests: **36 new R3746 cases plus 298 inherited tests = 334 tests**. Tests use temporary synthetic files, never the real staged rootfs. The archive SHA256 manifest is verified before the Mac-stage audit. **Host passing does not prove the actual stage or PW3 boot.**

## Run on macOS (no git or gh)

Download `pw3-r3746-plt-section-geometry-readonly.zip` into `~/Downloads`, then:

```sh
mkdir -p "$HOME/Downloads/pw3-r3746"
cd "$HOME/Downloads/pw3-r3746"
unzip -o "$HOME/Downloads/pw3-r3746-plt-section-geometry-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043746-PLT-EXEC-SECTION-PREFLIGHT-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send the resulting JSON, especially `weak_plt_candidate_section_categories_by_group`, `within_requester_candidate_reuse_categories`, `targeted_weak_plt_sites` and `requester_objects_with_targeted_weak_plt_sites`. If `HOLD`, preserve its `hold_category`; **do not alter the stage or pins to force a pass**. `NOT_BOOTABLE` regardless of the outcome.