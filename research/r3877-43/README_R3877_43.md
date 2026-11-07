# R3877.43 — Offline signed APKINDEX toolchain package candidates

Research/educational only. Immutable **NOT_BOOTABLE**.

R3877.42 user-reported Mac audit passes against the exact pinned public musl ARMv7 log. It finds only one ambiguous `abuild 3.17.0` text clue, no version banners/probes and no explicit ARM ABI switches. It **does not** establish installed historical build-tool versions.

R3877.43 is a standalone Mac-side diagnostic distributed as `pw3-r3877-43-signed-index-toolchain-candidates.zip` in the originating ChatGPT working session. The Python implementation and tests are **not yet committed here**. Its authoring package reportedly passed clean-ZIP verification and **110 synthetic offline tests**. The subsequent **user-reported real-input result passed (exit 0)** with classification `PASS_PINNED_SIGNED_INDEX_TOOLCHAIN_PACKAGE_CANDIDATES_ONLY`; see `R3877_43_USER_REPORTED_SELECTED_EVIDENCE.json`. Neither the run nor its local inputs were independently reproduced by GitHub CI.

The run checked the exact previously pinned Alpine v3.24/main/armv7 APKINDEX SHA-256 `5a709ea29c02499f799f2e56a2af7fe95f4dd6859867bbe65a0aa597fe294140`, re-verified its RSA signature using the Git-blob-pinned public key and host OpenSSL, rechecked the R3877.42 log, and found the allowlisted published package versions for abuild, binutils, build-base, gcc, make, musl and musl-dev. The key trust anchor is pinned to a Git snapshot, not independently established. The report must **never** equate published index package versions with **the historical builder's installed packages**. The public index snapshot is not independently time-anchored to the musl build; neither historical toolchain versions nor effective ARM float ABI, reproducibility, target musl runtime, or device recovery is verified.

Mac commands to reproduce locally with the original separately distributed ZIP and pinned inputs:

```sh
cd ~/Downloads/pw3-r3877-43
shasum -a 256 -c SHA256SUMS_R3877_43.txt
python3 -B -m unittest -q test_r3877_24.py test_r3877_25.py test_r3877_41.py test_r3877_42.py test_r3877_43.py
set -o pipefail
python3 -B pw3_r3877_43_signed_index_toolchain_candidates.py \
  --r42-report ~/Downloads/pw3-r3877-42/r3877_42_result.json \
  --log ~/Downloads/pw3-r3877-30/musl-armv7-build.log \
  --key-dir ~/Downloads/pw3-r3877-40-1/aports-keys \
  --downloads ~/Downloads | tee r3877_43_result.json
echo "R3877_43_EXIT_CODE=$?"
```

Expected real-input pass classification: `PASS_PINNED_SIGNED_INDEX_TOOLCHAIN_PACKAGE_CANDIDATES_ONLY`. Any input mismatch must HOLD; no pin relaxation. **No Kindle access, ARM execution, firmware writes or boot.** The prior R3877.5 ARMv7 BusyBox exit-127 HOLD and all independent-boot/recovery gates remain open.
