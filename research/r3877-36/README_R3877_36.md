# PW3 R3877.36 — Pinned musl build-log extra compile-output triage

**Research and educational use only. Immutable safety hold: `NOT_BOOTABLE`.**

## Established R3877.35 baseline

The user reported `PASS_PINNED_PRINTED_COMPILE_LINK_OBJECT_CROSSCHECK_ONLY`, exit code 0: all 1,423 object-like inputs in the printed two-line musl libc link candidate matched *exactly* 1,423 distinct printed compile outputs; five other distinct compile output strings were not present as object inputs in that candidate. Both the 1,644,394-byte build log and the 40,671-character two-line link candidate were SHA-256 pinned. This is a textual audit of a public, **unsigned** build log—not historical executed argv, toolchain provenance, or proof of actual object files.

## What R3877.36 does

1. Re-run the full R3877.35 hash-pinned input and count checks. Require 1,428 compile outputs, 1,423 matched link objects, zero missing link objects, and exactly **five** compile outputs not present in the *main* link candidate.
2. Identify those five output strings in memory without reporting their raw paths, basenames or hashes. Aggregate only safe source suffix classes (`.c`, `.S`, `.s`, etc), output suffix classes (`.o`, `.lo`), allowlisted compile flags, and whether their compile lines appeared before/after the printed main link.
3. Tokenize other bounded physical log lines **without shell evaluation** and count only *exact full-token* mentions of the five strings. Group other-line contexts coarsely as archive-tool-like, compiler/linker-like, copy/install-tool-like, or other. Exclude the producing compile lines and both main link lines from this classification.
4. Report skipped/unparsable other lines. Absence of other full-token mentions never proves an artifact was unused.

No command execution, Docker activity, Kindle SSH, raw path output or firmware interaction occurs. An object compiled but not present in *this one* linker candidate may be legitimate startup/helper/other-target material; it is not proof of a missing object or broken package.

## Run on Mac

Use the previously downloaded R3877.30 public log exactly as before:

```sh
mkdir -p ~/Downloads/pw3-r3877-36
unzip -oq ~/Downloads/pw3-r3877-36-unlinked-compile-triage.zip -d ~/Downloads/pw3-r3877-36
cd ~/Downloads/pw3-r3877-36
shasum -a 256 -c SHA256SUMS_R3877_36.txt
python3 -B -m unittest -q test_r3877_31.py test_r3877_32.py test_r3877_32_1.py test_r3877_32_2.py test_r3877_33.py test_r3877_33_1.py test_r3877_34.py test_r3877_35.py test_r3877_36.py
set -o pipefail
python3 -B pw3_r3877_36_unlinked_compile_triage.py ~/Downloads/pw3-r3877-30/musl-armv7-build.log | tee r3877_36_result.json
echo "R3877_36_EXIT_CODE=$?"
```

Expected success classification, conditional on real input: `PASS_PINNED_UNLINKED_PRINTED_COMPILE_OUTPUT_TRIAGE_ONLY`. Any unexpected input, path or count returns exit code 2 and `HOLD` rather than fabricating evidence. No private output filenames or other source tokens appear in the JSON.

## Remaining provenance gaps

Historical compiler/linker executable versions, complete CFLAGS/LDFLAGS and shell invocation, machine identity and immutable signed build-log evidence are still unverified. The signed APK loader has not been rebuilt from the patched source. Target PW3 kernel dispatcher and runtime safety, recovery, original R13 build provenance and any deployment readiness are unverified. Keep `NOT_BOOTABLE`.
