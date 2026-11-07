# R3877.33.1 — bounded long-neighbor build-log triage

For research and educational purposes only. `NOT_BOOTABLE` remains immutable.

R3877.33 stopped at `NEXT_LINE_TOO_LONG` (exit 2) because an adjacent printed line exceeded a local 15,000-character guard. This does not invalidate the pinned public log or imply a compiler failure.

The host-only diagnostic in the ChatGPT-distributed ZIP `pw3-r3877-33-1-long-neighbor-triage.zip` is checksum `b613ebc42d0854b2e9621df5c1e1a5e86fa4acf90e78d91596790887d229a005`. It passed 118 local synthetic tests and clean archive validation; **the Python implementation and tests are not committed in this evidence-only commit**.

The diagnostic rechecks the original 1,644,394-byte public log (SHA-256 `a8405a50c1849aebc0fefadcab4e4f7fa7da27d9c1296fa2ce46b73df56ca2ce`) and physical linker-like log line 1666 (SHA-256 `1082a4442e1edcdcdedcda614abceae9d08961b69bd7bb0c09c2010dbefe6dcd`). It fingerprints the full next printed line and reports its length, without printing raw commands or paths.

A fully joined candidate is lexed **only when at most 256 KiB**, otherwise it reports `NOT_LEXED_OVERSIZED_PRINTED_NEIGHBOR` and a line hash. This is metadata triage, not a verified historical shell invocation.

Run on the user's Mac after obtaining the downloadable ZIP:

```sh
mkdir -p ~/Downloads/pw3-r3877-33-1
unzip -oq ~/Downloads/pw3-r3877-33-1-long-neighbor-triage.zip -d ~/Downloads/pw3-r3877-33-1
cd ~/Downloads/pw3-r3877-33-1
shasum -a 256 -c SHA256SUMS_R3877_33_1.txt
python3 -B -m unittest -q test_r3877_31.py test_r3877_32.py test_r3877_32_1.py test_r3877_32_2.py test_r3877_33.py test_r3877_33_1.py
set -o pipefail
python3 -B pw3_r3877_33_1_long_neighbor_triage.py \
  ~/Downloads/pw3-r3877-30/musl-armv7-build.log | tee r3877_33_1_result.json
echo "R3877_33_1_EXIT_CODE=$?"
```

Expected success *classification* if all input hashes match: `PASS_PINNED_LONG_NEIGHBOR_LOG_TRIAGE_ONLY`. Runtime linker provenance, complete historical flags, binary reproducibility, Kindle recovery, and bootability remain unverified.
