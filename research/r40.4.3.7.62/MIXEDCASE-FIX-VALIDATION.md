# R3762 — mixed-case Kconfig parser correction (host candidate)

**Research/educational only.** The original R3762 release remains unchanged. This record describes a user-tested **local** corrected candidate, not a verified GitHub-hosted build. `NOT_BOOTABLE` is immutable. No device access, guest execution, firmware writes, interpreter mapping, pruning, or source-stage modification is authorized.

## Root cause

The original R3762 parser only accepted `CONFIG_[A-Z0-9_]+` in the positive and "is not set" regexes. This omitted the actual pinned public Linux config key `CONFIG_VFPv3=y` because the lowercase `v` is significant in the spelling of the key.

The resulting false `NOT_DECLARED` classification yielded `REFERENCE_FEATURE_TABLE_DISAGREEMENT_HOLD` even though the Git blob and 23 documented feature expectations matched.

**Proposed minimal source change (two existing tokens only):**

```text
r'^(CONFIG_[A-Z0-9_]+)=(.*)$'             -> r'^(CONFIG_[A-Za-z0-9_]+)=(.*)$'
r'^# (CONFIG_[A-Z0-9_]+) is not set$'  -> r'^# (CONFIG_[A-Za-z0-9_]+) is not set$'
```

Do **not** uppercase `CONFIG_VFPv3` or relax `read_nofollow()`. Its full symlink-ancestry rejection correctly blocked fixtures under the macOS `/var` symlink. For host tests, use a controlled `TMPDIR` beneath a physically resolved, symlink-free path instead.

## User-reported local validation — 2026-11-06

The user ran the two-regex corrective preparation against the original pinned scripts and the public source reference. The resulting console output reports:

| Gate | User-reported result |
| --- | --- |
| Original source SHA-256 | Verified `ece09d6b9c59e03d3fae8c8567fcb5255494b9a9fbd1e627c22e2f0500ca0690` |
| Original test SHA-256 | Verified `0ad8acfb236028239d426963a7a54c88ac0b84681935ae67ab6d4271af16b636` |
| Public reference Git blob SHA-1 | Verified `bbc2f92713d05dfd6ea52973fc7d958e49fa6464` |
| Source changes | Two regexes: positive + explicitly-disabled options |
| Real reference audit | `PUBLIC_WARIO_KERNEL_CONFIG_REFERENCE_STATIC_ONLY` |
| Tests | 36 / 36 PASS (32 original + 4 new synthetic regressions) |
| Candidate corrected source SHA-256 | `4a1f87c851072695f621522a56158b39e7ae3d9ff42a545073437cdafb8ae22f` |
| Original locally modified? | No |
| Immutable restriction | `NOT_BOOTABLE` |

Candidate generated on the user's Mac at `~/Downloads/pw3-r3762-complete-mixedcase-candidate/`. The candidate's `R3762-COMPLETE-MIXEDCASE-FIX.patch`, `VERIFY-RESULT.json`, `SHA256SUMS`, corrected Python source, original test and regression test are **not yet committed in this branch**, because they currently exist only on the user's Mac and have not been provided as file contents to the GitHub connector. Their existence and checksums are **reported by the local run** and not GitHub-verified.

## Publication gate still open

1. Import the exact local candidate files, preserving their checked hashes, to a **new** versioned repository path (do not overwrite the historical R3762 release).
2. Verify source hash `4a1f87c851072695f621522a56158b39e7ae3d9ff42a545073437cdafb8ae22f`, reference Git blob, patch scope, and manifest against the committed bytes.
3. Add or enable CI against the committed Python source and regressions; collect an actual GitHub Actions result before claiming CI PASS.
4. Keep all original `NOT_BOOTABLE`, no-device, no-execution, no-firmware-write, and no-prune constraints unchanged. A public defconfig is **not** the actual running PW3 kernel configuration.

**Status:** `LOCAL_CANDIDATE_VERIFIED_USER_REPORT; GITHUB_SOURCE_PUBLICATION_PENDING; GITHUB_CI_NOT_RUN; NOT_BOOTABLE`.
