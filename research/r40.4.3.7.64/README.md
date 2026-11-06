# R40.4.3.7.64 — Amazon Wario defconfig delta and exact fingerprint reconstruction

**Research/educational only. NOT_BOOTABLE.** This records the user's *local* R3764 report and a separate reproducible, host-only SHA-1/size reconstruction. No device access, guest execution, interpreter mapping, firmware writes, pruning or boot.

## What the user observed

The Amazon-listed PW3 source bundle `Kindle_src_5.16.2.1.1_4097470002.tar.gz` was scanned locally on macOS using the R3764 offline tool. The tool found a Wario defconfig in a nested kernel source tar, and returned `OFFICIAL_ARCHIVE_WARIO_CONFIG_BLOB_DIFFERS_HOLD` (exit code 2).

- Observed source archive: 331,107,525 bytes; SHA-256 `af3355ecc855d4c91ab86b3442ec05209b3748e3bf594277cba3261f2e6bafa5`.
- Older pinned R3762 defconfig: 59,582 bytes; Git blob SHA-1 `bbc2f92713d05dfd6ea52973fc7d958e49fa6464`.
- User-observed Amazon defconfig: 59,593 bytes; Git blob SHA-1 `b4ed2a1f317de6c11f75582327d847b30eae2547`.
- Parsed config keys: 1,769 in each; zero added/removed; exactly **one raw-value/status change**, `CONFIG_COMPAT_BRK`. All 23 R3762 tracked feature statuses match.

**Important:** these archive and Amazon blob measurements are **user-reported evidence**, not a download or byte scan performed on GitHub runners.

## Independent fingerprint reconstruction

The repo's R3762 reference contains exactly one line `CONFIG_COMPAT_BRK=y`. Replacing that exact line with `# CONFIG_COMPAT_BRK is not set` produces 59,593 bytes and **exactly** Git blob SHA-1 `b4ed2a1f317de6c11f75582327d847b30eae2547` — the reported Amazon fingerprint. The constructed complete config SHA-256 is `71eca1037a4428e11fb8a03c66e3ef78d5f0d24d5338035588c7963ed28b1833`.

This reconstruction alone was initially insufficient to establish the actual Amazon file's byte equality. **A later, separate user-run direct comparison now reports full byte-for-byte equality**, and its observed SHA-256 agrees with the reconstructed SHA-256 (see below). GitHub Actions does not download or inspect the Amazon archive. No arbitrary source edits were made to the R3762 pin.

The `R4043764-COMPAT-BRK-FINGERPRINT-PROOF.py` script performs that reconstruction deterministically from the pinned R3762 file and prints read-only JSON. CI exercises the proof on Linux/macOS and Python 3.9/3.12 without downloading or opening any Amazon archive. A green workflow is a host proof only, **not** an authenticated public archive comparison.

## Meaning of CONFIG_COMPAT_BRK

Upstream Linux `CONFIG_COMPAT_BRK` controls the boot-time default for legacy heap layout compatibility: `y` generally leaves heap randomization disabled by default, while `n` generally enables heap randomization by default, subject to `/proc/sys/kernel/randomize_va_space` and other runtime conditions. This change does **not** show that a physical PW3 kernel has either configuration, or verify the guest's ABI/TLS/loader functionality.

Background: [Linux Kernel Driver DataBase](https://www.cateee.net/lkddb/web-lkddb/COMPAT_BRK.html), [Ubuntu ASLR documentation](https://documentation.ubuntu.com/security/security-features/process-memory/aslr/).

## Reproduce the host proof

```sh
python3 -B research/r40.4.3.7.64/R4043764-COMPAT-BRK-FINGERPRINT-PROOF.py
python3 -B -m unittest discover -s research/r40.4.3.7.64 -p 'test_r4043764_fingerprint_proof.py' -v
```

No path in the stage, private device data, or firmware is modified.

## Final direct byte comparison — user-reported PASS (mismatch HOLD remains)

On 2026-11-06, the user executed `R4043764-COMPAT-BRK-EXACT-DELTA-VERIFY.py` against the **existing locally downloaded** Amazon source archive. The user reported both supplemental script checksum checks as `OK`, and supplied this read-only result:

| Gate | Local result |
| --- | --- |
| `observed_full_config_bytes_equal_single_line_reconstruction` | **true** |
| `observed_amazon_config_sha256` | `71eca1037a4428e11fb8a03c66e3ef78d5f0d24d5338035588c7963ed28b1833` |
| `reconstructed_config_sha256` | `71eca1037a4428e11fb8a03c66e3ef78d5f0d24d5338035588c7963ed28b1833` |
| `observed_amazon_config_blob_sha1` | `b4ed2a1f317de6c11f75582327d847b30eae2547` |
| `observed_amazon_config_size_bytes` | 59,593 |
| `observed_archive_report_sha256_match` | **true** |
| `evidence_check` | `EXACT_ONE_LINE_CONFIG_DELTA_CONFIRMED_STATIC_ONLY` |
| Exit code | **2**, intentional `PUBLIC_REFERENCE_BLOB_DIFFERS_HOLD` |

The local verification reports literal equality between the observed Amazon member and a one-line reconstruction of R3762's pin (`CONFIG_COMPAT_BRK=y` to `# CONFIG_COMPAT_BRK is not set`). This **closes the static defconfig difference question** at the level of the user's supplied local measurements. No Amazon archive or extracted member is committed to the repository. GitHub CI checks the internal consistency of the report and independently reconstructs its advertised SHA-256 **without opening the actual archive**.

The result is preserved verbatim in `USER-MAC-EXACT-ARCHIVE-EQUALITY.json`. The earlier `USER-MAC-AUDIT-AND-RECONSTRUCTION.json` remains a historical record of the *prior* uncertainty; it must not be overwritten or reinterpreted as contradicting the later finding. The original R3764 auditor ZIP (SHA-256 `fa80b24ca8ba5fee2ca0ecc63055c4df621875f39f8da5d2726f0380602af2c6`) and follow-up verifier ZIP (`a98d405d33efc905c587feb92bdedd779493ab83bd1b0f2ca09209806b0d0985`) were validated separately with 23/23 synthetic tests but are not committed.

**Important distinction:** The reported direct comparison does not independently cryptographically authenticate the Amazon archive's origin, authenticate the unrelated R13 image, determine the running PW3 kernel, or establish ARM ELF loader, TLS/ABI, recovery or boot compatibility. The two reference source files still differ, so **the HOLD and exit code 2 are correct**.

## Unresolved evidence gates

Source archive origin has no independently verified signature or trusted upstream digest; R13 image provenance is not authenticated; the exact device firmware/running kernel, ARM loader startup, TLS, ABI and recovery remain unverified. The R3763/R3764 mismatch HOLD must **not** be removed merely because the single option is understood.

**NOT_BOOTABLE.**
