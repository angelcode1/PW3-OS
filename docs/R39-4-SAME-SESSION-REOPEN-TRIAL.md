# R39.4 — same-session PDF reopen / second Home trial

**2026-11-02 status: source-only host-tested release, 291/291 host regressions PASS; ARM/QEMU pending. NOT_BOOTABLE.**

## Purpose and preserved controls

R39.3.3's real two-page PDF draw, genuine `GotoPage(2)`, first Home→FileManager return, engine release and final Close passed user-side ARM/QEMU. R39.4 is a **new**, bounded follow-up to test a second document lifecycle in the *same application process*; its experimental overlay does not modify production KOReader or the original R25/R39.3.3 source. The separate old one-cycle R39.3 strict reviewer must not be applied to a two-cycle log.

## New intended guest sequence

1. First genuine FileManager → asynchronous ReaderUI → original PDF scroll draws for pages 1 and 2 → real UIManager `GotoPage(2)` → genuine Home → new FileManager, all strict first-cycle ownership/engine/registry checks retained.
2. Returned genuine FileManager instance invokes original `FileManager:openFile` for **the same** disposable `/tmp/r25-ko-home/library/r39-original-two-pages.pdf`. The real coroutine must create a **distinct** ReaderUI and PdfDocument.
3. Complete genuine `ReaderView:drawScrollPages` again. The reopened document may start on page 1 **or** page 2 depending on saved reading position; a second page change is deliberately **not** claimed.
4. A second UIManager Home closes the second reader and engine. A pre-constructor read-only snapshot requires raw engine nil, inherited false sentinel, no registry refs, nil ReaderUI singleton/document and the absence of a new FileManager until real construction returns.
5. Genuine FileManager appears a second time. Final real UIManager Close leads to empty widget stack and Generic/device/input shutdown.

Only **four UIManager-dispatched events** (page turn, Home, Home, Close), at most **eight input polls**, and a single bounded genuine `UIManager:setDirty` retry per page per cycle. No mock ReaderUI, PDF engine, direct renderer, hardware device, firmware write, boot action or staged file removal is permitted.

## Release and host checks

Session artifact `pw3-os-r39.4-same-session-reopen-arm-trial.zip` SHA-256:
`aaa25639971c47553ad9896694cbd1949ec8fa7b49e45e1afc901c45470675b3`.

- 47 ZIP entries; CRC and release `SHA256SUMS-R394` verified.
- **291 Python host regressions PASS** (261 inherited + 30 R39.4).
- Python compileall and both POSIX shell syntax checks PASS.
- Three Lua experimental files pass Lua 5.4 syntax-only compilation.
- R39.4 source pins, previous R39.3.3 user-side sentinel SHA-256 `0495144ebea105d337ea0bcf0b7009bcb679b3dcaafaa22f2ed3a48753f1dbb6`, original R39.3.3 source pins and independent original R25 stage/control are checked before guest execution.

The ZIP is distributed separately from the repository through the research session. See its `README-R39.4.md` for the full Mac command, fresh output paths and evidence collection. The official GitHub repository does not itself contain an independently bootable image.

**Pending ARM/QEMU target gates** (not earned by host tests):

```text
R25_REAL_EVENT_LOOP_ARM_PASS
R39_4_REOPEN_ARM_GATE_PASS
R39_4_SAME_SESSION_REOPEN_ARM_PASS
```

Only a new, user-side ARM/QEMU run can establish the last two. R39.4's new strict reviewer is `r394/review_r394.py`; original historical reviewers remain distinct and unmodified.

**Holds:** `NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE`. All 976 prior `UNKNOWN_HOLD` staged files remain retained. There is no physical device demonstration, global startup migration, dependency closure or boot authorization.
