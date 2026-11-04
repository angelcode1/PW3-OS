# R40.4.3.7.18.D1 — original Lua pcall reason classifier (diagnostic-only)

Research and educational purposes only; **NOT_BOOTABLE**.

User's exact R3718 trial had original R3717 parent marker chain 7/7 PASS, third original InkAway view opened, 0/8 new R3718 markers, QEMU exit=1, Lua traceback. Pinned site diagnostic returned guest frame line **2440**, which is the outer assertion checking the already-caught `pcall(native_dofile, 'reader.lua')` reason against `R4041_INTENTIONAL_OS_EXIT_HOLD`, **not the underlying pre-marker error site**. The reason was not printed by that outer assertion, so existing raw trace does not establish which new expression failed.

Diagnostic-only source pinned ZIP: `pw3-os-r40.4.3.7.18.d1-pcall-reason-diagnostic.zip`, SHA-256 `5b20580ea7d47b0c15142ea2159cf9bfe29291da7967b73e9ca66b005425a653`, 13 files. Clean extracted 30/30 local host tests PASS, manifest hashes PASS, ZIP CRC PASS and shell syntax PASS. **No new ARM/QEMU result**.

The D1 guest is a byte-pinned exact one-insertion derivative of the original R3718 guest (original SHA `f29128070a7824b56dfdb09a00865b4a9d5b1378ba74d756f6fce1a47a9a68a4`). The insertion is immediately after original `pcall` and prints only fixed enum `REASON_CLASS` / `REASON_PHASE` values, never the captured raw string, paths or traceback. The original pcall return values, final R4041 assertion, original staged Lua sources, R3718 reviewer, R3717 inherited source and R35/R26 preflight are not altered. The original R3718 source-check is required. A fresh output directory and original offline Docker policy (network none, read-only stage, no-new-privileges, all caps dropped, non-root) are mandatory.

The diagnostic reviewer always writes `R4043718D1_DIAGNOSTIC_HOLD_NO_ARM_PASS`, never a research PASS. It records whether the parent final marker was present and the classified reason; raw QEMU/guest logs remain local. This is to classify a failure, **not a repair, deployment, firmware action or hardware test**. R26 provenance remains unauthenticated, device polling and physical PW3 untested, stage 1,101 unobserved files and 976 UNKNOWN_HOLD retained, complete dependency closure unproven. `NOT_BOOTABLE`.
