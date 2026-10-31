# Read-only Kindle PW3 evidence collector

**The collector is opt-in and defaults to a dry run.** It is a bounded inventory of fixed diagnostic paths, not a recursive file dump or a firmware-copying tool.

```sh
python3 tools/collect_pw3_readonly.py
python3 tools/collect_pw3_readonly.py --host 192.168.8.102 --port 2222 --collect --out ~/Downloads/pw3-readonly-evidence.zip
```

To optionally read a small fixed set of init-related *text* files into a separate local ZIP:

```sh
python3 tools/collect_pw3_readonly.py --host 192.168.8.102 --port 2222 --collect --include-init-scripts --out ~/Downloads/pw3-init-evidence.zip
```

**Never upload the resulting ZIP to this public repository.** Inspect its contents for personal identifiers, mount paths, and secrets before sharing. No automatic sharing is performed. By design it omits user documents, wireless credentials, SSH keys, boot images, firmware blobs, personal home directories, and arbitrary recursive paths.

Uses ordinary SSH commands: `uname`, `cat`, `ls`, `wc`, `dd`. These commands perform no remote writes. The archive and SHA-256 manifest are generated locally. The optional init-file list is fixed and uses size limits and symlink checks. The script cannot bring up SSH or change Kindle settings; if SSH is not already enabled, do not modify stock software just to collect data.

This optional observational SSH access is distinct from the **strict host-only emulation** used for R21.5. It does not authorize flashing, boot changes, EPDC commands, suspend, sysfs writes, networking changes or actual Kindle-side KOReader runs.

Some future research may need specifically approved read-only evidence about PW3 e-ink/touch/battery/frontlight interfaces. Do not probe these functions by sending ioctls or changing hardware. **NO_FIRMWARE_WRITES_HOLD** remains in effect.

## Kindle BusyBox 1.17 compatibility

The 2026-11-01 SSH v2 evidence reached the Kindle but all 17 probes
failed: BusyBox rejected `head -c`; its `grep` also rejected `-E`.
The collector now caps remote stdout with POSIX `dd bs=1 count=32768`
and filters library filenames on the Mac instead of using remote grep.
It refuses unbounded collection if remote `dd` is unavailable.

Use a fresh output name (no overwrite):

```sh
python3 tools/collect_pw3_readonly.py --host 192.168.8.102 --port 2222 \
  --collect --out ~/Downloads/pw3-readonly-evidence-v3.zip
```

This fix has only been locally regression-tested, not yet verified against
the physical Kindle. It does not authorize hardware IOCTLs, boot actions,
firmware writes, or pushing raw captures to public GitHub.
