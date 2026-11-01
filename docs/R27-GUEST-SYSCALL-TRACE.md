# PW3-OS R27 — guest syscall file-access trace (offline ARM/QEMU candidate)

**2026-11-01 verified state:** R25.3 genuine `reader.lua` → FileManager → Ink Away-owned plugin → UIManager run → synthetic Close → Generic:exit path **ARM/QEMU PASS** (user-supplied). R26 static rootfs catalog **user-executed** with 2,070 entries, 83 ELF objects, 0 ELF parse errors, 0 unresolved staged DT_NEEDED name candidates. R26's 15-test run reported **one skip**. **R27 is host-tested, NOT YET EXECUTED ON ARM/QEMU.**

## Tool and boundary

R27 is a small, independent source-only harness. It consumes the unchanged user's R13 stage, R24.3.1 source tree (including the R25.3 Dockerfile and Lua), successful R25.3 reviewer JSON and R26 summary. It checks R26's stage-sentinel checksum and R25 reviewer, runs the same five source audits to distinct output files, and replays the exact synthetic R25.3 lifecycle with `QEMU_STRACE=1`, which is documented for QEMU user-mode syscall tracing. [Official QEMU documentation](https://www.qemu.org/docs/master/user/main.html) notes that its strace-like output is **incomplete** and is not equivalent to host `ptrace` tracing.

The QEMU runtime keeps `--network none`, `--read-only`, `--cap-drop ALL`, `--security-opt no-new-privileges`, `--pids-limit 96`, 768 MB memory cap, one CPU, read-only `/stage`, no host/Kindle device mounts, and a 160 MB disposable `/tmp` home. Docker *image build* may need Debian package downloads when uncached; the **application execution** is networkless.

The QEMU guest syscall log is **private** and can contain absolute paths; the secondary normalized path observation file is **private** too. The only artifact proposed for sharing is `R27-SUMMARY.json` with aggregate counts, scope flags, and input sentinel hash. The reviewer requires a replayed strict R25.3 lifecycle PASS and at least one parsable successful guest file open; otherwise emits `R27-FAIL.json`. Successful guest file opens and failed lookups are useful evidence, **not** a complete dependency closure, and in-memory synthetic `/proc/meminfo` is *not* a kernel-file open. Host-QEMU's own files and kernel firmware requests are outside the trace.

Host-only source tests: **21/21 PASS**, shell syntax PASS, Python syntax PASS; ZIP checksum and all four internal payload SHA-256 digests verified. No Docker/QEMU execution was available in the authoring environment. Source-only ZIP in conversation:

`pw3-os-r27-dynamic-file-trace.zip` — SHA-256 **`b548ef55007ae81c7dec2e8eba0eecda32101ae7a0843fdaf3dfd88cb461204a`**. The archive contains the independent shell runner, guest-trace reducer/reviewer, tests and README; it contains **no staged binaries, private device captures or Amazon firmware**.

## Mac invocation

```sh
cd ~/Downloads
unzip pw3-os-r27-dynamic-file-trace.zip
cd pw3-os-r27-dynamic-file-trace
python3 -m unittest discover -s tests -v

./run-r27-docker.sh \
  "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core" \
  "$HOME/Downloads/pw3-os-r26-static-results-first-run/R26-SUMMARY.json" \
  "$HOME/Downloads/pw3-os-r24.3.1-audit-output-fix/src/r21-filemanager-core/results-r25.3-first-run/R25.3-RESULT-REVIEW.json" \
  "$HOME/Downloads/pw3-os-r27-trace-first-run"

cat "$HOME/Downloads/pw3-os-r27-trace-first-run/R27-SUMMARY.json"
```

A successful **user-side** trace should report `R27_GUEST_SYSCALL_TRACE_CAPTURED`; if it fails, review only the local `R27-FAIL.json` and R27 R25 reviewer, keeping full raw trace private. The script **refuses any existing R27 results directory**. Preserve all R25.3/R26 outputs; do not run destructive commands.

## Non-claims and subsequent plan

- The R26 static stage's 2,070 entries are **present**, but their runtime use is not established by R26.
- If R27 succeeds, it will prove **only guest syscall file-access attempts within one synthetic replay**; an unopened file might still be required by a feature, fallback, recovery, kernel driver, suspend or charging. It does not certify removal or image deployment.
- R28 would correlate the private inventory and trace on the **user's Mac**, then build a **new** minimal Alpine rootfs from audited/licensed files. No pruning of the existing stage or Amazon stock firmware is authorized.
- Migrations remain deliberately skipped; no physical PW3 device calls, hardware refresh, firmware writes, bootloader changes, stock OS erasure or independent boot.

**Immutable hold:** `NO_FIRMWARE_WRITES_HOLD; NO_DEVICE_ACCESS; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`.
