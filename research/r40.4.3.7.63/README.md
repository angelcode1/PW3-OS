# R40.4.3.7.63 — Amazon PW3 public-source origin comparison (offline)

**Research and education only. NOT_BOOTABLE.** This is a host-only source comparison tool, not a firmware installer or loader. The original R13/R26 evidence and R3762 corrected release are unchanged. No device access, guest execution, interpreter mapping, firmware writes, pruning or boot.

## New upstream lead

Amazon's [source code notice](https://digprjsurvey.amazon.com/csad/help/node/200203720) currently lists the **Kindle Paperwhite (7th Generation)** entry `Kindle_src_5.16.2.1.1_4097470002.tar.gz`, which links to:

`https://kindledownloads.s3.amazonaws.com/Kindle_src_5.16.2.1.1_4097470002.tar.gz`

The community mirror used in R3762 points to a different, older Amazon-listed archive: `Kindle_src_5.10.1.1_3358210034.tar.gz`. The 5.10.1.1 entry in Amazon's displayed PW3 source list is *labeled* `3358230034`, but its currently linked URL ends in `3358210034`. **Do not equate the displayed filename and the URL without verifying the actual target.** This ambiguity is one reason R3763 pins the unambiguous 5.16.2.1.1 URL and reports findings only.

This source is **not** independently authenticated R13-image provenance. The official Amazon source listing can help anchor *public source-file content* if the download succeeds and the compared bytes match. An archive filename and locally observed SHA-256 are not an independently signed provenance chain.

## Download the public source (Mac, host-only)

From Terminal, with sufficient free disk space:

```sh
cd "$HOME/Downloads"
curl --fail --location --show-error --retry 2 \
  'https://kindledownloads.s3.amazonaws.com/Kindle_src_5.16.2.1.1_4097470002.tar.gz' \
  --output 'Kindle_src_5.16.2.1.1_4097470002.tar.gz'
```

Do not use `curl -k` or disable TLS certificate validation. No download attempt was completed in the assistant's environment; the archive might be unavailable or the link might change. Do **not** upload the archive to the repository.

## Offline test against the Amazon archive

Use Python 3.9+ and the repository's R3763 Python script:

```sh
python3 -B R4043763-AMAZON-PW3-SOURCE-COMPARE-READONLY.py \
  --archive "$HOME/Downloads/Kindle_src_5.16.2.1.1_4097470002.tar.gz"
```

The program reads the local tar archive directly and, when present, the nested kernel-source tar stream. It never extracts files to disk. It searches for an unambiguous `arch/arm/configs/imx60_wario_defconfig` regular file, compares its full Git blob identity to R3762's pinned `bbc2f92713d05dfd6ea52973fc7d958e49fa6464` (59,582 bytes), and emits JSON.

- On a single exact match: `AMAZON_LISTED_ARCHIVE_WARIO_BLOB_MATCH_STATIC_ONLY`, exit 0.
- On a missing, different or ambiguous configuration, malformed archive, symlink path, changed input or other invalid condition: `HOLD`, exit 2.

Even a match leaves `archive_origin_cryptographically_authenticated=false`, `r13_image_provenance_authenticated=false`, `actual_pw3_running_kernel_verified=false` and `immutable_hold=NOT_BOOTABLE`. If the official archive contains a different defconfig, do not tamper with the R3762 pin to force agreement; record the genuine divergence.

## Host CI and limitations

The 14 synthetic tests include direct and nested tar members, matching and differing blobs, symlinks, corrupt and nonregular entries, missing configs and duplicate candidates. CI never downloads Amazon archives, never touches any Kindle and never executes guest binaries. The actual official archive has **not yet been downloaded and verified**.

Passing tests proves the checker functions on synthetic inputs; it does not establish Amazon archive availability, authenticity, or a match. Comparing the published public source does not prove that R13 originates from Amazon, that the physical Kindle runs a matching kernel, that TLS/ABI is compatible or that boot is safe.

**NEXT EVIDENCE:** Run this checker on a locally downloaded Amazon-hosted source archive and provide only the JSON output (without sensitive device files). If the archive is unavailable, record a hold instead of inventing a replacement.

**NOT_BOOTABLE.**
