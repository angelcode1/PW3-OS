# R40.4.3.7.48 — Exact .plt offsets and numeric anchor reuse (read-only)

Research and educational purposes only. **NOT_BOOTABLE**. Original R13 stage unchanged.

User-reported R3747 Mac audit found 18 weak R_ARM_JUMP_SLOT unrelocated original words in the first 16 bytes of their respective .plt sections across nine requester ELFs. Each exposed three file-backed A32 encoding-field words with the same coarse categories. No runtime pointer, stub or dynamic loader interpretation has been established.

R3748 is a separate SHA-pinned read-only program that replays R3747 and its predecessor chain, including the R3745 historical parser HOLD, and checks the exact **relative byte offset within each .plt section**: 0, 4, 8 or 12. It also counts whether original slot words reuse the same numeric .plt anchor within a requester, including across distinct weak-symbol groups. It never compares virtual addresses across unrelated objects, exports addresses/words/symbols/paths, decodes instructions, applies relocations or modifies the stage.

**Host verification:** 40 new plus 360 inherited synthetic tests PASS, including clean-extraction rerun; ZIP integrity and 40-file SHA256SUMS manifest PASS. The runnable tool, pinned predecessors, tests and matching checksums are distributed only in the conversation ZIP `pw3-r3748-plt-anchor-reuse-readonly.zip` (41 archive members, SHA256 `54a58eaf1e41b1c4fb5c00e44ca7366f0b478da9dcffedede102fb7f76febc29`). Full runnable source has NOT been published in this GitHub research directory; no GitHub Actions PASS is claimed.

## macOS runbook (no git/gh)
Download ZIP to Downloads:

```sh
mkdir -p "$HOME/Downloads/pw3-r3748"
cd "$HOME/Downloads/pw3-r3748"
unzip -o "$HOME/Downloads/pw3-r3748-plt-anchor-reuse-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043748-PLT-ANCHOR-REUSE-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send result JSON, particularly `candidate_dot_plt_relative_offset_categories_by_group`, `requester_numeric_anchor_alias_categories`, and `targeted_weak_plt_sites`.

No runtime weak-symbol semantics, lazy binding, loader namespace, ARM TLS, kernel ABI, original R26 source provenance, historical hashes, guest interpreter path, image recovery or boot authorization proven. No guest alias, firmware writes, ELF execution, pruning, or staged file modifications. **NOT_BOOTABLE.**
