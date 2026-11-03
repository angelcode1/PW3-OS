# R40.4.3.2 — staged Canvas-model stroke/atomic-save/reload offline ARM trial

**2026-11-03. 59/59 synthetic host regression tests PASS; new ARM/QEMU model/storage execution PENDING. NOT_BOOTABLE.**

The user's R40.4.3.1 staged-source audit found an actual `Storage.writeAtomic` destination-removal fallback. The next test therefore exercises storage only in an isolated guest sandbox: stage-sourced `ink/canvas.lua` → `Canvas.new` → `startStroke/addPoint/finishStroke` → stage-sourced `ink/project.lua:save` → stage-sourced `ink/storage.lua:writeAtomic` → `Project.load` to confirm a single persisted operation. **This is not a genuine InkAwayView, UIManager, stylus/gesture event, or FileManager lifecycle test**. It must not be called a view/canvas GUI PASS.

**Source release:** `pw3-os-r40.4.3.2-model-storage-trial.zip`, SHA-256 `2c7970087295b2c89baf19b3343e9dab8755805e5d3e35253980b0bec96d2c23`; 11 ZIP entries, 10 checksum-manifest members, CRCs and SHA-256 digests verified, 59 host tests PASS. All runnable scripts and tests are in this separately versioned conversation ZIP. See `README-R40.4.3.2.md` inside it for exact Mac commands. The GitHub status includes no private stage source files or path logs.

**Hard gates:** before Docker, rehash all original R26 stage entries and revalidate the previous R40.4.3.1 private source map and original source pins. Docker uses only the previously-built `pw3-r394-reopen-trial` image, network disabled, stage bind readonly, release bind readonly, dropped capabilities, unprivileged UID/GID, and synthetic tmpfs HOME. Guest Lua wrappers reject writes/renames/removes outside `/tmp/r40432-ko-home/`, device/proc/sys/stage reads through those wrappers, and shell escapes. Independent reviewer replays the old pinned R40 syscall decoder from separate QEMU stderr and guest stdout, requires exact model/save/reload markers, QEMU zero exit and decoded write/rename confined to HOME, and refuses any decoded unlink. **Partial QEMU syscall decoding means this is not full path isolation proof or independent runtime dependency closure.**

No direct physical Kindle, boot, firmware, hardware writes, source modification, stage pruning or new optional puzzle integration. Model/storage test has not run yet. If it fails, leave the private traces and original stage unchanged; do not manufacture PASS.


## User-reported R40.4.3.2 offline ARM execution (2026-11-03)

The user ran the versioned, source-pinned release and reported **59/59 host tests PASS**, `R40432_STAGED_SOURCE_AND_R26_PREFLIGHT_PASS`, then the independent Python review printed `R40_4_3_2_STAGED_CANVAS_MODEL_STORAGE_ARM_PASS` followed by the runner's final `...; VIEW_NOT_TESTED; NO_PRUNING; NOT_BOOTABLE`. An earlier Docker daemon unavailable refusal was resolved before this successful run; it was an environmental failure and does not count as earlier guest evidence.

**Evidence tier:** terminal-reported review success only until `R40432-REVIEW.json` and `R40432-SUMMARY.json` are supplied and their fields reconciled. Raw guest syscall trace and actual stage files are retained locally and have **not** been independently replayed by the assistant. No staged-file union recomputation has occurred. A model/storage synthetic QEMU PASS must not be mislabeled as a genuine InkAwayView pen/touch/UIManager drawing application PASS; GUI canvas→stroke→save→FileManager return stays `NOT_TESTED_HOLD`.

Still `NOT_BOOTABLE`; no rootfs pruning, device access, hardware action, firmware write, or new optional puzzle package.
