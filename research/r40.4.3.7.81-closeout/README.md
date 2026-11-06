# R3779–R3781 — Verified user Mac closeout and evidence boundary

**Research and educational use only. Original R13 stage unchanged. Immutable `NOT_BOOTABLE`.**

## Local result confirmed by the user

After downloading `pw3-r3781-static-investigation-closeout.zip`, the user reported `shasum -a 256 -c SHA256SUMS` returned **OK for all five entries** and `python3 -B verify_reports.py` returned `R3781_CLOSEOUT_REPORTED_EVIDENCE_CONSISTENT_NOT_BOOTABLE`, exit code **0**. The assistant independently checked the identical ZIP in its working container; its SHA-256 was `e5435f2a904880fd292f53c67db76964ba0f36a722c8444ea69e6dc3843a592d`.

`USER-MAC-CLOSEOUT-VERIFIED.json` preserves these user-reported checks and the **exact SHA-256 values of all five ZIP members**, as well as selected diagnostic counts. **This record is a summary, not the original full user-Mac JSON files.** The five member checksums identify the original evidence ZIP. No private stage data, package names, local script bodies or hashes of staged files are published.

## Findings retained without overclaiming

- **R3779:** Three affected signed Alpine package/index control identities matched using staged public keys. All 28 comparable non-architecture fields agreed, eight optional comparisons could not be made, and three architecture differences remained (`noarch` vs repository architecture). This pattern is compatible with `apk index --rewrite-arch`, but **does not prove the original build invoked it**.
- **R3780:** In eight bounded adjacent script candidates, three scripts referenced the exact path of one discrepant symlink. A write-like hint in one of those scripts did **not** establish a write targeting the symlink.
- **R3781:** All three path-bearing script references were comments. Zero active literal path references or plausible direct-write destinations were detected by the supported parser, with one script remaining unclassified. This **does not rule out** dynamic paths, other sources or historical modifications.
- **Earlier R3775/R3778:** One staged regular file and three staged symlink targets differ from the retrieved signed package payloads. The original build's cause, timing, and R13 image origin remain unknown.

## Decision

Close the repeated local lexical script investigation. The next substantive provenance test requires an **independently authenticated original image/source release or reproducible build trace** linked to R13, not another checksum scan of the same eight local scripts. Runtime ABI/TLS and missing PT_INTERP remain separate future-image gates, and an actual guest runtime trial is not authorized.

## GitHub CI scope

The accompanying workflow checks the **internal consistency of this summary and its immutable flags**, not the original Mac stage, and does not elevate a user-reported SHA-256 check into external source authenticity. All earlier HOLDs remain effective. No stage alteration, guest execution, firmware writes, device access, mapping, pruning, or boot is authorized. **NOT_BOOTABLE.**
