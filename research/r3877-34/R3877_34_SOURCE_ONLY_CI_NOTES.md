# CI scope

Run seven Python unittest modules in `research/r3877-34`. They use **synthetic log inputs** and a small JSON summary, never the 1.64 MB public log, and do not run compilers or Kindle/ARM code. Successful CI verifies parser regression behavior only; R3877.34 must be run separately on the real, pinned Mac-local log. Never mark historical shell argv, loader reproducibility, recovery or Kindle runtime as verified from CI.
