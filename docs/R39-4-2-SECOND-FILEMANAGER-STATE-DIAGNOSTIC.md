# R39.4.2 — second returned FileManager state diagnosis

**2026-11-02 status: 334/334 host regressions PASS; ARM/QEMU diagnostic PENDING; NOT_BOOTABLE.**

## Reason for this experiment

The original R39.4.1 ARM/QEMU run passed the original independent R25 baseline, genuine first PDF page rendering/page turn/Home return, and **second** ReaderUI initialization, actual second PDF scroll drawing on page 1, and a second Home engine-release check. The genuine second `FileManager:showFiles` returned, then the experimental wrapper failed with `R39.4 second FileManager not active` *before* recording the second FileManager success marker. Original strict reviewer `FAIL`; neither a successful second FileManager return nor final Close is verified.

The prior R39.4 original failure was at the synthetic Input lifecycle and was fixed in R39.4.1. The new failure has not yet been isolated to a single predicate, and cannot legitimately be labeled a production KOReader defect.

## Bounded source-only change

R39.4.2 changes **only the experimental forked test guard** `r394/loop_guard.lua`, its checker/source pin, and adds `r394/analyze_second_filemanager.py`, host regressions and documentation. The genuine `FileManager:showFiles`, ReaderUI, PDF engine, DocumentRegistry, UIManager, event limits and original `r394/review_r394.py` remain unmodified.

Exactly one snapshot `R39_4_2_SECOND_FILEMANAGER_STATE` is printed *after* the genuine FileManager constructor returns, **before the original unchanged strict assertion**. It reports the presence of the second FileManager and chooser, categorical chooser path (`expected`, `trailing_slash`, `other_home`, `outside_or_unset`, `unavailable`), bounded UI widget stack depth/index, whether FileManager or a prior reader owns the top widget, and whether the forbidden-operation counter remains zero. No files or objects are changed or released; no raw document paths or device data are printed.

The separate analyzer requires a fresh original R25 PASS, pinned R39.4.2 preflight, a genuine second PDF draw and second Home release state, the **unchanged R39.4 strict reviewer FAIL**, and the exact second FileManager assertion. It explicitly outputs only `R39_4_2_SECOND_FILEMANAGER_STATE_DIAGNOSTIC_CAPTURED`, `diagnostic_only=true`, `new_arm_success_claimed=false`, `second_filemanager_return_verified=false` and `root_cause_determined=false`. Any contradiction or missing/duplicate evidence is rejected. **The new ARM run is expected to fail closed; do not substitute the diagnostic verdict for the strict reviewer.**

## Release provenance

Research-session archive `pw3-os-r39.4.2-second-filemanager-state-diagnostic.zip` (56 entries, CRC PASS), SHA-256 `cef7c172f238e52ff40f4199da37c05be1ce35441cec4b786b7b40271afc30e9`.

- Experimental guard SHA-256: `70b2617ec9739106c499294d545a5908dd8a0683b4feb47eb661cf06d40bc139`
- Analyzer SHA-256: `16b17453bfe1c8539c434c6ae5db97c6452e8ffbd00d854c033c8cbeb05ead2e`
- Original strict reviewer SHA-256, **unchanged**: `b2d7a44f1acedeb6ec9899074e91bb0f4d3a4fed63b15d0816ff9d7b99d51e57`
- **334/334 Python host tests PASS** (311 inherited plus 23 new). Python compilation, POSIX shell syntax and 55-entry new SHA-256 manifest PASS. ARM/QEMU has not run for this diagnostic in this research session.

For the exact nine-argument Mac Docker run, new output directory, diagnostic analyzer and evidence ZIP, see the archive's `README-R39.4.2.md`. Old source/manifests are included as historical artifacts; verify **`SHA256SUMS-R3942`** for the new release.

Do not prune any of 976 staged `UNKNOWN_HOLD` files or alter the existing Kindle installation. **NO_DEVICE_ACCESS; NO_FIRMWARE_WRITES; NO_HARDWARE_ACTIONS; NO_BOOT; NO_PRUNING; NOT_BOOTABLE.** No physical Kindle operation, independent boot, full dependency closure or global migrations are established.

## 2026-11-03 — actual R39.4.2 ARM/QEMU diagnostic captured

The user supplied `R39.4.2-ARM-EVIDENCE.zip` (SHA-256 `fa46b4ad3c397f18a76f267f74518d236602084047875c58e142fa84210cdeab`), including the independent fresh R25 strict reviewer PASS, source preflight PASS with `r3942_second_filemanager_snapshot_pinned=true`, original strict R39.4 `FAIL`, original guest log and the separate diagnostic JSON. ZIP CRC passes and the standalone JSON agrees with the archive.

After genuine second scroll draw and second Home with released raw PDF engine and empty registry, the post-`stock_show` snapshot was:

```text
R39_4_2_SECOND_FILEMANAGER_STATE
fm_present=true chooser_present=true chooser_path_kind=expected
stack_depth=1 fm_stack_index=1 top_widget_present=true
top_is_fm=true top_is_second_reader=false top_is_first_reader=false
denied_zero=false
```

The separate analyzer concluded `failed_original_predicates=["denied_operation_recorded"]`, with `root_cause_determined=false` and `second_filemanager_return_verified=false`. The original strict reviewer `FAIL` remains unchanged because the internal blocked-operation counter `stats.denied` is nonzero, despite the FileManager being genuinely present and active. A blocked operation may have raised an error caught internally by KOReader, but this has **not been proven** and must **not** be presumed acceptable. See [R39.4.3](R39-4-3-FIRST-DENIAL-PROVENANCE.md) for first-denial provenance without a bypass or reset.

