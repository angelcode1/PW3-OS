# PW3 R3877.28 — Signed musl package build-metadata and pinned recipe snapshot audit

**For research and educational purposes only. `NOT_BOOTABLE` is immutable.**

## Confirmed input

User-run R3877.27 passed with canonical patched-tree SHA-256:

`61bc0d7c9559ffb9c6d1f25a40f041a04391bd2960a0176ac65cc9fe4aae7b8e`

The source tree contains 2,899 entries (2,662 regular files, 237 directories); all six Alpine downstream patches and 26 hunks applied in memory, with seven changed files. The signed public musl package and loader were already checked in R3877.25. No source-to-binary rebuild has occurred.

## What R3877.28 does

1. Reverify all 13 musl source inputs and seven patched-file hashes, then require the original R3877.27 canonical source-tree digest. Never extract the musl tar to the host filesystem.
2. Read *five* public `APKBUILD` files from the exact pinned `alpinelinux/aports` snapshot. Verify each Git blob against its **hard-coded expected SHA-1** before parsing or reporting its declared `pkgver` and `pkgrel`. Check the `build-base` recipe's dependency list. These are **snapshot recipe versions**, not proof of the historical build machine's installed toolchain.
3. Revalidate the exact earlier public `musl-1.2.6-r3.apk` hash, signed repository index, signed APK, pinned signing-key bytes, and loader byte-match from R3877.25. Parse a small allowlist of `.PKGINFO` fields (`builddate`, `commit` and package identity) from the authenticated package. The signing-key pins are still anchored to a pinned Git repository snapshot, not an independently verified trust root.
4. Compare any **package-declared `commit`** to the pinned aports snapshot as metadata. A match is not proof that the builder checked out this source; a mismatch is reported rather than concealed. The package need not carry a `commit` field.
5. Report the still-unresolved build inputs: compiler and linker versions **on the original Alpine builder**, actual CFLAGS/LDFLAGS/environment, abuild version used, compiled binary reproducibility, source-to-binary equivalence, and vendor kernel runtime compatibility.

The script cannot recreate the Alpine builder and intentionally does not invoke a compiler, Docker, QEMU, an Alpine binary, SSH, kernel syscall probe, or any firmware/partition tooling. It never writes to Kindle storage. **It must not return a success code that implies binary reproducibility.**

## Run on Mac — reuse previously downloaded local files

```sh
mkdir -p ~/Downloads/pw3-r3877-28
unzip -oq ~/Downloads/pw3-r3877-28-build-provenance-inventory.zip -d ~/Downloads/pw3-r3877-28
cd ~/Downloads/pw3-r3877-28
shasum -a 256 -c SHA256SUMS_R3877_28.txt
python3 -B -m unittest -q test_r3877_24.py test_r3877_25.py test_r3877_26.py test_r3877_26_1.py test_r3877_27.py test_r3877_28.py

# Download only public Alpine build recipes to the Mac. Verify with the Python audit.
sh FETCH_PINNED_BUILD_RECIPES.sh recipes

set -o pipefail
python3 -B pw3_r3877_28_build_environment_inputs.py \
  --source-dir ~/Downloads/pw3-r3877-26/sources \
  --recipe-dir recipes \
  --apk ~/Downloads/pw3-r3877-24/public-musl/musl-1.2.6-r3.apk \
  --index ~/Downloads/pw3-r3877-24/public-musl/APKINDEX.tar.gz \
  --candidate-loader ~/Downloads/pw3-r3877-23/candidate/loader \
  --key-dir ~/Downloads/pw3-r3877-25/aports-keys \
  | tee r3877_28_result.json
printf 'R3877_28_EXIT_CODE=%s\n' "$?"
```

**Expected classification only after successful real input verification:**
`PASS_PINNED_RECIPES_AND_SIGNED_PACKAGE_BUILD_METADATA_ONLY` (exit 0). Missing or mismatched files yield `HOLD` (exit 2). No Kindle access is requested. GitHub Actions only runs synthetic offline tests; it cannot claim success on the real signed package.

## Why the proposed rebuild is still blocked

Snapshot source recipes can change **after** a package build. The version labels in `main/gcc/APKBUILD`, `main/binutils/APKBUILD`, `main/make/APKBUILD` and `main/abuild/APKBUILD` do not identify which binaries the original signed `musl-1.2.6-r3.apk` builder had installed. A reproducibility attempt should wait for a specifically pinned historical build environment and actual build flags, not substitute an unverified current toolchain.

The candidate's `musl-armhf` loader cannot be directly linked against Kindle stock `armel` soft-float/glibc KOReader binaries. Bootloader provenance, recovery, live kernel syscall dispatch and musl runtime remain unverified. `NOT_BOOTABLE` remains enforced.
