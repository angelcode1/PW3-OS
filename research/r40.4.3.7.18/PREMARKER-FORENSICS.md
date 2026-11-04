# R40.4.3.7.18 — refined read-only Lua traceback site diagnosis

The user ran the exact-review-sha-pinned R3718 read-only forensics. The original R3717 markers completed **7/7 in order**. No R3718 new marker appeared (**0/8**). Last original guest marker was `R404377_TOUCHMENU_SELECTION_OPENED_THIRD_ORIGINAL_VIEW`; the first missing new marker was `R4043718_MENU_SELECTED_DRAW_INPUT_BOUNDARY_AUTHENTICATED`. QEMU exited `1`, a Lua traceback was observed, and the post-exit failure marker was present. No known R3718 assertion literal was found. This **does not identify the root cause** and does not imply original R3717 regression.

The exact R3718 archived guest source is SHA-256 `f29128070a7824b56dfdb09a00865b4a9d5b1378ba74d756f6fce1a47a9a68a4`, 2,479 lines. The R3718 setup insertion is at guest lines 1630–1697 and its first `R4043718_MENU_SELECTED_DRAW_INPUT_BOUNDARY_AUTHENTICATED` marker is at line 1698. It is not proven which expression or underlying original function failed.

Read-only follow-up tool: `R4043718-PREMARKER-TRACE-SITE-READONLY.py`, SHA-256 `c514d88fac1aa6ae396284441755454d3374fcae30e13745e45cb0e0466f0a3c`, 52/52 local host tests PASS. It pins exact previously uploaded HOLD review and exact archived guest source, inspects only the local existing trial trace and exits with a sanitized fixed error code or source line/phase, recognized error category and allowlisted symbol. No paths, raw messages or tracebacks are printed; no QEMU or any write, device access, gate modification, stage mutation or source repair occurs. **User has not run this tool yet**.

Existing R35/R26 and R3717 safety and provenance gates unchanged. Physical PW3 untested, original stage and historical unknown holds retained, full dependency closure unproven. **NOT_BOOTABLE**.
