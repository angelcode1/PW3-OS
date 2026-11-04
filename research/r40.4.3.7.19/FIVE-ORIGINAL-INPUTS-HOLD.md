# R40.4.3.7.19 — original R40.1/R40.2/R40.3 evidence recovery HOLD

User ran exact-source no-clobber recovery in both `check` and `run` modes. Both refused **before any source fetch, regeneration, stage modification or QEMU** with five original inputs unavailable at their expected paths: `R40.3-R26-HASH-SUMMARY.json`, `R40.1-PRIVATE-CROSSWALK.json`, `R40.1-SUMMARY.json`, `R40.2-PRIVATE-CWD-CROSSWALK.json`, `R40.2-SUMMARY.json`.

The last R3719 audit separately verified the original 2,070-entry R26 stage content as `ALL_RECORDED_ENTRIES_MATCH_UNAUTHENTICATED`; original R3718.1 source-pinned menu-selected synthetic ARM workflow PASS is unaffected. Prior R40.4.0 static evidence is **historical aggregate evidence only** until exact files are recovered or a fresh original-source graph is independently regenerated. Do not fabricate prior private crosswalk records or claim new full dependency closure.

Prepared a standalone filename-only, read-only local five-input finder: `R4043719-FIND-ORIGINAL-FIVE-READONLY.py`, SHA-256 `21c95851d46e37f0b96f4bf8c312df30b80ae1419c65ddcaf0892d35e36753df`; 11/11 local host tests PASS. It scans bounded Downloads directories, prunes staged rootfs, refuses symlinks, recognizes exact and numbered alias filenames, checks original R40.3 hash summary and R40.2 private/public SHA pins, and prints only fixed category labels. An R40.1 candidate is **unverified** pending original validators. User-side finder **not yet executed**. It never modifies files or runs QEMU.

If originals cannot be found, do not weaken old R403/R4040 source pins. A future independent R3718.1 trace-observation audit can collect *new* observed-file evidence under original R26 stage validation, while maintaining the old 347-file union as a historical baseline that is **not** recomputed without original path-level evidence.

No device access, stage pruning, boot, firmware writes, source provenance authentication or dependency closure. Preserve all 1,101 historical unobserved staged regular files and 976 older UNKNOWN_HOLD entries. Research/educational use only. **NOT_BOOTABLE**.
