# R40.4.3.7.12.2 — all-known-predecessor read-only inventory

**2026-11-04. Host-tested source-only diagnostic; user Mac results pending; NOT_BOOTABLE. Research and educational purposes only.**

The original R40.4.3.7.12 Mac source verifier continues to refuse before ARM execution, despite checksums for the R3712 release itself reporting OK. Prior source diagnostics showed sequential missing release prerequisites; the latest generic HOLD does not identify the current one.

The standalone script `R4043712-ALL-PREREQUISITES-READONLY.py` checks **13** public predecessor release directories, **160** release files against independently verified released ZIP SHA-256 manifests (including each manifest itself), **two** private/public collector-output SHA-256 digests (no source content exported), and **18** original staged KOReader menu sources against the R378-v2026.07.2 Git blob SHA-1 pins. Rejects symlinked paths and files and unexpected release files; prints only allowlisted public member and release labels and fixed categories; does not expose private source/path, arbitrary unknown filename or log content.

SHA-256 `b8cc5981845745fd5913480539dc7e18ead43b70a29d44c71e33cde36efe0fdc`, 26,319 bytes. Locally verified against all 13 clean-extracted public ZIPs plus the two collector digests; negative fixtures detected one missing prior source, one tampered source, two simultaneously absent release dirs, an extra unidentified member, and a symlink. No genuine user Mac stage was accessed, and a PASS here is not equivalent to the original full verifier passing. All previous R375 synthetic ARM historical PASS and R3711 TouchMenu INDEX_ERROR HOLD status remain unchanged; R3712 QEMU not started.

Mac: save the standalone script in Downloads, then `python3 -B "$HOME/Downloads/R4043712-ALL-PREREQUISITES-READONLY.py"`. Share only its fixed `R4043712_CLOSURE_HOLD` and `R4043712_CLOSURE_SUMMARY` lines (or PASS line). Do not automatically repair/overwrite release directories or bypass full source verification.

Historical staged observed open union 347 not recomputed; 1,101 unobserved stage regular files and 976 historical UNKNOWN_HOLD retained. Provenance and complete dependency closure unproven; QEMU decoder incomplete. No device/firmware/hardware writes, boot, file removal, or pruning: **NOT_BOOTABLE**.
