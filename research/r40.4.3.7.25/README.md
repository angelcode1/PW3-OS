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
