# R3877.40.1 — Signed loader input recovery succeeded (reported Mac evidence)

**Research only; immutable `NOT_BOOTABLE`.** The R3877.40.1 resolver found one SHA-256 pinned musl APK, one pinned cached loader, one public index candidate whose SHA-256 matched the earlier index, and a pinned Alpine key directory.

The user's actual Mac run returned `PASS_VERIFIED_LOCAL_INPUT_RESOLUTION_AND_R3877_40_ONLY` with exit code 0. Its invocation of R3877.40 returned `PASS_PINNED_SIGNED_LOADER_STATIC_ELF_METADATA_ONLY` with exit code 0.

This is a **selected, user-reported wrapper result**. The original `r3877_40_result.json` ELF inventory was not supplied. It cannot be used to assert any specific `.comment` version, ARM attribute, e_flags value, or GNU build-ID, and does not verify the historical compiler, builder identity, build flags, source-to-binary reproducibility or Kindle runtime compatibility.

The original host-only R3877.40 and R3877.40.1 Python implementations and tests were distributed in the corresponding earlier downloadable diagnostic ZIPs. This commit records only the result and a source-independent evidence gate.

To inspect the already generated ELF inventory safely on the Mac:

```sh
cd ~/Downloads/pw3-r3877-40-1
python3 - <<'PY'
import json
from pathlib import Path
p=Path('r3877_40_result.json')
if not p.is_file() or p.is_symlink():
    raise SystemExit('HOLD: existing R3877.40 result file unavailable')
d=json.loads(p.read_text(encoding='utf-8'))
assert d.get('result')=='PASS_PINNED_SIGNED_LOADER_STATIC_ELF_METADATA_ONLY'
assert d.get('immutable_hold')=='NOT_BOOTABLE'
assert d.get('inventory',{}).get('candidate_loader_matches_signed_public_loader') is True
print(json.dumps(d['inventory'].get('static_elf', {}),sort_keys=True,indent=2))
PY
```
