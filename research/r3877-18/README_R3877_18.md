# PW3 R3877.18 — Read-only ARM ELF import/export and relocation candidates

**Research/educational use only. `NOT_BOOTABLE` remains immutable.** This is **not** a Kindle runtime test, an ABI-complete loader simulator, or authorization for firmware writes. The original R13 build stage is never accessed.

## Why this step

User-reported R3877.17.2 found 174/174 GNU version-name requirements and 48 valid `SHT_NOBITS` sections after correcting the local ELF parser. A matching version **name** does not demonstrate that an individual exported symbol exists with the correct version, or that a relocation can be applied.

This package reuses the **unchanged R3877.17.2 SSH collection code**. It reads the existing `/mnt/us/koreader/{fbink,luajit,libs/*.so*}` and the seven specific stock provider files, over one existing SSH connection, without changing the Kindle. The bytes are processed in memory on the Mac. No user books, settings or logs are requested. No new Kindle binaries run or get installed. No Docker is involved.

## Improvements

- Parse ELF32 little-endian ARM `SHT_DYNSYM`, `.gnu.version` (versym), `.gnu.version_r` (verneed), `.gnu.version_d` (verdef), and allocated `SHT_REL` / `SHT_RELA` entries, with bounded table lengths and symbol indices.
- Decode relocation **symbol references** and their version indices, rather than comparing version names alone.
- Match undefined strong/weak relocation-bound symbols to exported candidates in the transitive `DT_NEEDED` file set. For versioned imports, require the exact declared provider name and symbol-version match. Exclude hidden/internal exports and non-default versions for unversioned lookups.
- **Do not equate a candidate with actual binding**: loader search order, interposition, `dlopen`, relocation application, TLS and IFUNC semantics, imported symbols never referenced by these relocation sections, and kernel ABI remain unproven.
- Fail closed for missing strong export candidates or malformed ELF/relocation tables. Weak missing candidates are reported separately because a null weak reference may be legal.
- Recheck prior SHA-256 evidence on `fbink`, `luajit`, `libc.so.6`, the seven stock-provider identities and R3877.17.2 GNU version-name requirements.

## Run on macOS

```sh
mkdir -p ~/Downloads/pw3-r3877-18
unzip -oq ~/Downloads/pw3-r3877-18-symbol-relocation-candidates.zip -d ~/Downloads/pw3-r3877-18
cd ~/Downloads/pw3-r3877-18
shasum -a 256 -c SHA256SUMS_R3877_18.txt
python3 -B -m unittest -q test_r3877_15.py test_r3877_16.py test_r3877_17.py test_r3877_17_1.py test_r3877_17_2.py test_r3877_18.py

# Offline preflight: should print HOLD and exit 2 without SSH
python3 -B pw3_r3877_18_relocation_candidates.py

# Explicitly authorized single-SSH read-only audit
set -o pipefail
python3 -B pw3_r3877_18_relocation_candidates.py \
  --target root@192.168.8.102 \
  --port 2222 \
  --authorize-live-readonly-ssh \
  | tee r3877_18_result.json
echo "R3877_18_EXIT_CODE=$?"
```

This test **has not been executed against the physical PW3** by the package author. A successful output will say `PASS_SYMBOL_RELOCATION_CANDIDATES_METADATA_ONLY`. If strong candidate exports are missing, the result is `HOLD` with bounded `strong_missing_samples`. The command's exit status is **0** only for candidate metadata success; other outcomes exit **2**.

## Review restrictions

The target SSH host is pinned to the previously user-approved PW3 IP address; another target is refused. The shell script delegates only to unchanged, fixed-scope tar collectors. The Mac copies and parses files solely in memory; the package writes the JSON report locally only via the user's `tee` command. No source or guest image is altered.

## Remaining independent holds

- Runtime dynamic loader resolution and symbol relocation application
- Uncollected `dlopen` plugins/module closures and loader search ordering
- Real Kindle Linux 3.0.35 musl/syscall/TLS execution (candidate Alpine remains isolated)
- Original R13-stage provenance, recovery plan and boot validation

**`NOT_BOOTABLE`.**
