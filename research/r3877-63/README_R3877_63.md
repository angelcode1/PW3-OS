# PW3-OS R3877.63 — Candidate-first recovery header and local checksum triage

**For research and educational purposes only. The physical Kindle remains `NOT_BOOTABLE`.** This is a local Mac metadata/content-inspection experiment, **not** a recovery procedure. It does not contact a Kindle, access Docker/QEMU, restore anything, boot, modify firmware, extract archives, invoke commands from files, or write to the scanned directory.

## Why R3877.63

The user-reported R3877.62.2 Mac inventory completed a scan of 58,080 entries (depth 3, 100,000-entry budget): 51 research-named ZIPs, **4 nonresearch backup-named archives totaling 69,302,116 bytes**, 5 recovery-document candidates and 61 manifest-filename candidates. There were **no direct stock partition image candidates** in that bounded scope, but archive internals had **not been inspected**. Neither file names nor reported sizes authenticate a recovery backup. R62.2 returned the required `HOLD` / exit 2.

## What this new experiment inspects, on explicit opt-in only

1. Re-run the pinned R62.2 metadata triage, requiring a complete bounded scan, then re-enumerate candidates with the same exclusions and symlink rules. Reject changed candidate counts.
2. Restrict reads to the **nonresearch backup-named archives**, any separately named raw image candidates, checksum-manifest filenames and recovery-document filenames. Ignore the 51 research packages. Refuse if more than 256 review files, if aggregate archive candidate bytes exceed 256 MiB, if any archive candidate exceeds 128 MiB, or if any manifest/document exceeds 256 KiB.
3. Open regular files read-only with `O_NOFOLLOW` where supported, verify inode/device/size/mtime against the selected metadata both before and after reading. Hash only the selected archives; **do not publish content hashes or file paths**.
4. Inspect ZIP end-of-central-directory and central directory metadata only, with limits (4,096 members, 2 MiB central directory); count image-named entries, suspicious paths, symlink or encrypted members. **Never extract, decompress, run scripts, or open member payloads.** Treat tar/gzip/xz/zstd/7z as opaque formats rather than guessing at their contents.
5. Read small checksum-manifest files and count *exact SHA-256 + basename* matches for the selected archives. Matches may be self-authored or from untrusted sources and **never prove authenticity**. Read small plaintext recovery documents only for counts of relevant terms; PDFs/binary docs remain opaque. No document text or private filenames are printed.
6. Output anonymous per-archive IDs `A01`, etc., plus content signatures and aggregate observations. Continue to exit **2 / HOLD**. Even an internal image and matching checksum do not establish stock authenticity or an independent recovery interface.

The bounds above are intentionally conservative: the script may HOLD if a ZIP uses unsupported features or there are unexpected large files. This is not permission to loosen safeguards or start recovery operations.

## Mac commands

```zsh
mkdir -p ~/Downloads/pw3-r3877-63
unzip -oq ~/Downloads/pw3-r3877-63-recovery-headers.zip -d ~/Downloads/pw3-r3877-63
cd ~/Downloads/pw3-r3877-63
shasum -a 256 -c SHA256SUMS_R3877_63.txt
python3 -B -m unittest -q test_r3877_62.py test_r3877_62_2.py test_r3877_63.py

# Expected no-read HOLD / exit 2:
python3 -B pw3_r3877_63_recovery_candidate_headers.py

# EXPLICIT opt-in: read bounded bytes from only local candidate files.
setopt pipefail
python3 -B pw3_r3877_63_recovery_candidate_headers.py \
  --scan-root "$HOME/Downloads" \
  --max-depth 3 \
  --max-entries 100000 \
  --max-candidates 3000 \
  --acknowledge-readonly-content-inspection \
  | tee r3877_63_result.json
printf 'R3877_63_EXIT_CODE=%s\n' "$?"
```

Expected tests: **83 tests** including one Linux-only skip for macOS-specific coverage; all test cases pass on the macOS and Ubuntu matrix. The user-facing runtime **always returns HOLD/exit 2**. Useful report fields: `review.archive_candidates`, `review.archive_candidates_with_matching_untrusted_sha256_manifest`, `review.recovery_doc_keyword_mentions_by_document`, `review.scope.bounded_scope_scan_complete`. No success classification authorizes a Kindle boot.

## Important nonclaims

- A matching checksum from a nearby file is not an externally authenticated stock recovery image.
- A ZIP containing a file named `rootfs.img` is not proof that its contents are safe, valid, correctly sized, or restorable.
- A document mentioning UART/serial/fastboot is not proof the user has working independent recovery access.
- Empty/absent results do not prove no recovery path exists outside the limited folder/depth scope.
- macOS file access may incidentally update access-time metadata depending on filesystem policy, but the script never writes file contents or creates local files. `tee` in the suggested command does create the explicitly requested report file.
- QEMU success from R3877.61 does not verify Kindle Linux `3.0.35-lab126` time64 or other syscall compatibility, and application secure entropy fallback remains separately unverified.

No network, no user-owned path publication, no Kindle SSH, no firmware modifications, no recovery test, no new backup, no QEMU/ARM guest execution. `NOT_BOOTABLE` remains immutable.
