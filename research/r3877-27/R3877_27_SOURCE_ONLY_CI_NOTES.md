# CI safety and expected evidence

CI runs only Python synthetic fixtures and checks missing-input refusal. It never downloads source archives, connects to any target, executes ARM code, or measures the R3877.27 real source-tree digest.

A `PASS_PINNED_PATCHED_SOURCE_TREE_FINGERPRINT_ONLY` result must originate from the user's Mac, with the pinned real source files present, and is only evidence of a canonical **source** fingerprint.

`NOT_BOOTABLE` is unconditionally preserved. No Kindle writes or boot tests are authorized.
