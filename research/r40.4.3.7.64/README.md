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

This extremely tight match strongly supports a single-setting delta; **it does not prove actual Amazon file byte equality** without a SHA-256 of that *observed* archive member (or direct comparison). Hash collision limitations also apply. No arbitrary source edits were made to the R3762 pin.

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

## Final direct byte comparison — still requested

The user has an existing R3764 diagnostic ZIP with the user-run offline scanner. For an **independent, actual byte equality check**, run the separate exact-delta verifier on the same existing local Amazon archive. It compares the complete Amazon defconfig bytes with the reconstructed config and reports the observed Amazon config SHA-256, without extracting the archive or modifying it. Its exit code remains **2** and `NOT_BOOTABLE` remains enforced even if equality is confirmed.

The original R3764 auditor ZIP (SHA-256 `fa80b24ca8ba5fee2ca0ecc63055c4df621875f39f8da5d2726f0380602af2c6`) and follow-up verifier ZIP (`a98d405d33efc905c587feb92bdedd779493ab83bd1b0f2ca09209806b0d0985`) were validated in the assistant's isolated environment with 17 original plus 6 new regression tests (23/23 total). Their original checked manifests are unchanged; they have **not** been uploaded to this repository.

## Unresolved evidence gates

Source archive origin has no independently verified signature or trusted upstream digest; R13 image provenance is not authenticated; the exact device firmware/running kernel, ARM loader startup, TLS, ABI and recovery remain unverified. The R3763/R3764 mismatch HOLD must **not** be removed merely because the single option is understood.

**NOT_BOOTABLE.**
