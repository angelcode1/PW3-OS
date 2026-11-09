# R3877.88.2 — pinned Git-blob reference recovery (Mac-only)

**State:** User-reported `UPSTREAM_REFERENCE_PIN_MISMATCH` during R3877.88.2. No source diff has been performed; no Kindle access or stage edits. **HOLD / NOT_BOOTABLE**.

The R3877.88.2 auditor's reference pin is correct: `koreader/koreader` tag `v2026.07.2` → commit `9192014d8bd82a91dc1012473be0f238dedfdb54`, `frontend/ui/geometry.lua`, Git blob `dc8362ae455d3fddce2513865d340b482a9bdc53`, size **10,734 bytes**.

The file downloaded on the Mac is not available in evidence. Do not assume why the hash differed. Retain the old raw file for diagnosis and fetch a new independently pinned copy from the Git *blob API* instead of retrying the raw-content URL or changing the expected hash.

## macOS zsh command

Run from the existing `~/Downloads/pw3-r3877-88-2` directory (the R3877.88.2 package is already installed). This does not modify the existing R13 stage.

```zsh
cd ~/Downloads/pw3-r3877-88-2

curl --fail --show-error --silent --location --retry 0 \
  --connect-timeout 10 --max-time 40 \
  --header 'Accept: application/vnd.github+json' \
  --header 'User-Agent: PW3-OS-R3877-88-2' \
  'https://api.github.com/repos/koreader/koreader/git/blobs/dc8362ae455d3fddce2513865d340b482a9bdc53' \
  --output geometry-verified-gitblob-api.json

python3 - <<'PY'
import base64, hashlib, json
from pathlib import Path

pin = 'dc8362ae455d3fddce2513865d340b482a9bdc53'
previous = Path('geometry-v2026.07.2-upstream.lua')
def gitsha(buf):
    return hashlib.sha1(b'blob ' + str(len(buf)).encode() + b'\0' + buf).hexdigest()

if previous.is_file() and not previous.is_symlink():
    old = previous.read_bytes()
    print('PREVIOUS_RAW_REFERENCE_BYTES', len(old))
    print('PREVIOUS_RAW_REFERENCE_GIT_BLOB_SHA', gitsha(old))

doc = json.loads(Path('geometry-verified-gitblob-api.json').read_text())
assert doc.get('sha') == pin, 'API blob SHA mismatch'
assert doc.get('encoding') == 'base64', 'API response is not base64'
assert doc.get('size') == 10734, 'API reported unexpected size'
blob = base64.b64decode(''.join(doc['content'].split()), validate=True)
assert len(blob) == 10734, 'decoded size mismatch'
assert gitsha(blob) == pin, 'decoded blob did not match pinned source'

out = Path('geometry-v2026.07.2-from-gitblob-verified.lua')
if out.exists() or out.is_symlink():
    assert out.is_file() and not out.is_symlink() and out.read_bytes() == blob, 'refusing to overwrite nonidentical output'
else:
    with out.open('xb') as f:
        f.write(blob)
print('PINNED_GIT_BLOB_VERIFIED', len(blob), gitsha(blob))
PY

STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
setopt pipefail

python3 -B pw3_r3877_88_2_geometry_diff.py \
  --stage "$STAGE" \
  --upstream-geometry "$PWD/geometry-v2026.07.2-from-gitblob-verified.lua" \
  --acknowledge-readonly-two-file-diff \
  | tee r3877_88_2_pinned_retry.json

printf 'R3877_88_2_PINNED_RETRY_EXIT_CODE=%s\n' "$?"
```

**Expected:** The independent blob check prints `PINNED_GIT_BLOB_VERIFIED 10734 dc8362ae455d3fddce2513865d340b482a9bdc53`. R3877.88.2 still returns exit **2** because `NOT_BOOTABLE` is mandatory, but it should provide `review` and `hold_category=SOURCE_DIFF_DIAGNOSED_PIN_MISMATCH_ACTIVE` (unless the staged file unexpectedly matches upstream). Share only its JSON and terminal exit code. If the reference-pin error remains, also share the two `PREVIOUS_RAW_REFERENCE_` lines; do not publish the complete stage file.

If curl fails, stop. Do not execute R3877.87 or WidgetContainer on the Kindle, change the expected SHA, alter the stage file, or treat a raw-content download error as a true geometry change.
