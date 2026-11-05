# R40.4.3.7.47 — Read-only ARM PLT encoding-field prefix audit

**Research only. NOT_BOOTABLE.** Original Mac R13 staged rootfs remains unchanged. The runnable source and tests are in the conversation ZIP, not standalone GitHub files.

## User Mac R3746 evidence

The user reported 18 weak R_ARM_JUMP_SLOT sites from nine requesting objects. The original file-backed slot words are nonzero, A32 word aligned, and numerically fall in executable .plt sections of their own source ELF. Nine sites reuse a numeric candidate within requester/group; nine use an unrepeated candidate. All 12 requesting objects have DT_PLTGOT in writable load memory. This does not establish that a word is a valid code pointer, PLT stub or functioning lazy binder. Original R3745 parser HOLD remains historically recorded.

## R3747 diagnostic

The new tool pins exact original R3746 SHA256 `9b852e291c482a50c8c07585941ec10c1abc59e48c8ae94d0fb018bc03e14f87`, replays the R3746 stage baseline and inherited source SHA chain, then reads at most three complete 32-bit words **within** each numeric target's bounded file-backed .plt section. It counts only coarse A32 encoding **field patterns** and section-position/window availability categories. This is **not** disassembly, valid instruction verification, dynamic symbol resolution, or a runtime loader test. No paths, addresses, words, names or bytes are reported. No ELF execution, symlink creation, image write, QEMU, firmware, boot or pruning.

**Locally verified:** 26 new synthetic tests + 334 inherited synthetic tests = **360/360 PASS**. Clean extraction, SHA256 checksum manifest and 39-member ZIP integrity PASS. No user Mac stage result or GitHub Actions pass has been verified for R3747.

The full self-contained user-conversation archive is `pw3-r3747-arm-plt-prefix-readonly.zip`, SHA256 `e6e95c0a34ba8695194ce0430d5f3c24f96462e403d9bb6456e2e0c409618d13`. It contains the source, regression tests, predecessor scripts, README, release status, 38-file SHA256SUMS and a sample host-only workflow. Example workflow is not installed/verified in GitHub Actions.

## macOS (no git or gh)

Download the ZIP into `~/Downloads`, then:

```sh
mkdir -p ~/Downloads/pw3-r3747
cd ~/Downloads/pw3-r3747
unzip -o ~/Downloads/pw3-r3747-arm-plt-prefix-readonly.zip
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043747-ARM-PLT-WORD-PREFIX-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send the JSON, especially `candidate_plt_prefix_categories_by_group` and `targeted_weak_plt_sites`. If HOLD, do not change pins or source. Original R26 provenance, historic file hashes, guest PT_INTERP, runtime namespace, ARM TLS and recovery remain unresolved. OpenSSH/SFTP/rsync are deferred to an independently validated future image. **NOT_BOOTABLE.**

Reference: Arm Architecture Reference Manual, A32 top-level encoding field categories: https://support.arm.com/documentation/ddi0406/c/Application-Level-Architecture/ARM-Instruction-Set-Encoding/ARM-instruction-set-encoding
