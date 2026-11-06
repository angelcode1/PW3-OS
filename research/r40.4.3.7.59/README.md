# R40.4.3.7.59 — R13 manifest provenance survey

Read-only source-only audit, immutable NOT_BOOTABLE. Replays the SHA-pinned R3758 historical 2070-entry stage inventory baseline and reviews an original R13-MANIFEST.json file if and only if present as a unique regular file in that inventory. Does not run guest code, mutate the stage, create symlinks, apply relocations, prune or boot.

Mac R3758 returned complete hash/mode agreement for 1,448 regular files, 335 symlinks, 287 directories and 2,070 permission modes. The original R26 source and any R13 manifest source chain remain **unauthenticated** despite historical content agreement.

R3759 inspects bounded JSON schema categories, declared signature/attestation/source metadata families, and optionally checks recognizable regular-file SHA256 records privately against original R26 entries. Signature-shaped fields are **not** cryptographically verified. Unsupported layouts are reported not comparable, not falsely verified. It never exports private names, paths, file hashes or data.

Distribution: pw3-r3759-r13-manifest-provenance-survey-readonly.zip, SHA256 042a5afd2e8cbb439ab4e308f08067aadc0179a0fd8bd37fad5d7f74a0ca51f0; 65 file members and 64 checksum entries. Host synthetic 940/940 tests pass, including 39 new and 901 inherited tests; clean-extraction verification passed. The full runnable source, tests and pinned predecessors are in the conversation ZIP, not standalone GitHub files. No GitHub Actions pass is claimed.

Mac runbook: download the ZIP into ~/Downloads, extract into ~/Downloads/pw3-r3759, verify `shasum -a 256 -c SHA256SUMS`, run `python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v`, then run:

```
python3 -B R4043759-R13-MANIFEST-PROVENANCE-SURVEY-READONLY.py \
  --stage "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  --r26-inventory "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-INVENTORY.json" \
  --parent-dir "$PWD"
```

Send result JSON including `r13_manifest_metadata_field_categories`, `r13_manifest_file_hash_collection` or `hold_category`. No signed trust root or original source provenance verified; missing guest PT_INTERP path, real loader behavior, ARM TLS and recovery are unresolved. NOT_BOOTABLE.
