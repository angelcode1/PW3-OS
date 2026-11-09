# R3877.90.1 — SSH 255 triage, no LuaJIT execution

**Status:** Local package prepared, synthetic host tests 20 PASS; physical Kindle inspection **NOT RUN**. User-reported R3877.90 had 12 planned cases, offline source and ELF checks PASS, SSH exit **255**, **106 stderr bytes**, no parseable stdout, and tmpfs cleanup unconfirmed. The batch parser's `REMOTE_OUTPUT_SIZE_OR_TERMINATOR_INVALID` is secondary to the SSH transport failure; it does not prove an application failure.

Source package **`pw3-r3877-90-1-ssh-inventory.zip`** is attached to this ChatGPT conversation, not committed as individual Python files in this documentation commit.

The new runner `pw3_r3877_90_1_ssh_inventory.py` has **read-only** modes only:
- `--review-only`: no SSH.
- `--acknowledge-readonly-ssh-inventory`: one SSH attempt, no tar/LuaJIT transfer. Inspect `uname`, `/proc/mounts` and existence of matching `pw3-r3877-90-*` directories on pre-existing tmpfs `/tmp`, `/run`, `/dev/shm`.
- `--ssh-debug --private-ssh-stderr ABSOLUTE_PATH`: optional local 0600 exclusive file containing raw SSH negotiation details; **do not publish this private log**. Public JSON carries only diagnostic category, SHA256, stderr length and matching-directory counts.

The tool **always** returns `HOLD / NOT_BOOTABLE` exit 2, including after a successful inventory. No cleanup is performed; if residues are found, investigate separately before restarting any native run. A zero count does not prove historical cleanup in all circumstances.

### macOS

```zsh
cd ~/Downloads
unzip -oq pw3-r3877-90-1-ssh-inventory.zip -d ~/Downloads
cd ~/Downloads/pw3-r3877-90-1
shasum -a 256 -c SHA256SUMS_R3877_90_1.txt
python3 -B -m unittest -q test_r3877_90_1.py
python3 -B pw3_r3877_90_1_ssh_inventory.py --review-only
setopt pipefail
python3 -B pw3_r3877_90_1_ssh_inventory.py \
  --acknowledge-readonly-ssh-inventory \
  --target root@192.168.8.102 --port 2222 \
  --ssh-debug \
  --private-ssh-stderr "$PWD/r3877_90_1_ssh_stderr_PRIVATE.log" \
  | tee r3877_90_1_inventory.json
printf 'R3877_90_1_EXIT_CODE=%s\n' "$?"
```

The original 106 stderr bytes were discarded by R90 and cannot be recovered from its JSON. Do not infer their contents. Do not run the full R90 batch again until the new SSH inventory and cleanup uncertainty are reviewed.

**Future code requirement:** teach R90's output parser to handle SSH exit 255 before case-log parsing; preserve per-case logs only if fully received, and keep the entire 12-case batch rather than returning to individual module tests. No GUI, device hardware or independent boot is authorized.
