# R40.4.3.7.53 — Alternate guest interpreter ELF32 ARM metadata preflight

**Research only; immutable NOT_BOOTABLE.** No original R13 rootfs changes, guest alias/mapping, ELF/QEMU execution, firmware write, boot or pruning.

## Reason for the change in direction
R3752 Mac results: 12 requester ELF objects, six direct providers, 18 targeted weak PLT sites, nine objects with a .plt anchor, zero dynamic relocation targets anywhere in their .plt sections, no DT_TEXTREL/DF_TEXTREL flags and zero word positions with a constant tested low-12-bit arithmetic relation to .plt or DT_PLTGOT. No raw-word comparison can by itself prove runtime weak-symbol or PLT resolver semantics.

The earlier R3726/R3727 Mac-stage baseline reported **12 requesters of one missing absolute PT_INTERP guest path** and exactly **one same-basename compatible ELF32 ARM header candidate** at a different regular-file path in the staged rootfs. Those observations do not prove the kernel-requested path exists or the alternate is a usable dynamic loader.

## R3753 read-only test
The downloaded Python script pins unchanged R3752, R3726 and R3727 code by exact SHA256, replays the 12-requester/one-alternative and R3752 parent baselines, retains the historical R3745 HOLD, and then checks only:
- Candidate ELF type (ET_DYN / ET_EXEC), ELF32 ARM header metadata, entry-point containment in an executable PT_LOAD, PT_LOAD W/X flags, PT_DYNAMIC, PT_INTERP, PT_TLS, GNU RELRO and GNU STACK.
- Candidate DT_NEEDED entry count; presence of SONAME, RPATH, RUNPATH, GNU/SysV hash, GNU version and text-relocation tags.
- ARM e_flags EABI version and soft/hard-float flag categories of **all 12 requesters** versus the candidate.

All file paths, symbol names, raw addresses, ELF flag values, words and DT_NEEDED literals stay private in memory. The emitted JSON contains only category names and aggregate counts. Equal EABI/e_flags header fields are not proof of runtime ABI compatibility; zero DT_NEEDED values do not establish complete self-containment. The guest interpreter path is still absent and no alias is created.

Host checks: **43 new + 618 inherited synthetic tests = 661/661 PASS**; clean-extract rerun PASS; 50 SHA256 manifest entries PASS; 51-member ZIP integrity PASS. Runnable code is **only in the conversation ZIP**, not separately published to GitHub. Mac stage run NOT EXECUTED. No GitHub Actions success claimed.

## macOS runbook (no git/gh)
Download `pw3-r3753-interpreter-candidate-abi-readonly.zip` into Downloads, then:
```sh
mkdir -p "$HOME/Downloads/pw3-r3753"
cd "$HOME/Downloads/pw3-r3753"
unzip -o "$HOME/Downloads/pw3-r3753-interpreter-candidate-abi-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043753-INTERPRETER-CANDIDATE-ABI-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send the JSON fields `candidate_type_category`, `candidate_entry_location_category`, `candidate_program_header_counts`, `candidate_dynamic_metadata`, `requester_candidate_eflags_relation_counts`. If a HOLD occurs preserve its category and do not modify source pins or stage.

## Outstanding
Original R26 provenance, historical inventory hashes, real guest PT_INTERP, kernel/runtime compatibility, full dependency resolution, weak symbol semantics, ARM TLS and safe boot/recovery remain unverified. OpenSSH/SFTP/rsync deferred to a separately validated image. **NOT_BOOTABLE.**
