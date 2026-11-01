# R39.0 — separate real ReaderUI activation trial

**2026-11-02 update:** Original R39.0 **USER ARM/QEMU TRIAL FAIL**, although an independently executed, unchanged R25.3 baseline reviewer returned `R25_REAL_EVENT_LOOP_ARM_PASS`. Genuine FileManager opened the original two-page PDF and scheduled the real ReaderUI coroutine. ReaderUI failed during `init()` at line 120 because the R17 synthetic Input adapter lacked `inhibitInput`; error recovery then hit missing `inhibitInputUntil` at line 730. R39 ReaderUI instance/page navigation remain unverified. [R39.1](R39-1-READERUI-INPUT-LIFECYCLE-FIX.md) corrects only this synthetic input adapter gap; **51/51 host tests PASS; user-side ARM/QEMU pending**. Never reinterpret original R39.0 reviewer FAIL as PASS.

## R39.0 user-supplied ARM/QEMU evidence

The user-supplied local output confirms the unmodified R25 baseline first: `R25_REAL_EVENT_LOOP_ARM_GATE_PASS` and reviewer `R25_REAL_EVENT_LOOP_ARM_PASS`. The distinct R39 trial then reached:

```text
R39_ORIGINAL_TWO_PAGE_PDF_COPIED_TO_TEMP
R39_GENUINE_FILEMANAGER_OPENFILE_READERUI_SCHEDULED
INFO opening file /tmp/r25-ko-home/library/r39-original-two-pages.pdf
[!] doShowReader coroutine crashed:
frontend/apps/reader/readerui.lua:120: attempt to call method 'inhibitInput' (a nil value)
...
frontend/apps/reader/readerui.lua:730: attempt to call method 'inhibitInputUntil' (a nil value)
R39_READERUI_FIRST_ACTIVATION_ARM_GATE_FAIL (exit=1)
```

R39's independent reviewer returned `FAIL` for missing `R39_REAL_READERUI_INSTANCE_AND_TWO_PAGE_PDF_OPENED`. This is correct and remains the historical status; the first error is a missing input API on the synthetic R17 instance, not a failed PDF fixture or a proven ReaderUI constructor. `Generic:setIgnoreInput`, `Generic:notifyBookState` and the synthetic memory-screen's `setWindowTitle` already exist and do not require replacement. See the bounded synthetic Input adapter correction in [R39.1](R39-1-READERUI-INPUT-LIFECYCLE-FIX.md).

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
