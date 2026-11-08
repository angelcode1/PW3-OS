# PW3 R3877.54 — pinned BusyBox ELF entropy-import audit

**Research/educational only. Immutable `NOT_BOOTABLE`.** This is a **static, off-Kindle binary audit**. It does not execute ARM code, test kernel syscalls, replace the Kindle userland, or modify firmware/boot. It does not prove that application-level entropy fallback exists or is unnecessary.

## Background

User-reported Mac R3877.53 returned `PASS_PINNED_PUBLIC_LINUX3_ENTROPY_ABI_AND_MUSL_CALLPATH_SOURCE_ONLY`, exit 0, after validating six public Git blobs. The public Linux 3.0 ARM source has no standard `getrandom` syscall; musl 1.2.6 `getrandom()` and `getentropy()` lack an internal device fallback. The libc startup stack-canary code can read `AT_RANDOM` independently. **None of this proves** runtime syscall availability on the user's running Kindle or identifies all entropy paths taken by BusyBox.

The next useful, bounded step is to inspect **the exact Alpine BusyBox ELF already used for the R47–49 QEMU tests**, rather than infer application behavior from musl sources.

## Strict input pins

Reuses an unchanged, included R3877.48 inspector module with its exact **SHA-256 `61b42893aa1707e74ddafba5907c380ab65aa286bf233328f19128b16e9d835a`**. It validates:

- Parent image **tag**: `pw3-r3877-signed-alpine:3.24.3-armv7-dc1ddfaf03ed`
- Parent image **ID**: `sha256:c732b1bb478555ebb81e01632b519b712bd32b262d80af8bfbed2940602d397a`
- BusyBox **SHA-256**: `df4dd71f89214032872e60328f3af03faf35e344f6fa5493656d8775d35e930c`
- musl loader **SHA-256**: `2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990`
- BusyBox: ELF32 little-endian ARM EABI5 hard-float, `PT_INTERP=/lib/ld-musl-armhf.so.1` and dynamic segment. Loader: ELF32 ARM ET_DYN, no interpreter.

R54 then safely parses the *undefined entries* in the `.dynsym` section of the exact BusyBox file. It prints **only** counts and the booleans for 10 allowlisted symbol names (`getrandom`, `getentropy`, `syscall`, `open`, `open64`, `openat`, `read`, `fopen`, `arc4random`, `RAND_bytes`). It also reports the presence/absence of four literal byte markers (`/dev/urandom`, `/dev/random`, `getrandom`, `getentropy`).

**Interpretation rules:** A string marker is not an executed code path or a safe entropy fallback. An undefined import is not proof that the function was called. **No imported symbol is not proof that direct assembly syscalls, internal libc calls, dynamically loaded code, or a linked wrapper are absent.** Failure to parse `.dynsym` returns HOLD rather than treating missing metadata as no imports. This is a narrow static binary-surface audit; it cannot establish `getrandom` ENOSYS handling on the Kindle.

## macOS verification (zero Docker)

```zsh
mkdir -p ~/Downloads/pw3-r3877-54
unzip -oq ~/Downloads/pw3-r3877-54-busybox-entropy-elf.zip -d ~/Downloads/pw3-r3877-54
cd ~/Downloads/pw3-r3877-54
shasum -a 256 -c SHA256SUMS_R3877_54.txt
python3 -B -m unittest -q test_r3877_54.py

# Default preflight MUST return exit 2/HOLD; invokes NO Docker/Kindle.
python3 -B pw3_r3877_54_busybox_entropy_elf_audit.py > r3877_54_preflight.json
print "R3877_54_PREFLIGHT_EXIT_CODE=$?"
```

## Optional stopped-only local Docker audit

**Only if you agree to creating a disposable, never-started container** from the existing pinned local Alpine image. It uses no image pull, no network, privileged mode, mounts, extra devices or host binfmt registration. The container is created with guest filesystem read-only, capabilities dropped, no-new-privileges, and pids limit; copies exactly two files to an auto-deleted Mac temporary directory, runs the host-only parser, removes the stopped container, verifies removal and unchanged parent ID.

```zsh
setopt pipefail
python3 -B pw3_r3877_54_busybox_entropy_elf_audit.py \
  --authorize-stopped-image-audit | tee r3877_54_result.json
print "R3877_54_EXIT_CODE=$?"
```

Narrow successful classification: `PASS_PINNED_BUSYBOX_DIRECT_ELF_ENTROPY_INDICATORS_ONLY`, exit 0. If image/ELF bytes differ, section headers missing, or cleanup cannot be confirmed, classification is `HOLD`, exit 2. A PASS is *not* any actual entropy fallback or syscall compatibility PASS.

Alternatively, if you already have the two **exact pinned copies** saved on your Mac from an older diagnostic, use `--busybox /path/to/busybox --loader /path/to/ld-musl-armhf.so.1` for entirely offline analysis, with no Docker. Do not install or run either binary on the Kindle.

## What happens next

Record the allowlisted static indicators. If imports or markers suggest entropy handling, audit the actual applet source and caller control flow with pinned source or run a tightly scoped, offline QEMU ENOSYS test under separate authorization. If no imports/markers appear, **do not** treat that as proof of `getrandom` independence; the broader application and distro initialization paths remain untested. ARM TLS/multi-thread behavior on physical Kindle, musl patched binary reproducibility, and recovery remain unverified.

Full stock kernel config stays local on Mac; no collection or export of secrets or Kindle identifiers. **`NOT_BOOTABLE` remains unchanged.**
