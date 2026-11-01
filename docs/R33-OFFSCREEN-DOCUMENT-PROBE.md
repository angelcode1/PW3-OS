# R33 — genuine PDF and EPUB offscreen document engines

**2026-11-01 status:** R32 genuine Ink Away menu, synthetic stroke, temporary project save, parser reload and R25 real UIManager loop/shutdown **ARM/QEMU PASS** (user-supplied reviewers). **R33 host-only: 27/27 tests PASS; ARM/QEMU run PENDING.** EPUB/PDF rendering has NOT been verified on ARM.

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