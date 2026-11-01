# R35 — trace guest file opens across Ink Away, PDF, EPUB and ReaderUI import

**2026-11-02. Latest verified ARM:** User-supplied `R34_READERUI_IMPORT_ARM_PASS` with fresh R25, R32, R33 strict reviewers PASS. ReaderUI was imported, **not instantiated**, and no per-book migration, reader navigation, hardware initialization or boot occurred.

**R35 USER ARM/QEMU PASS**, supplied by the user with four fresh reviewer PASS outputs. The 33/33 synthetic host tests also passed. This is a QEMU guest syscall trace of one combined synthetic workload, not complete dependency closure. Source-only archive available in the current ChatGPT conversation: `pw3-os-r35-workload-file-trace.zip`, SHA-256 `90f40b21027fc4da9d21833d1db34656d3d3a29324aa36c648e9da70a2a7b869`. ZIP integrity, six payload checksums, shell and Python syntax verified. It contains no R13 rootfs, Kindle firmware, copyrighted books or local private trace records.

## User-side R35 verified aggregate result — 2026-11-02

The user supplied `R35_GUEST_WORKLOAD_TRACE_CAPTURED`, plus fresh `R25_REAL_EVENT_LOOP_ARM_PASS`, `R32_INKAWAY_PERSISTENCE_ARM_PASS`, `R33_PDF_EPUB_OFFSCREEN_ARM_PASS`, and `R34_READERUI_IMPORT_ARM_PASS`. The R35 JSON reports:

| Observed aggregate | R27 startup-only | R35 combined |
|---|---:|---:|
| Guest path syscall attempts | 2,262 | **4,995** |
| Successful guest open calls | 697 | **1,007** |
| Failed guest path attempts | 1,471 | **3,745** |
| Distinct lexical paths with successful opens | 369 | **543** |
| Additional distinct successful-open lexical paths vs R27 | — | **175** |
| Additional distinct *stage-like* lexical successful-open paths | — | **132** |
| Guest trace lines | 6,113 | **10,822** |

R35 used 4,501 `open`, 16 `openat`, 473 `stat64`, 4 `lstat64` and one `access` call. All 4,995 path syscalls were parsed, with zero unresolved path attempts. Raw R35 trace SHA-256: `5a564aeea8ba6b46cf77e36dee86784afae8829ed772d4f2335f725dda8fdcbe`. The original R27 trace and R26 stage sentinel SHA-256 digests matched the user-supplied values.

The **175** and **132** are counts of lexical path strings, **not verified additional distinct regular staged files**. The R35 guest environment includes temporary storage, the test harness, unresolved working-directory context and unvalidated symlink behavior. It is not safe to infer any file removal, closure, Kindle hardware operation or new rootfs.

**Next:** [R36 stage-catalog lexical correlation](R36-EXPANDED-WORKLOAD-CATALOG-CORRELATION.md) will revalidate the private R26/R27/R35 evidence locally, then count newly observed *cataloged regular files* rather than equating distinct raw path strings with staged file dependencies.

## Motivation and scope

The old R27 guest-syscall trace covered only a synthetic startup/shutdown run: 2,262 guest path attempts and 697 successful opens. Later milestones proved genuine Ink Away menu/stroke/temp save/project parser reload (R32), MuPDF PDF memory tile and CREngine EPUB memory view (R33.1), and genuine ReaderUI module import (R34.0). R35 reruns this **combined R34 workload** with QEMU's guest syscall tracing enabled, and compares its *distinct lexical successful-open path strings* to the original R27 private records.

**R35 is not a full ReaderUI workflow test or complete dependency closure.** It does not validate ReaderUI instance creation, actual page turning, pixel fidelity, guest CWD/symlink resolution, host QEMU or kernel firmware file access, suspend/battery/e-ink, or independent Alpine boot. No file is marked removable based on lack of open evidence. Use a new rootfs only after further audited coverage, never prune the stock stage.

The unchanged originals are pinned via R34 source SHA checks, R33.1 and R32 source checks, the immutable R13 manifest checksum, the R26 stage-sentinel checksum, prior R27 summary/private-observation consistency, and previous R34 reviewer. A fresh run must pass four original strict R25/R32/R33/R34 reviewers. R35's host reducer uses the unchanged SHA-pinned R27 parser. The stdout application log and stderr QEMU trace are separated to avoid exposing the raw trace. The shareable R35 summary reports aggregate counts and hashes only. Keep `R35-QEMU-GUEST-SYSCALLS.PRIVATE.log` and `R35-OBSERVATIONS.PRIVATE.json` local.

Docker **application execution** preserves `--network none --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 96 --memory 768m --cpus 1 --tmpfs /tmp:rw,nosuid,nodev,size=160m`. The existing R13 stage and all sources are bound read-only. The only host-writable location is a fresh results directory. Cold image builds may retrieve Debian packages before the networkless application run.

## Mac command

```sh
cd ~/Downloads
unzip pw3-os-r35-workload-file-trace.zip
cd pw3-os-r35-workload-file-trace
python3 -m unittest discover -s tests -v

./run-r35-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r32-inkaway-persistence" \
  "$HOME/Downloads/pw3-os-r32-inkaway-first-run/R32-RESULT-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r33.1-pdf-render-arguments-fix" \
  "$HOME/Downloads/pw3-os-r33.1-offscreen-first-run/R33-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r34-readerui-import-preflight" \
  "$HOME/Downloads/pw3-os-r34-readerui-import-first-run/R34-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-SUMMARY.json" \
  "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-SUMMARY.json" \
  "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-OBSERVATIONS.PRIVATE.json" \
  "$HOME/Downloads/pw3-os-r35-workload-trace-first-run"

cat "$HOME/Downloads/pw3-os-r35-workload-trace-first-run/R35-SUMMARY.json"
```

**Expected only after user ARM run:** `R35_GUEST_WORKLOAD_TRACE_CAPTURED`. Any failure leaves the R25/R27/R32/R33/R34 original passes and outputs untouched. Share only the summary, never the full raw trace or private path inventory.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.
