# PW3 R3877.37 — Five extra printed musl objects: command-family context

**Research and educational use only. Immutable hold: `NOT_BOOTABLE`.**

## Input and provenance

Use the already-downloaded Alpine 3.24 ARMv7 `musl-1.2.6-r3` public builder log from R3877.30. The audit uses the earlier pinned SHA-256:

`a8405a50c1849aebc0fefadcab4e4f7fa7da27d9c1296fa2ce46b73df56ca2ce` (1,644,394 bytes).

Reported R3877.36: 1,428 printed compile outputs, 1,423 objects in the printed main link candidate, five exact unmatched compile outputs, all five mentioned as full tokens elsewhere in the log, with five mentions categorized broadly as `copy_install_or_binary_tool_like`. One other log line did not parse and remains an explicit visibility limit. **The signed-musl-source/tree and public build-log signature are not authenticated as executed build commands.**

## What R3877.37 checks

- Run the existing R3877.36 chain first, preserving log SHA-256, two-line link-candidate hash and the 1,428:1,423:5 object mapping.
- Re-identify the exact five omitted compile outputs **privately**; tokenize printed non-compile, non-main-link lines without executing/evaluating them.
- Classify exact full-token mentions by conservative command families (`copy`, `install`, `move`, `binary_tool`, `archive`, `compiler_or_linker`, `other_or_unresolved`) and possible argument-position roles. Counts are candidate printed-text evidence, not evidence of commands executed or files copied.
- Report only aggregate counts; never reveal raw commands, tokens, paths, basenames, object-specific digests or the public log itself. Preserve visibility limit for the one unparsed printed line.

The categorization **cannot establish historical machine/compiler identity, full build flags, original executed argv, signed loader source-to-binary reproducibility, Kindle Linux 3.0.35 runtime compatibility, backups or recovery**.

## Mac commands

```sh
mkdir -p ~/Downloads/pw3-r3877-37
unzip -oq ~/Downloads/pw3-r3877-37-extra-object-context.zip -d ~/Downloads/pw3-r3877-37
cd ~/Downloads/pw3-r3877-37
shasum -a 256 -c SHA256SUMS_R3877_37.txt
python3 -B -m unittest -q test_r3877_31.py test_r3877_32.py test_r3877_32_1.py test_r3877_32_2.py test_r3877_33.py test_r3877_33_1.py test_r3877_34.py test_r3877_35.py test_r3877_36.py test_r3877_37.py
set -o pipefail
python3 -B pw3_r3877_37_auxiliary_context_audit.py ~/Downloads/pw3-r3877-30/musl-armv7-build.log | tee r3877_37_result.json
printf 'R3877_37_EXIT_CODE=%s\n' "$?"
```

Expected successful classification (if real log hashes and counts reconcile): `PASS_PINNED_FIVE_EXTRA_OBJECT_PRINTED_CONTEXTS_ONLY`. Otherwise `HOLD`, exit 2. A synthetic regression pass is **not** a real-log pass.

## Follow-on decision

Use the command-family and role counts to assess whether the five extra objects are *consistent* with auxiliary outputs. If classification is unresolved, do not silently assume use. No Kindle operations; **NOT_BOOTABLE**.
