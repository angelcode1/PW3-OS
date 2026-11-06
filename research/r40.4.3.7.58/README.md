# R40.4.3.7.58 — Original R26 inventory content re-verification (read-only)

**Research and educational use. Immutable `NOT_BOOTABLE`.** No stage writes, file replacement, alias/mapping, executable guest loader, firmware, pruning or boot.

## Reason

The R3757 Mac audit found `.ARM.attributes` file sections in the candidate loader and all 12 requesters. Every *jointly present* monitored tag matched. Three requesters omit `ABI_ALIGN_PRESERVED` and two omit `ABI_HARDFP_USE`; absence is **not** treated as compatibility. No more header equality can prove the guest loader works.

The older R26 inventory reported **2,070 stage entries: 1,448 regular files, 287 directories, and 335 symlinks**. Earlier R3719 research reported hash agreement with the user-supplied historical inventory, but the original R26 provenance was **not authenticated**, and later ELF audits did not replay the original private inventory's content hashes. This independently rechecks the current stage against **the locally retained R26 inventory file**, without uploading private paths or hashes.

## What R3758 does

- SHA-256 pins the unchanged R3757 program and replays its entire R3756 and older preflight chain, including historical R3745 HOLD and R3757's 12-requester/one-candidate ARM attribute baseline.
- Requires the original private `R26-INVENTORY.json` as a **separate input**; it never regenerates, edits or uploads that evidence.
- Requires an `entries[]` object schema with safe relative paths, file/directory/symlink types, SHA-256 for each regular file, literal target for each symlink and optional recorded permission modes. Unrecognized schemas, missing hashes, unsupported records or inconsistent duplicate fields produce HOLD; **the schema has not yet been confirmed against the user's actual private inventory**.
- Independently traverses the original stage using non-following directory-entry metadata. Requires exactly 2,070 matching paths and inode types; hashes all 1,448 original stage regular files using nofollow file-descriptor reads and before/after metadata checks; compares all 335 symlink targets and all 287 directory records, plus modes when present.
- Exports only numerical match counts and safety booleans; no private path names, file contents, hashes, link literals or inventory payload.

A full match means **`R26_HISTORICAL_STAGE_INVENTORY_MATCH_UNAUTHENTICATED`**, **not** a signed or otherwise authenticated R26 source chain, and not proof of kernel/loader compatibility, dependency closure or boot. A missing file or incompatible original inventory schema gives an explicit HOLD; do not fabricate an inventory or bypass its hash checks.

## Verification

The downloadable ZIP contains the entire unchanged 863-test predecessor lineage, the new source, 38 new synthetic tests, workflow, README, release status and SHA-256 manifest. Clean extraction, all manifest hashes and ZIP integrity were checked. Host synthetic checks: **38 new + 863 inherited = 901 tests PASS**. The real Mac stage audit has **not run**.

## Run on macOS, no `git` or `gh`

Download `pw3-r3758-r26-inventory-reverification-readonly.zip` into `~/Downloads`, then:

```sh
mkdir -p "$HOME/Downloads/pw3-r3758"
cd "$HOME/Downloads/pw3-r3758"
unzip -o "$HOME/Downloads/pw3-r3758-r26-inventory-reverification-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043758-R26-INVENTORY-REVERIFICATION-READONLY.py \
  --stage "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  --r26-inventory "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-INVENTORY.json" \
  --parent-dir "$PWD"
```

On `HOLD`, send its category. In particular, `R26_PRIVATE_EVIDENCE_MISSING_HOLD` means the historical R26 inventory is not at that path; `R26_EVIDENCE_*_SCHEMA_HOLD` means schema adaptation may be needed after a privacy-preserving local inspection. Never overwrite original R26 evidence or stage files.

OpenSSH/SFTP/rsync remain deferred to a future independently validated image. Guest `PT_INTERP` path remains missing; actual relocation, weak-symbol resolution, ARM TLS, historical source authenticity, kernel ABI, safe recovery and boot remain unverified. **`NOT_BOOTABLE`.**