# R40.4.3.7.25 — staged rootfs inventory count reconciliation

**Host-only, read-only, independently enumerated file-type audit; NOT_BOOTABLE.**

The user-reported R3724 run classified 83 ELF objects with 19 interpreter segments (9 strict and 10 trailing-NUL-padding candidates). However, the standalone scan counted 1,446 regular files, whereas the older R3721/R3722 source-pinned stage baseline reported 1,448. Until these counts are reconciled against the original pinned inventory, full-file coverage is **not proven**.

This utility checks physical file types twice, using separate `os.scandir` and `os.walk` traversals, without following symlinks or printing paths. It counts symlink entry types but **does not resolve symlinks or guest loader paths**. `STANDALONE_INVENTORY_COUNTS_MATCH` means that the two enumeration methods agree with the supplied expected regular-file count; it does **not** mean SHA-pinned inventory membership or provenance was verified.

On the user's Mac, with no `git`/`gh` required, download the script into `~/Downloads/pw3-r3725` and run:

```sh
python3 -m unittest discover -s "$HOME/Downloads/pw3-r3725" -p 'test_*.py' -v
python3 "$HOME/Downloads/pw3-r3725/R4043725-INVENTORY-COUNT-READONLY.py" \
  --stage-root "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --expected-regular-files 1448
```

If the result is `INVENTORY_COUNT_GAP_HOLD`, the next step is to compare the **original R26 source-pinned file manifest** with the present stage. Do not guess two missing filenames, treat symlinks as regular files, modify the stage to force a count, boot, flash, delete files or prune. No Python packages, QEMU, device connection or firmware access are needed. Existing authenticity, runtime resolution, dependency and hardware holds remain. **NOT_BOOTABLE.**

## Mac result and baseline scope correction

The Mac user reported `OK` and ran R3725 on `stage-r13-fixed/rootfs`. Both independent scanners agreed: **1,446 regular files, 286 directories, 335 symlinks, no other nodes**. This produced `INVENTORY_COUNT_GAP_HOLD` against 1,448.

**Root cause of the apparent difference:** the original R26 stage inventory and corrected R3721.1 membership gate explicitly count the **enclosing `stage-r13-fixed` directory**, including the `rootfs/` entry and non-rootfs metadata files. The original enclosing-stage baseline is **1,448 regular files + 287 directories + 335 symlinks = 2,070 entries**, not a rootfs-only inventory. The user’s rootfs-only values sum to 2,067, differing by precisely **two regular files and one directory**. No claim is made yet about the actual outer-stage run; the scope hypothesis must be verified using the command below.

No download, Git, or GitHub CLI is required; reuse the existing audited R3725 script, pointing at the **parent** directory rather than rootfs:

```sh
python3 "$HOME/Downloads/pw3-r3725/R4043725-INVENTORY-COUNT-READONLY.py" \\
  --stage-root "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \\
  --expected-regular-files 1448
```

Expected if scope is the entire explanation: `STANDALONE_INVENTORY_COUNTS_MATCH`, 1,448 regular files, 287 directories and 335 symlinks. This is **not** a new R26 signed inventory/hash recheck, source authentication, runtime loader resolution, dependency closure, or permission to boot/prune; `NOT_BOOTABLE` remains unchanged.
