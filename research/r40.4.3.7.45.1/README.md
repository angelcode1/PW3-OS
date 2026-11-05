# R40.4.3.7.45.1 — original R3745 unexpected parser failure triage

**Research/education, host only, strictly read-only. `NOT_BOOTABLE`.**

The original R3745 Mac-stage run returned `HOLD` and `UNEXPECTED_STATIC_PARSER_HOLD` (recorded at `research/r40.4.3.7.45/USER-MAC-AUDIT-RESULT.json`). The original R3745 catches all otherwise unrecognized exceptions in its final handler, hiding whether this was a Python bug or an upstream pinned `Hold`. This result is not proof of a malformed ELF, loader failure or successful weak binding.

## What changed

This **separate** R3745.1 diagnostic SHA-256 checks the exact unchanged R3745 source (`c3b95955df80e896196887fe922acd253d26948728939f1ea8349782feb73794`) and invokes the original audit body, without invoking its broad `main()` exception handler. All prior source pins remain in the original audit. If it raises, this new tool reports only:

- the exception **class**, allowlisted or `OTHER_EXCEPTION_CLASS_REVIEW`;
- a safe constant-code HOLD category, if one exists;
- up to six fixed, allowlisted R3726–R3745 **source module IDs**, function names and *source line numbers* from the original pinned code.

It **never prints** the exception message, Python traceback, host filesystem path, raw ELF bytes, symbol/library name, guest path or any original address/value. It does not inspect exception strings for logic. If the original failure cannot be reproduced, it retains a `HOLD` rather than declaring resolution. Any new original behavior remains on hold for investigation.

This diagnostic does **not fix a parser error** or prove loader compatibility. It provides the safe first failing source location for a later narrowly tested correction. The previous R3741 local-version HOLD and R3743 overlap HOLD remain preserved.

## Mac command, no git or gh

Download `pw3-r3745-1-static-parser-failure-triage-readonly.zip` into `~/Downloads`:

```sh
mkdir -p "$HOME/Downloads/pw3-r3745-1"
cd "$HOME/Downloads/pw3-r3745-1"
unzip -o "$HOME/Downloads/pw3-r3745-1-static-parser-failure-triage-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043745-1-STATIC-PARSER-FAILURE-TRIAGE-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Expected local synthetic regressions: **276 tests**, including **23 new** tests and **253** inherited. If the diagnostic returns `HOLD`, preserve the category and do not weaken source pins or change original files to force a PASS. Send the JSON output with `exception_class`, `pinned_parent_hold_category`, `last_pinned_frame` and `pinned_call_frames`.

## Safety holds

The staged interpreter guest path is absent and the proposed alias has not been applied. Actual ARM ELF runtime symbol interposition, weak binding, TLS, Linux 3.0.35 compatibility, R26 provenance, historic inventory hashes and dependency closure are unverified. No stage/rootfs writes, no symlink creation, relocation or weak zero substitution, ELF/QEMU execution, physical PW3 access, firmware write, boot or pruning. OpenSSH/SFTP/rsync remain deferred to a separately validated final image. **`NOT_BOOTABLE`.**

## User Mac diagnostic — confirmed parser bug

R3745.1 returned `ORIGINAL_R3745_FAILURE_SITE_CLASSIFIED_ONLY`, `AttributeError`, originating at `audit` line 192 in original R3745. That line erroneously invokes `p43.load_pinned_parent(folder)` where `p43` is the R3743.1 module; the latter exports `load_original`, not `load_pinned_parent`. The correct module chain goes via `p43.load_original(folder).load_pinned_parent(folder)`. This is an implementation defect, **not** evidence of a rejected ARM ELF layout or symbol failure. Original R3745 source and its historical `UNEXPECTED_STATIC_PARSER_HOLD` are unchanged. R3745.2 is a separately pinned corrective diagnostic with regression tests. See `USER-MAC-AUDIT-RESULT.json`. Stage remains unmodified; **NOT_BOOTABLE**.
