# PW3 R3877.35 — Printed compiler-output versus linker-object consistency

**Research and educational use only. Immutable hold: `NOT_BOOTABLE`.**

## What R3877.34 proved

The user's Mac verified the unchanged public Alpine musl 1.2.6-r3 ARMv7 build log (1,644,394 bytes; SHA-256 `a8405a50c1849aebc0fefadcab4e4f7fa7da27d9c1296fa2ce46b73df56ca2ce`). Lines 1666–1667 are a `shlex`-parseable *printed* 1,494-token link candidate, with 1,423 object-like tokens, two shared-library-like tokens and one `-o` output switch. The 1,428 printed compile command lines were verified earlier. **This is not attested historical argv.**

## What this diagnostic does

1. Reads the pre-existing R3877.30 log **only** from the Mac's filesystem. Requires the exact pinned byte count and SHA-256 and reruns all the R3877.34 candidate/neighbor hash checks.
2. Classifies the 1,428 compile lines using the same selector as R3877.32, `shlex`-tokenizes them without evaluating any shell expression, and accepts only a single *literal* `-o OBJECT.o` or `-o OBJECT.lo` output. Unknown/missing output forms are counted as not extractable; lexical failure or driver change triggers a hold.
3. Reconstructs the printed two-line linker candidate for **text comparison only** and requires the existing 1,494-token and 1,423-object counts.
4. Compares the **complete exact object-text tokens internally**, preserving duplicate multiplicities. It emits the match, mismatch, duplicate and unextractable counts, **never the object names, basenames, paths, raw tokens or per-object digests**. No basename fallback, shell expansion, path normalization or inferred historical execution.
5. Keeps historical toolchain, builder identity, `CFLAGS/LDFLAGS`, reproducibility, Kindle runtime and recovery **unverified**.

The difference `1,428 - 1,423 = 5` does **not** prove five missing object files: exact matching, duplicate outputs, non-object auxiliary compilations and printed-log limitations must first be checked.

## Run (Mac only; no network needed)

```sh
mkdir -p ~/Downloads/pw3-r3877-35
unzip -oq ~/Downloads/pw3-r3877-35-compile-link-object-crosscheck.zip -d ~/Downloads/pw3-r3877-35
cd ~/Downloads/pw3-r3877-35
shasum -a 256 -c SHA256SUMS_R3877_35.txt
python3 -B -m unittest -q test_r3877_31.py test_r3877_32.py test_r3877_32_1.py test_r3877_32_2.py test_r3877_33.py test_r3877_33_1.py test_r3877_34.py test_r3877_35.py
set -o pipefail
python3 -B pw3_r3877_35_object_link_consistency.py ~/Downloads/pw3-r3877-30/musl-armv7-build.log | tee r3877_35_result.json
printf 'R3877_35_EXIT_CODE=%s\n' "$?"
```

A fully hash-consistent but *printed-text-only* result yields `PASS_PINNED_PRINTED_COMPILE_LINK_OBJECT_CROSSCHECK_ONLY`. Any failed pin, unparsable compile command, changed driver, unexpected count or missing log yields `HOLD` and exit code 2. The match totals in the real log remain unknown until the user runs this Mac-only audit.

## Safety boundaries

No Kindle SSH; no reading or writing raw partitions; no new binary execution; no Docker; no shell command evaluation; no firmware changes, installation, reboot or boot attempt. No source-to-binary rebuild. The public build log is not independently signed. PR #19 is research only and must remain unmerged unless explicitly instructed.
