R3877.39 offline regression tests use synthetic records only. The real musl
builder log is intentionally not committed and is not available in CI. CI
must not claim the signed loader is reproducible, or that it ran on Kindle.
The real-log test requires the user to run the pinned analyzer locally.
Immutable hold: NOT_BOOTABLE.
