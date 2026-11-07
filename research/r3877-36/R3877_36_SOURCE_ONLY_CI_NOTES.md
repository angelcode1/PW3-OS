# R3877.36 CI scope

All repository CI tests are **synthetic**, offline and host-only. The 1.64 MB public log must not be checked into the repo, nor are any generated linker tokens or paths. A synthetic regression pass does not validate the real public log. The user's Mac must run the exact-hash verifier for that evidence. The GitHub Actions job invokes only Python unit tests and the mandatory missing-log refusal check; no ARM build, SSH, Docker or device access.

Immutable safety hold: `NOT_BOOTABLE`.
