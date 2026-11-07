# PW3 R3877.34 — Two-line printed linker-candidate structural audit

**Research/educational use only. The immutable hold remains `NOT_BOOTABLE`.**

## Why this exists

R3877.33.1 established, on the user's Mac, that two adjacent physical lines of the public Alpine 3.24 ARMv7 musl `1.2.6-r3` build log form a Python `shlex`-tokenizable **printed candidate**. The candidate contains 1,494 tokens and 40,671 characters. The first line ends with a shell-style unpaired backslash; the second does not. Neither a public build log nor `shlex` output attests that a historical shell actually executed that exact command.

The R3877.34 diagnostic builds on the hash-pinned earlier audits and verifies the first printed line, the full neighboring line and the joined text against the user-reported SHA-256 values. It classifies safe token *types* (object-like inputs, static archives, libraries, output-option shape and linker flags), not the actual input names, paths or raw command. It does **not** run `cc`, a shell, ARM binaries, Docker, SSH or anything on Kindle.

## Run on Mac

Use the **existing** `~/Downloads/pw3-r3877-30/musl-armv7-build.log` file:

```sh
mkdir -p ~/Downloads/pw3-r3877-34
unzip -oq ~/Downloads/pw3-r3877-34-link-candidate-structure.zip -d ~/Downloads/pw3-r3877-34
cd ~/Downloads/pw3-r3877-34
shasum -a 256 -c SHA256SUMS_R3877_34.txt
python3 -B -m unittest -q test_r3877_31.py test_r3877_32.py test_r3877_32_1.py test_r3877_32_2.py test_r3877_33.py test_r3877_33_1.py test_r3877_34.py
set -o pipefail
python3 -B pw3_r3877_34_pinned_link_structure.py ~/Downloads/pw3-r3877-30/musl-armv7-build.log | tee r3877_34_result.json
printf 'R3877_34_EXIT_CODE=%s\n' "$?"
```

Successful hash-pinned, structurally classified source evidence yields `PASS_PINNED_TWO_LINE_LINK_CANDIDATE_STRUCTURE_ONLY`. The entire 1.64 MB log must match its pinned length and SHA-256 before the candidate is accepted. Any changed log line, mismatched token count or lexical failure yields a `HOLD` and nonzero exit.

## Important limitations

- `shlex` parses quoted textual words, **not shell grammar** or shell expansions; the candidate may contain printed shell syntax, expansion markers or log artifacts.
- Neither a lexically complete candidate nor one `-o` output switch proves historical compiler/linker identity, complete `CFLAGS/LDFLAGS`, original builder versions, machine identity or actual executed argv.
- Only names of a *small fixed allowlist of flags* are emitted. Paths, output basenames, input basenames and raw tokens are not emitted; only integer counts and pinned hashes are included.
- No rebuild occurs and no claim of byte-identical reproducibility or Kindle runtime compatibility is made.
- The public log's signature has not been independently verified. The historical toolchain is still unpinned.

## Next gate

Depending on this structural result, a later host-only study may compare token-class counts to object inventories from the pinned musl 1.2.6 source or identify historical builder environment data. The Kindle `NOT_BOOTABLE` hold remains in force until recovery and boot requirements are independently satisfied.
