# R40.4.3.7.4.1 — host manifest correction and offline Docker read-only doctor

Research and educational only. **23/23 host tests PASS; ARM/QEMU NOT RUN; NOT_BOOTABLE.**

Original R40.4.3.7.4 Mac host tests failed from `manifest line count mismatch` when generated `__pycache__/*.pyc` files were mistakenly counted against the 10-payload SHA256SUMS. Fresh extraction reproduced the failure with bytecode enabled. The new `verify.manifest()` ignores **only** ephemeral Python `__pycache__/*.pyc` and macOS `.DS_Store`/`._*` sidecars; it still validates every declared source member hash, rejects unlisted nonmetadata content, and rejects modified listed files. Three new regression tests enforce those distinctions. The original guest Lua, `reference.json` exact source pins, strict reviewer, QEMU probe and Docker runner are byte-identical to the prior release.

Corrected ZIP: `pw3-os-r40.4.3.7.4.1-host-fix.zip`, SHA-256 `b6aa5f169be296a4fe469b0649fdb0f3c9741ab410ecfbfc3ea7ecc5d2160119`, 39,093 bytes, 12 ZIP members (11 SHA256SUMS entries). Fresh extraction, CRC and SHA-256 checks PASS. 23 host regressions PASS in a clean extraction with bytecode enabled, repeated after caches are created; the one-command test mode PASS; shell syntax checks PASS. Read-only Docker diagnostic separately classifies missing CLI, unreachable Docker engine and missing local image `pw3-r394-reopen-trial`. It never downloads, builds, retags or imports any image.

Exact Mac commands:

```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.4.1-host-fix.zip -d pw3-os-r40.4.3.7.4.1-host-fix
SRC="$HOME/Downloads/pw3-os-r40.4.3.7.4.1-host-fix"
sh "$SRC/RUN-R404374-MAC.sh" test
sh "$SRC/CHECK-R404374-DOCKER.sh"
```

If the required image exists in the original Docker context and no other guard refuses, run **once** into a fresh output:

```sh
sh "$SRC/RUN-R404374-MAC.sh" trial "$HOME/Downloads/pw3-os-r40.4.3.7.4.1-handler-lookup-first-run"
```

No Docker replacement is presumed. If Docker check fails, retain original image requirement and report only the fixed diagnostic category. If the guest executes, upload only its public `R404374-REVIEW.json`, not raw trace/source/stage paths. The 347 historical observed staged opens were not recomputed, 1,101 unobserved regular stage files and 976 historical UNKNOWN_HOLD retained, R26 provenance and complete dependency closure unproven, QEMU decoder incomplete. No device, hardware, firmware, boot, file removal or pruning; **NOT_BOOTABLE**.
