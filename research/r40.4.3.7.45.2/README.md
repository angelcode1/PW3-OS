# R40.4.3.7.45.2 — Correct R3745 parent-module chain (read-only)

**Research and educational purposes only. NOT_BOOTABLE.**

## Exact defect confirmed on user Mac

Original R3745 returned `HOLD` / `UNEXPECTED_STATIC_PARSER_HOLD`. R3745.1 located
an `AttributeError` in original `R3745.audit()` at line 192. The code used
`p42 = p43.load_pinned_parent(folder)` although the pinned R3743.1 module
`p43` has `load_original(folder)`, **not** `load_pinned_parent`.

This release is **independent** of the original script and corrects only the
parent walk:

```python
original43 = p43.load_original(folder)           # pinned original R3743
p42 = original43.load_pinned_parent(folder)     # pinned R3742
```

The original R3745 script remains SHA-pinned and unchanged
(`c3b95955df80e896196887fe922acd253d26948728939f1ea8349782feb73794`),
and its HOLD remains historical evidence. R3745.2 requires the exact original
SHA **before** performing the stage audit. It continues to replay unchanged
R3744 and earlier pinned checks. No structural/ABI/weak-reference restrictions
are relaxed and no symbol is treated as resolved.

## Tests and interpretation

Synthetic regression reproduces the original `AttributeError`, demonstrates
R3745.2 reaches the old PLT audit with the correct parent chain, checks exact
source pins, unchanged safety holds and no names/paths in output. **298 synthetic
tests pass** (22 new, 276 inherited). A synthetic PASS is *not* a real Mac
stage audit or a Kindle boot check.

R3745.2 will examine 18 unrelocated PLT/GOT slot words of the previously
held 44 weak referenced entries. It classifies their original word geometry
relative to the referencing ELF's PT_LOAD segments, low-bit state and
DT_PLTGOT segment location. Neither apparent executable-segment containment
nor a likely PLT trampoline proves lazy binding, runtime weak semantics,
interpreter resolution, kernel ABI or runtime functionality.

## Mac commands — no git or gh

Download `pw3-r3745-2-pinned-plt-callchain-fix-readonly.zip` into `~/Downloads`,
then run:

```sh
mkdir -p "$HOME/Downloads/pw3-r3745-2"
cd "$HOME/Downloads/pw3-r3745-2"
unzip -o "$HOME/Downloads/pw3-r3745-2-pinned-plt-callchain-fix-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043745-2-PINNED-PLT-CALLCHAIN-FIX-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send `result`, `targeted_weak_plt_sites`, `weak_plt_initial_target_categories_by_group`
and `requester_dt_pltgot_categories` (or a new HOLD category if returned).
Do not change pinned scripts or the source stage to force a pass.

**No rootfs writes, symlink creation, ELF execution, QEMU, Kindle access,
firmware writing, boot or pruning.** Original R26 provenance, historical
hashes, dynamic loader lookup, ARM TLS, image recovery and full dependency
closure remain held; OpenSSH/SFTP/rsync remain deferred. **NOT_BOOTABLE.**
