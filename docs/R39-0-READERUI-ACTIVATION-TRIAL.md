# R39.0 — separate real ReaderUI activation trial

**Status (2026-11-02): SOURCE-ONLY/HOST PASS, ARM/QEMU PENDING.** The source-only `pw3-os-r39.0-readerui-activation-trial.zip` has release SHA-256 `e77c99ccc36bb0a4309d1a957ac88a36d8a012f04fc4269b97cc647c3d63aedb`. Its ZIP integrity and ten internal payload hashes verify; **35/35 host tests PASS**, Python/shell syntax and three Lua source parses PASS. No staged rootfs or Kindle firmware is distributed. This is **not** an independently bootable image.

## Basis and boundaries

R38.2.1's **user-side read-only reconciliation PASS** (`R38_2_EXISTING_ARM_EVIDENCE_GATE_RECONCILED`, 79 host checks) supports genuine isolated per-book settings migration and reload, but preserved the original R38.2 review FAIL for an old marker typo. R37 validated six original KOReader source hashes. R36 found 472 positively observed staged regular files and 976 `UNKNOWN_HOLD`. Neither outcome proves full ReaderUI opening, page-turn or complete dependency closure.

R39.0's *purpose* is to try the next real boundary rather than falsely reusing an old pass: real FileManager `openFile()` → actual ReaderUI `showReader()` → actual `UIManager:nextTick`/coroutine → genuinely constructed ReaderUI instance holding an **original two-page PDF** → one synthetic Close → genuine UIManager shutdown.

It does **not** yet send `GotoPage`, verify changing the current page from one to two, return to FileManager or exercise a physical PW3 screen. The two-page fixture is reproducibly generated, independently inspected as exactly two PDF pages and SHA-pinned: `17f2bf493433c9664457dd51f0e3e31e2f67b88b0480f97a3ed9dc2ade7170db`.

## Independent control and new guard

R25's original pinned one-event `loop_guard.lua` remains completely unchanged. The R39 source archive includes an explicitly **forked synthetic guard** SHA-256 `1b7512a896c04d17b4632e12011424a10344e4745d5bb00de3c2ba77159c6ba6`, which retains hard filesystem and hardware denials and allows at most one additional Ink Away plugin discovery/load attempt *after genuine FileManager close*. This fork is not the R25 source and will never be reviewed as if it were. The source preflight confirms original R25 SHA `7f5881a9c79da22c626bd0451a580fd13eae8af96330de811a13042cd98ed2b8` and six pinned staged KOReader hashes against R37.

The runner performs **two separate QEMU/Docker executions** with their own ephemeral `/tmp`: first the unmodified R25 strict baseline, second the new R39 ReaderUI trial. If the baseline fails, the R39 experiment is not run. The R39 reviewer has its own ordered markers and requires a real `ReaderUI.instance`, the two-page PDF in an active real document, a genuine ReaderPaging method, and clean app exit. It will fail if ReaderUI cannot initialize, if its asynchronous coroutine crashes, if a synthetic device method is missing or if the widget stack differs. It explicitly returns `page_navigation_verified=false`, `returned_to_filemanager_verified=false`, `complete_dependency_closure_proven=false` even if first activation passes. Do not lower that standard to force a green outcome.

Runtime container has `--network none --read-only --cap-drop ALL --security-opt no-new-privileges`, memory and CPU bounds, disposable `/tmp`, and read-only stage/source mounts. Docker *image build* can fetch packages on cold cache, but application execution is networkless. The stage is never modified, and all target EPUB/PDF sources are synthetic.

## Run on Mac (fresh R39 output)

```sh
cd ~/Downloads
unzip pw3-os-r39.0-readerui-activation-trial.zip
cd pw3-os-r39.0-readerui-activation-trial
python3 -m unittest discover -s tests -v

./run-r39-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json" \
  "$PWD" \
  "$HOME/Downloads/pw3-os-r39.0-readerui-activation-first-run"

cat "$HOME/Downloads/pw3-os-r39.0-readerui-activation-first-run/R39-R25-BASELINE-CONTROL.json"
tail -n 180 "$HOME/Downloads/pw3-os-r39.0-readerui-activation-first-run/R39-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r39.0-readerui-activation-first-run/R39-REVIEW.json"
```

**Expected only if the user's QEMU run completes every independent check:** `R39_READERUI_FIRST_ACTIVATION_ARM_PASS`. Current status: **PENDING**. A failed R39 attempt is a bounded and useful next-interface diagnostic; preserve both its new log and historic baseline results, and do not infer that old R25/R32/R33 success was invalidated. All unknown staged files continue on hold.

**Immutable safety status:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.

Related: [R39 full two-page navigation design](R39-READERUI-TWO-PAGE-EVENT-CONTRACT.md), [R38.2.1 verified reconciliation](R38-2-1-GATE-MARKER-REPAIR.md), [R37 source hashes](R37-READERUI-BOUNDARY-PREFLIGHT.md).
