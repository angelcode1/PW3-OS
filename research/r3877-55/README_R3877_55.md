# R3877.55 — Alpine BusyBox entropy configuration and upstream fallback source

**Research/educational only. `NOT_BOOTABLE` is immutable.** This is a Mac-only public-source audit. The auditor makes no network calls, executes no ARM binaries, invokes no Docker, and does not contact the Kindle. The opt-in fetcher downloads five **public text files** using HTTPS certificate verification; it never downloads or modifies firmware.

## Prior observed result

R3877.54 user-reported Mac result: `PASS_PINNED_BUSYBOX_DIRECT_ELF_ENTROPY_INDICATORS_ONLY`, exit 0. The pinned dynamic ELF imported `syscall`, not directly `getrandom`/`getentropy`, and contained `/dev/urandom` bytes. Its BusyBox SHA-256 was `df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c` and its musl loader SHA-256 was `2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990`. No QEMU runtime entropy test was performed at R54.

## Scope and key hypothesis

At pinned Alpine `alpinelinux/aports` commit `35f5eb2864e50dd4448758d31f3e2a32f733ab84`:

- `main/busybox/APKBUILD` identifies BusyBox `1.37.0-r31` and copies the named `busyboxconfig` into the normal dynamic build.
- Both `busyboxconfig` and `busyboxconfig-extras` have `# CONFIG_SEEDRNG is not set`.
- Normal `busyboxconfig` has `CONFIG_ASH_RANDOM_SUPPORT=y`, while extras disables it.
- In the upstream BusyBox mirror at tag `1_37_0`, `miscutils/seedrng.c` **contains** an `ENOSYS` fallback from `getrandom` to `/dev/urandom`; because the Alpine recipe disables `seedrng`, **do not credit the disabled applet with providing the installed binary's entropy fallback**.
- The upstream shell `$RANDOM` source is a pseudorandom facility, **not** a cryptographically secure randomness or kernel entropy fallback.

Five paths have exact Git blob IDs hardcoded in the Python auditor. The program computes the full Git blob SHA-1 before parsing. Altered or missing source, changed configurations, or a changed R54 evidence result leads to HOLD. A PASS is `PASS_PINNED_ALPINE_BUSYBOX_SEEDRNG_DISABLED_AND_UPSTREAM_FALLBACK_SOURCE_ONLY`; it is **not** a signed APK proof, patched-build reproduction, installed binary applet-list proof, or target runtime test.

## Run on Mac

Extract the ZIP into a fresh `~/Downloads/pw3-r3877-55` directory, then:

```zsh
cd ~/Downloads/pw3-r3877-55
shasum -a 256 -c SHA256SUMS_R3877_55.txt
python3 -B -m unittest -q test_r3877_55.py

# No-input preflight: expected HOLD, exit 2, no network and no Docker.
python3 -B pw3_r3877_55_busybox_seedrng_source_audit.py

# Public source fetch: explicitly contacts only raw.githubusercontent.com.
sh FETCH_R3877_55_PUBLIC_SOURCES.sh sources

setopt pipefail
python3 -B pw3_r3877_55_busybox_seedrng_source_audit.py \
  --source-dir sources \
  --r54-report R3877_54_USER_REPORTED_SELECTED_PASS.json \
  | tee r3877_55_result.json
print "R3877_55_EXIT_CODE=$?"
```

Send the JSON and exit code. The source fetch is allowed only for public text, not user data, proprietary source, or the running Kindle firmware.

## Remaining unanswered questions

The exact running Alpine BusyBox package revision has not been re-read from the pinned local image's package database in this stage. Even if the recipe and source match, they do **not** prove binary-to-source reproducibility or presence of specific applet code in the stripped ELF. The observed `/dev/urandom` byte string remains unattributed. Generic `syscall` imports may have unrelated callers. The `getrandom` availability and any security-sensitive entropy fallback on real Linux `3.0.35-lab126` are unverified. No on-device binaries, boot changes, or firmware writes are authorized. Recovery and musl runtime compatibility remain open. Overall hold: `NOT_BOOTABLE`.
