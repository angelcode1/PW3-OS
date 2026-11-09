# PW3-OS R3877.65 — TAR extended-name / bounded gzip stream structural triage

**Research/education only. Physical Kindle remains `NOT_BOOTABLE`.** No Kindle SSH, firmware write, boot, image manipulation or restore. This is local Mac-only, read-only analysis of already-discovered candidate files. Even complete TAR metadata, a verified gzip checksum, or a locally matching untrusted SHA-256 manifest does **not** authenticate a stock Kindle backup or demonstrate independent recovery.

## Why R3877.65

The **user-reported R3877.64 Mac result was HOLD / exit 2**. A01 was a 23,388,160-byte TAR containing six regular members and five extended/sparse headers; A02 was a 42,721,280-byte TAR containing eight regular members and seven extended/sparse headers. Both had a valid two-zero-block ending but *incomplete effective-name coverage*. A04 was a 3,183,009-byte gzip: its first bounded 512 KiB expanded into a TAR prefix with 26 headers (22 dirs, 3 files, 1 symlink), but the prefix ended before TAR termination. A03 remained the small six-entry ZIP. No recovery/stock image was authenticated.

## What changed and limits

- Reuse and pin the R3877.64 / R3877.63 / R3877.62.2 / R3877.62.1 dependency chain, unchanged. No Mac recompile or third-party modules.
- TAR reader checks USTAR magic, octal size, header checksum, two-zero-block terminator, and record count. Reads **only TAR headers and necessary extended-name metadata**, seeks over member bodies in uncompressed TAR files, and does not extract anything.
- Recognizes bounded POSIX PAX `x`/`g` records and GNU `L`/`K` longnames to classify **effective** member names (never prints them). Rejects malformed PAX records, oversize extensions, unsupported sparse headers, disagreeing PAX sizes and undecodable names as *incomplete*; does not invent coverage.
- For gzip only, decompresses into **ephemeral memory**, capped at **8 MiB compressed input, 64 MiB decompressed bytes**, and a **128:1 expansion guard**; validates gzip CRC/trailer only if the complete single gzip stream is observed. Reports unverified truncated, concatenated or trailing data. The gzip stream intrinsically decompresses member payload bytes into memory, but nothing is saved/extracted; only TAR header and bounded extension metadata are parsed from the inflated bytes.
- Each TAR is capped at **8,192 headers**, each extension at **64 KiB**, and combined extension payload bytes at **512 KiB**. No member filename, link target, raw digest or local path is emitted. Unsafe paths/links are counted, never followed.
- The prior candidate scan remains bounded to depth 3, 100,000 entries, and 3,000 filename candidates. The report assigns stable ephemeral candidate IDs A01–A04, but never releases filenames. No network, Docker, QEMU or physical-device work.

A test result of `TAR_NAMES_RESOLVED_HEADERS_COMPLETE` or `tar_full_coverage_verified: true` verifies only bounded *metadata name coverage*, **not data integrity, a usable image, or recovery authenticity**.

## Mac instructions (zsh)

```zsh
mkdir -p ~/Downloads/pw3-r3877-65
unzip -oq ~/Downloads/pw3-r3877-65-tar-extended-gzip-triage.zip -d ~/Downloads/pw3-r3877-65
cd ~/Downloads/pw3-r3877-65
shasum -a 256 -c SHA256SUMS_R3877_65.txt
python3 -B -m unittest -q test_r3877_62.py test_r3877_62_2.py test_r3877_63.py test_r3877_64.py test_r3877_65.py

# With no opt-in the scanner returns HOLD/exit 2, without scanning.
python3 -B pw3_r3877_65_extended_tar_triage.py > r3877_65_preflight.json
printf 'R3877_65_PREFLIGHT_EXIT_CODE=%s\n' "$?"

# Opt in to read-only metadata plus bounded *in-memory* gzip decompression.
setopt pipefail
python3 -B pw3_r3877_65_extended_tar_triage.py \
  --scan-root "$HOME/Downloads" \
  --max-depth 3 \
  --max-entries 100000 \
  --max-candidates 3000 \
  --acknowledge-readonly-extended-metadata-and-bounded-gzip-decompression \
  | tee r3877_65_result.json
printf 'R3877_65_EXIT_CODE=%s\n' "$?"
```

Expected offline suite: **142 tests** (one macOS-only test is skipped on Linux). The actual Mac scan **always** produces `result: HOLD` and exits **2**, including if complete archive metadata is observed.

Useful new fields: `review.archive_candidates[].structural_review.full_name_coverage_verified`, `extension_header_counts`, `stock_image_named_member_count`, `unsupported_sparse_or_other_count`; and, for A04, `gzip_full_stream_integrity_verified`, `tar_full_coverage_verified` and `tar_headers`.

## Remaining holds

No original vendor Linux 3.0.35 syscall dispatch or time64 fallback measured; no independent Kindle restore path tested; no stock partitions authenticated; no validated application-level secure entropy fallback. Do **not** boot or flash. Results belong only to off-device structural triage. The immutable hold is **`NOT_BOOTABLE`**.
