# R39.2.2 — bounded genuine UIManager repaint for PDF page-turn proof

**2026-11-02 status: HOST-ONLY PASS — 116/116 tests; ARM/QEMU PENDING.** This is a separate trial after user-side **R39.2.1 ARM/QEMU FAIL**, and preserves that historical failure plus the independent original R25 control PASS and earlier R39.1 ReaderUI-activation ARM PASS.

## Actual R39.2.1 failure and source diagnosis

The user's local R39.2.1 guest trace reached genuine FileManager `openFile`, ReaderUI coroutine, and source-pinned Input inhibit/release successfully, then failed at `/r39/loop_guard.lua:471: R39.2.1 first page must complete genuine MuPDF draw before input`. The original R25 control returned `R25_REAL_EVENT_LOOP_ARM_PASS`. **No GotoPage event was sent; no page navigation was verified.** No successful original PDF draw-completion callback was observed before the first input poll; the guest log does not show why.

KOReader `UIManager:handleInput()` processes due nextTick tasks, runs `_repaint()`, and then invokes `Input:waitEvent`. The ReaderUI instance may therefore be visible at the first synthetic poll without its PDF page already having been drawn if it did not yet receive a dirty repaint. Separately, the R39.2.1 strict reviewer ordered the first *input poll*'s `R39_REAL_READERUI_INSTANCE_AND_TWO_PAGE_PDF_OPENED` marker **before** the *paint pass*'s `R39_2_1_GENUINE_MUPDF_PAGE1_DRAW_COMPLETED` marker. That is not a valid mandatory ordering for real paint-before-input events.

R39.2.2 corrects both limitations while preserving the original genuine PDF draw requirement.

## Narrow source changes

The new, separately SHA-pinned forked R39 synthetic Input guard permits **one bounded no-event input poll per PDF page**. If a live real ReaderUI with the exact original two-page temporary PDF is present and page 1 or 2 has not completed its genuine `ReaderView:drawSinglePage`, the guard verifies `UIManager:setDirty` originates from the pinned upstream UIManager, calls `real_ui:setDirty(reader,'full')` **once** for that page and returns `nil` to permit the next genuine UIManager `_repaint` cycle. If the original ReaderView draw still has not completed on the next poll, FAIL with a page-specific diagnostic; no arbitrary waiting or fake draw is allowed. Polls bounded at **four** total: two actual dispatched events (`GotoPage(2)`, then `Close`) and at most two no-event repaint cycles.

The original ReaderView `drawSinglePage` wrapper still requires genuine `ReaderView:paintTo` caller at pinned source line 198, unchanged original `drawSinglePage` execution and successful return, live real ReaderUI/ReaderPaging, exactly two pages, a nonnil memory-backed blitbuffer, and page state agreement. Its page-specific counter increments **only after** the original PDF draw returns. There is no direct `paintTo`, direct PDF draw, fake ReaderUI instance, fake page-state assignment, or synthetic drawing marker.

The new strict reviewer accepts an optional single `R39_2_2_BOUNDED_REAL_UIMANAGER_REPAINT_REQUESTED_PAGE1` or `...PAGE2` marker only in the correct pre-draw phase. It requires the genuine page-1 draw-completion marker **before** first-input ReaderUI verification; page 2 completion must follow the genuine UIManager-dispatched page-turn event and precede Close. All previous source, PDF fixture, stage and original R25 control pins remain, and the previous R39.1 ARM reviewer PASS is mandatory.

An ARM PASS, if later observed, will support genuine **synthetic** ReaderUI page 1→2 navigation and completed original in-memory PDF draw calls, **not** physical framebuffer/pixel fidelity, hardware input, Home→FileManager return, complete dependency closure, boot or pruning.

## Host release

Conversation attachment: `pw3-os-r39.2.2-bounded-repaint-proof.zip`, SHA-256 **`4a7e28095d40696a7079eb04b3c6cabe29b0b653380ad2bba1d045415fe861d0`**. ZIP integrity and **18 internal payload SHA-256 hashes PASS**. **116/116 synthetic host tests PASS**, Python compilation, POSIX shell syntax, and syntax-only Lua 5.4 parsing of all three Lua files PASS. No ARM/QEMU run was performed in this environment. The stage remains private to the user's computer.

The new forked guard SHA-256 is `37c32a1c45d34f2ef6f724f71ac03ac0f30478ace69e4126e8899bf15165126f`, and independent strict reviewer SHA-256 `5c95e89a650b7ac0234fb3c1d44d647bc61cee7eaf58a6fee7f40850473d2714`. The original R25.3 guard SHA-256 `7f5881a9c79da22c626bd0451a580fd13eae8af96330de811a13042cd98ed2b8` is unchanged.

## Run on Mac

```sh
cd ~/Downloads
unzip pw3-os-r39.2.2-bounded-repaint-proof.zip
cd pw3-os-r39.2.2-bounded-repaint-proof
python3 -m unittest discover -s tests -v

./run-r39-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r37-readerui-boundary-first-run.json" \
  "$HOME/Downloads/R38.2.1-EXISTING-EVIDENCE-RECONCILED.json" \
  "$PWD" \
  "$HOME/Downloads/pw3-os-r39.1-readerui-activation-first-run/R39-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r39.2.2-page-turn-first-run"

cat "$HOME/Downloads/pw3-os-r39.2.2-page-turn-first-run/R39-R25-BASELINE-CONTROL.json"
tail -n 180 "$HOME/Downloads/pw3-os-r39.2.2-page-turn-first-run/R39-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r39.2.2-page-turn-first-run/R39-REVIEW.json"
```

**Expected only after actual user-side guest success:** runner gate `R39_2_PAGE_TURN_ARM_GATE_PASS`, strict reviewer `R39_2_READERUI_PAGE_TURN_ARM_PASS`, with `page_navigation_verified=true` and `genuine_pdf_draw_single_page_completion_verified=true`. This trial may still FAIL if the real UIManager repaint does not invoke ReaderView; in that event preserve the earliest failure and do not waive a render assertion. Do not overwrite the existing R39.2.1 run.

## Immutable holds

Docker application runtime remains networkless, read-only, capability-dropped and ephemeral; original source and synthetic PDF mounts read-only; no physical device mounts, firmware operations, kernel interfaces, rootfs creation or pruning. R36's 976 regular files without successful-open evidence remain `UNKNOWN_HOLD`. All global startup migrations remain skipped. **NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_BOOT_ACTIONS; NOT_BOOTABLE.**

See [R39.2.1 failed first-paint trial](R39-2-1-GENUINE-PDF-DRAW-COMPLETION.md) and [R39.1 verified ReaderUI activation](R39-1-READERUI-INPUT-LIFECYCLE-FIX.md).
