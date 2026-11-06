# R3762 corrected mixed-case public reference — read-only

**NOT_BOOTABLE.** This folder is a new, independently versioned corrected candidate. Do **not** replace or rewrite the historical R3762 release, its old checksums, or any private stage. This work is for research and education only.

## What changed

The original static `imx60_wario_defconfig` parser used `CONFIG_[A-Z0-9_]+` in both its enabled and explicitly-not-set option matchers. The pinned public file contains the **case-sensitive** key `CONFIG_VFPv3=y`, which that parser missed. That produced a false `REFERENCE_FEATURE_TABLE_DISAGREEMENT_HOLD`.

The corrected script changes exactly two regex character classes to `CONFIG_[A-Za-z0-9_]+`. Its new regression tests check the actual mixed-case key, disabled mixed-case options, incorrect uppercase substitution and duplicate conflict. The existing no-follow path checks remain unchanged. On macOS, testing must use a controlled temporary directory beneath a physical, symlink-free checkout path; the default `/var` temporary path may contain a symlink ancestor.

## Reproduction

From this directory (Python 3.9 or newer), run:

```sh
python3 - <<'PY'
from pathlib import Path
import hashlib
for record in Path('SHA256SUMS').read_text().splitlines():
    digest, file = record.split('  ', 1)
    assert hashlib.sha256(Path(file).read_bytes()).hexdigest() == digest, file
print('MANIFEST_PASS')
PY
mkdir -p .r3762-test-tmp
TMPDIR="$(pwd -P)/.r3762-test-tmp" TMP="$(pwd -P)/.r3762-test-tmp" TEMP="$(pwd -P)/.r3762-test-tmp" \
  python3 -B -m unittest discover -s . -p 'test_r4043762*.py' -v
python3 -B R4043762-PUBLIC-WARIO-KERNEL-REFERENCE-READONLY.py \
  --reference-defconfig "$(pwd -P)/imx60_wario_defconfig"
```

The expected test count is **36** and the successful real static-reference result is `PUBLIC_WARIO_KERNEL_CONFIG_REFERENCE_STATIC_ONLY`, with `tracked_reference_feature_disagreements=0` and `immutable_hold=NOT_BOOTABLE`. This is **not** device kernel verification.

## Candidate provenance and pins

The entire candidate file set is preserved from the user-provided ZIP. `SHA256SUMS` pins all six uploaded members; `R3762-COMPLETE-MIXEDCASE-FIX.patch` records the exact two-line source change. `VERIFY-RESULT.json` is the **original local report**, so `github_actions_run: false` is intentionally preserved even if a later workflow run passes.

- Corrected script SHA-256: `4a1f87c851072695f621522a56158b39e7ae3d9ff42a545073437cdafb8ae22f`.
- Original script SHA-256: `ece09d6b9c59e03d3fae8c8567fcb5255494b9a9fbd1e627c22e2f0500ca0690`.
- Pinned public reference: [katadelos/linux-3.0.35-lab126](https://github.com/katadelos/linux-3.0.35-lab126), commit `7ac2585f384573da8cbdcc987a3503e2e6ff1fb4`, file `arch/arm/configs/imx60_wario_defconfig`, Git blob `bbc2f92713d05dfd6ea52973fc7d958e49fa6464`, 59,582 bytes. The reference is from a community re-upload of Linux GPL sources and should be treated as GPL kernel-source reference material, **not** independent device-firmware authentication.

No Kindle device access, host/guest execution, firmware write, interpreter mapping, pruning or boot is permitted by this research artifact. Missing `CONFIG_TLS_REG_EMUL` and `CONFIG_KUSER_HELPERS` declarations are **not** proof that the corresponding runtime facilities are absent. The kernel ABI and TLS remain unverified. **NOT_BOOTABLE.**
