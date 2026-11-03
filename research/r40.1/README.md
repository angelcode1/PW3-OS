# R40.1 — local immutable-stage / QEMU-path crosswalk

**2026-11-03: 42/42 host regressions PASS; user-side R40.1 stage reconciliation PENDING. NOT_BOOTABLE.**

Complete runnable source artifact: `pw3-os-r40.1-local-stage-crosswalk.zip`, SHA-256 `586a3b5731c830795939d029df0a626a8cbc140214e65cc7e17ef44567179e06`. It contains `r401/reconcile.py`, `tests/test_reconcile.py`, `README-R40.1.md`, `SHA256SUMS-R401`; ZIP CRC and all three payload SHA-256 hashes PASS. Python compile PASS.

The `r401/reconcile.py` script is committed separately at `research/r40.1/r401/reconcile.py`. The runnable ZIP and its test suite remain the source of truth for the host-tested release. It reads only local R40.0.2 private events, the SHA-pinned original **passing** R40 shareable summary and reviewer, and the local staged R13 `rootfs` tree. It never contacts a device or network, opens stage ELFs, follows stage symlinks, writes stage files, or uses privileged operations.

Exact required public R40 input SHA pins are `b8fdcf502fa791816430c528feae57237872932631a369b674f272352c3739e2` for `R40-SUMMARY.json` and `d23d2bf43d6995c9fee73dd096e081dfc934d3d82269b4ab36b556d394b9302f` for `R40-REVIEW.json`. Old R40.0.1 `FAIL` evidence is rejected. The complete local `trace/R40-PRIVATE-EVENTS.json` file is required and its event totals/counters must match the passing summary. **No private QEMU path or file name is returned to the assistant.**

Only unambiguous absolute paths rooted under the original trace mount `/stage/rootfs` are matched. Relative paths and escaped C-string syntax remain unresolved; `/proc,/sys,/dev` and disposable QEMU home are segregated. An observed successful `open/openat/execve` is distinguished from a successful metadata lookup and a failed lookup. **No absent file or failed lookup is classified as safe to remove.** Symlinks, special files and directories remain on hold. The output `R40.1-PRIVATE-CROSSWALK.json` is path-level and stays on the user's Mac; `R40.1-SUMMARY.json` contains path-free counts and explicit holds. The script refuses unsafe or preexisting outputs, overlaps and stage filesystem-crossing mounts.

This tool does not inspect or reconcile `R26-INVENTORY.json` yet. The 2,070-entry R26 count is for the prior stage inventory and cannot be assumed to match the `rootfs` subset without a fresh read. Full dynamic dependency closure still needs varied workloads, ELF/runtime dependencies, fonts, old-kernel ABI, Ink Away save scenarios, error paths and boot/hardware essentials.

## Mac run

```sh
cd "$HOME/Downloads"
SRC="$HOME/Downloads/pw3-os-r40.1-local-stage-crosswalk"
mkdir -p "$SRC"
unzip -q pw3-os-r40.1-local-stage-crosswalk.zip -d "$SRC"
cd "$SRC"
shasum -a 256 -c SHA256SUMS-R401
python3 -m unittest discover -s tests -q

python3 r401/reconcile.py \
  --stage "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --r40 "$HOME/Downloads/pw3-os-r40.0.2-split-first-run" \
  --private-out "$HOME/Downloads/R40.1-PRIVATE-CROSSWALK.json" \
  --summary-out "$HOME/Downloads/R40.1-SUMMARY.json"
```

Only share `R40.1-SUMMARY.json`; never upload `R40.1-PRIVATE-CROSSWALK.json`, the original private event file or raw QEMU logs. If the run refuses, preserve its original files and share only the generic refusal text.

**Immutable:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. Maintain all 976 `UNKNOWN_HOLD` stage entries. Research and educational purposes only.
