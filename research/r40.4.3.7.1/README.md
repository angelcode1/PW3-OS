# R40.4.3.7.1 — existing R37 run read-only private-trace-safe diagnostic

**Diagnostic only; ARM/QEMU NOT RERUN; NOT_BOOTABLE; research and educational purposes only.**

The uploaded R40.4.3.7 review is a generic HOLD. Its `original_strict_r40436_reviewer_pass=false` is a fallback assigned by R37 on any caught failure, not proof the earlier reviewer actually ran and failed. The earlier R40.4.3.6 bounded synthetic draw/save PASS remains historical.

A standalone Python release reads only the existing local R37 `R40435-EXIT.txt`, private guest stdout and private QEMU stderr; it checks exact source-defined marker order (earlier 3.6 drawing/save, new R37 plugin event, closing). It exports only fixed checkpoint names, enumerated failure boundaries, count metadata and bounded replay category. If unchanged prior release and original stage source paths are present in Downloads, it calls the prior R36 strict reviewer on the existing trace read-only, suppressing any private text. It does not start Docker/QEMU, rerun the guest, touch a Kindle, write to the source stage or modify the original failed run. The only new output is `~/Downloads/R404371-DIAG-PUBLIC.json` outside the failed run; any existing output is refused.

**Standalone release:** `pw3-os-r40.4.3.7.1-existing-run-diagnostic.zip` SHA-256 `1ac336abd2b3ddbd6dadc31ae41dca98c2fa95f8188080dc3f3358cca3b5ff6b`, 8,782 bytes, 5 members (4 SHA manifest entries); archive CRC, clean extraction and member hashes verified, **16 host tests PASS**, shell syntax PASS. Full executable source and exact commands are included in the versioned ZIP (not in GitHub). Private run traces, original source capture and full local paths were **not** committed.

Run on the user's Mac:

```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.1-existing-run-diagnostic.zip -d pw3-os-r40.4.3.7.1-existing-run-diagnostic
SRC="$HOME/Downloads/pw3-os-r40.4.3.7.1-existing-run-diagnostic"
sh "$SRC/RUN-R404371-MAC.sh"
```

Share **only** `~/Downloads/R404371-DIAG-PUBLIC.json`. Preserve the existing failed guest run; no source patch or second guest run is authorized by this release. If the existing trace is missing or malformed, the tool reports that explicitly instead of claiming a root cause. Original decoded syscall analysis remains incomplete. Preserve historical 347 staged regular file opens (not recomputed), 1,101 unobserved stage regulars, 976 historical UNKNOWN_HOLD, and `NOT_BOOTABLE`: no device/firmware/hardware writes, boot, file removal or pruning.
