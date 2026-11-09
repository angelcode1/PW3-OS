# PW3 R3877.42 — Historical toolchain clue triage

**Static research only. Immutable `NOT_BOOTABLE` hold.**

## Basis
The user's R3877.41.1 Mac result passed for a pinned signed Alpine musl loader,
historical `APKBUILD` Git blob, and unsigned public ARMv7 build log.
The ELF carries ARMv7 EABI5 hard-float markers but no `.comment` or DWARF
compiler-version evidence. Printed linker argv includes `cc` and no explicit
`-mfloat-abi=` switch. This is not proof of the effective compiler defaults.

## New R3877.42 local research tool
The separately distributed, offline-tested
`pw3-r3877-42-toolchain-textual-evidence.zip` contains:
- `pw3_r3877_42_toolchain_textual_evidence.py`
- `test_r3877_42.py`
- earlier R3877.41 offline test and analyzer dependencies
- an SHA-256 manifest and local runbook.

Run using existing Mac-local inputs:
```sh
cd ~/Downloads/pw3-r3877-42
shasum -a 256 -c SHA256SUMS_R3877_42.txt
python3 -B -m unittest -q test_r3877_41.py test_r3877_42.py
set -o pipefail
python3 -B pw3_r3877_42_toolchain_textual_evidence.py \
  --r41-report ~/Downloads/pw3-r3877-41-1/r3877_41_1_result.json \
  --log ~/Downloads/pw3-r3877-30/musl-armv7-build.log \
  | tee r3877_42_result.json
echo "R3877_42_EXIT_CODE=$?"
```

Expected pass category **only if** both actual files meet pins:
`PASS_PINNED_PRINTED_TOOLCHAIN_VERSION_CLUE_TRIAGE_ONLY`.

R3877.42 categorizes explicit version-banner text, package-version
references, printed probe commands and ARM-ABI switch text. These clues
are not authenticated evidence of the historical builder's installed
compiler/binutils/abuild versions, command execution, flags or machine.
The unsigned log remains unsigned. No source-to-binary reproducibility
or PW3 vendor kernel runtime compatibility is claimed.

## Publishing status
The successful R3877.41.1 selected evidence and this runbook are in the
research branch; the R3877.42 analyzer/tests remain in the independent
downloadable ZIP and are **not** asserted to have GitHub CI coverage yet.
Research PR #19 remains unmerged.
