# PW3 R3877.39 — Five copy destinations: exact printed consumers

**Research and educational purposes only. `NOT_BOOTABLE` is immutable.** No Kindle SSH, install, boot, firmware write, ARM binary execution, host compilation, Docker guest operation, or evaluation of printed shell text.

## Result established by the user (R3877.38)

The user reported `PASS_PINNED_FIVE_EXTRA_OBJECT_COPY_ARGUMENT_STRUCTURE_ONLY` (exit 0). In the pinned Alpine musl 1.2.6-r3 ARMv7 public build log, 1,428 printed compile outputs have 1,423 exact-text matching object inputs in the two-line main linker candidate. The five other compile outputs each appear once as a source operand of a *printed* `cp` command, with five distinct printed copy destinations. Previous outputs/command identifiers and path basenames remain private. The log itself is **not cryptographically authenticated**, printed commands are not attested argv, and no filesystem copy has been demonstrated.

## Audit R3877.39

The new analyzer accepts only the existing log with pinned byte length 1,644,394 and SHA-256 `a8405a50c1849aebc0fefadcab4e4f7fa7da27d9c1296fa2ce46b73df56ca2ce`. It recursively repeats the R3877.31–38 checks, including the joined-link and linker-line fingerprints. All operations are Python parsing and exact string comparison in memory.

For the five `cp` lines, it rechecks that each original unlinked object is a source operand and that destinations are distinct. It classifies only coarse destination filename suffix types, separates single-source from multiple-source `cp` shapes, and compares each private destination text against printed compile-output and main-link object text. It then counts **later** exact full-token occurrences elsewhere in the log, aggregated by printed command family. No paths, basenames, tokens or per-path hashes are emitted. It does not claim a destination was copied, installed, executed, or loaded.

The audit cannot determine historical compiler identities, exact executed linker argv, package source-to-binary reproducibility, vendor Linux syscall dispatch, or Kindle boot/recovery safety. One other printed log line was not lexically parsed in R3877.38; that incompleteness is carried forward explicitly, so an absence of later mentions is **not** absence of actual consumers.

## Run on macOS

```sh
mkdir -p ~/Downloads/pw3-r3877-39
unzip -oq ~/Downloads/pw3-r3877-39-copy-destination-consumers.zip -d ~/Downloads/pw3-r3877-39
cd ~/Downloads/pw3-r3877-39
shasum -a 256 -c SHA256SUMS_R3877_39.txt
python3 -B -m unittest -q test_r3877_31.py test_r3877_32.py test_r3877_32_1.py test_r3877_32_2.py test_r3877_33.py test_r3877_33_1.py test_r3877_34.py test_r3877_35.py test_r3877_36.py test_r3877_37.py test_r3877_38.py test_r3877_39.py
set -o pipefail
python3 -B pw3_r3877_39_copy_dest_consumer_audit.py \
  ~/Downloads/pw3-r3877-30/musl-armv7-build.log | tee r3877_39_result.json
echo "R3877_39_EXIT_CODE=$?"
```

Expected successful classification, only after **real pinned log** analysis: `PASS_PINNED_FIVE_COPY_DESTINATION_TEXT_CONSUMER_TRIAGE_ONLY`. A successful synthetic test suite does not establish what the real-log counts will be. Any missing, modified, symlinked, or unexpected log fails closed with exit 2 and `HOLD`.

## Next substantive gate

After the five destination references are classified, prioritize recovering historical builder toolchain identity and build-environment provenance, rather than inferring binary reproducibility from printed log structure. No build is authorized on the Kindle.
