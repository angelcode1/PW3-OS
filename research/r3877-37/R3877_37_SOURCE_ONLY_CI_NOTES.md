# R3877.37 offline test scope

CI runs the synthetic Python regression tests and missing-file refusal. It **does not** download the 1.64 MB builder log and does **not** prove that the real-line classifications pass. The Mac-local audit must independently report exit 0 and the hash-pinned success result.

No containers, ARM execution, Kindle access, firmware writes, installs or boot attempts. `NOT_BOOTABLE` stays enforced.
