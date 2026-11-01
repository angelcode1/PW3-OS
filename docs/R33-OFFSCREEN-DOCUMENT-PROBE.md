# R33 — genuine PDF and EPUB offscreen document engines

**2026-11-02 status:** R25.3 and R32 remain **user-verified ARM/QEMU PASS**. Original R33 **ARM/QEMU FAIL** in the PDF test fixture due to omitted gamma/saturation arguments. Corrected R33.1 **33/33 host tests PASS, ARM/QEMU PENDING**. Neither PDF nor EPUB offscreen rendering has been verified on ARM.

## User-supplied R33 ARM failure and targeted R33.1 retry

The user's R33 log reached genuine `reader.lua`, FileManager, R32 Ink Away project persistence, `R33_ORIGINAL_DOCUMENT_FIXTURES_COPIED_TO_TEMP`, and `R33_GENUINE_MUPDF_PDF_OPENED`. It then failed at:

```text
frontend/document/document.lua:398: attempt to concatenate local 'saturation' (a nil value)
R33_DOCUMENT_OFFSCREEN_ARM_GATE_FAIL (exit=1)
```

All three fresh R25, R32, R33 reviewers correctly reported **FAIL**, because the R33 test never resumed the event-loop/shutdown after the exception. This does not undo the separate R25.3 or R32 ARM successes.

The R33 test overlay incorrectly called `pdf:renderPage(1,pdfrect,1,0)`; genuine KOReader v2026.07.2 `Document:renderPage(pageno,rect,zoom,rotation,gamma,saturation,hinting)` includes both numeric values in `Document:getFullPageHash`. Its neutral gamma is `GAMMA_NO_GAMMA=1.0`, and unmodified saturation is `1.0`. **Only the test overlay** now supplies both parameters: `pdf:renderPage(1,pdfrect,1,0,1.0,1.0)`.

R33.1 changes no native renderer, test document fixture, staged rootfs, R32/R25 pin, strict reviewer or Docker safety setting. **33/33 synthetic host tests PASS** (27 previous, 6 new), Python/shell/Lua syntax PASS, ZIP integrity and 12 payload SHA-256 checks PASS. Source-only ZIP `pw3-os-r33.1-pdf-render-arguments-fix.zip`, SHA-256 `b3d6070b6f3c1b3923f11784d65486ba9db20ff168c1584a27465f525b7422bf`. **R33.1 ARM execution remains pending.**

### Mac retry: do not overwrite previous evidence

```sh
cd ~/Downloads
unzip pw3-os-r33.1-pdf-render-arguments-fix.zip
cd pw3-os-r33.1-pdf-render-arguments-fix
python3 -m unittest discover -s tests -v

./run-r33-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r32-inkaway-persistence" \
  "$HOME/Downloads/pw3-os-r32-inkaway-first-run/R32-RESULT-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r33.1-offscreen-first-run"

tail -n 160 "$HOME/Downloads/pw3-os-r33.1-offscreen-first-run/R33-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r33.1-offscreen-first-run/R33-R25-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r33.1-offscreen-first-run/R33-R32-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r33.1-offscreen-first-run/R33-REVIEW.json"
```

The target verdict is still `R33_PDF_EPUB_OFFSCREEN_ARM_PASS`, only after three fresh reviewers succeed. New actual ARM failures must remain FAIL and be diagnosed individually.

## Narrow objective

The R33 overlay runs inside the unchanged pinned R25.3 + R32 synthetic `reader.lua` test. It creates two original, checksum-pinned document fixtures (one valid PDF, one minimal EPUB), copies them from read-only `/r33/fixtures` into disposable `/tmp/r25-ko-home/library`, and uses the genuine KOReader v2026.07.2 `DocumentRegistry:openDocument` API. PDF must select MuPDF, open one real page and return an in-memory render tile. EPUB must select CREngine, load and lay out the document and draw a 240x320 memory-only BlitBuffer. Both document references must close; the R32 and R25 lifecycle must then complete again.

The source-only test does not prove the ReaderUI document-open workflow, pixel fidelity, page navigation, the physical PW3 framebuffer, an unrestricted migration-enabled startup, stock firmware modifications or independent boot. An unsupported native document method or synthetic hardware API must FAIL rather than emit a false successful render. A passed host syntax/reviewer suite does not establish ARM execution.

## Package and host validation

Source-only conversation archive `pw3-os-r33-offscreen-document-probe.zip` SHA-256 **`da655b57e9b7b9076a4a250150d3f85937eb3f52f3be100a37a5b971c275ed1f`**; ten payload SHA-256 entries and ZIP integrity checked, 27/27 host tests PASS, Lua/Python/shell syntax PASS. The original test PDF was parsed as a valid single-page PDF by the host pdfinfo command; the EPUB ZIP passed integrity tests. The archive contains no R13 stage, user books, private paths or Kindle firmware.

The runner pins the earlier R32 source file hashes and checks the prior R32 reviewer, which itself was based on a pinned R25.3 source. It repeats the five source-contract audits into distinct files, refuses overwrites, and regenerates fresh R25, R32 and R33 reviewers. Application runtime uses Docker `--network none`, `--read-only`, `--cap-drop ALL`, `--security-opt no-new-privileges`, one CPU, 768 MiB limit, disposable 160 MiB `/tmp`, a read-only R13 stage and read-only R32/R33 source mounts with no Kindle device mounts. Cold Docker image builds may need Debian package downloads; runtime is networkless.

## Reproduce from existing user packages

```sh
cd ~/Downloads
unzip pw3-os-r33-offscreen-document-probe.zip
cd pw3-os-r33-offscreen-document-probe
python3 -m unittest discover -s tests -v
./run-r33-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r32-inkaway-persistence" \
  "$HOME/Downloads/pw3-os-r32-inkaway-first-run/R32-RESULT-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r33-offscreen-first-run"
tail -n 160 "$HOME/Downloads/pw3-os-r33-offscreen-first-run/R33-EMULATION.log"
cat "$HOME/Downloads/pw3-os-r33-offscreen-first-run/R33-R25-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r33-offscreen-first-run/R33-R32-REVIEW.json"
cat "$HOME/Downloads/pw3-os-r33-offscreen-first-run/R33-REVIEW.json"
```

**Target only after ARM/QEMU PASS:** `R33_PDF_EPUB_OFFSCREEN_ARM_PASS`. If it fails, preserve all logs and never overwrite prior R25/R32 success evidence. No file removal is authorized.

**HOLD:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.

Upstream pinned source: [DocumentRegistry](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/document/documentregistry.lua), [PDF renderer](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/document/pdfdocument.lua), [CRE renderer](https://github.com/koreader/koreader/blob/v2026.07.2/frontend/document/credocument.lua).