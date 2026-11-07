# R3877.25 — Host-only Alpine APKv2 RSA signature verification

**Research and educational purposes only. `NOT_BOOTABLE`.** No Kindle SSH, kernel calls, boot, firmware writes, eMMC reads, image execution, Docker start or APK installation.

## Observed baseline (reported by the user, R3877.24)

- `PASS_INDEXED_PUBLIC_MUSL_LOADER_BYTES_MATCH_ONLY` and exit 0.
- Candidate loader = public Alpine ARMv7 `musl-1.2.6-r3.apk` loader, SHA-256 `2acf3c82bc97b496c40e1d5007d4258570c8df0edc45793d6651a352fb778990`.
- Package SHA-256 `9fca75b09538f9788b1ca800d56cd93dd4d584fac76a57c959666a9a0b93d397`; index SHA-256 `5a709ea29c02499f799f2e56a2af7fe95f4dd6859867bbe65a0aa597fe294140` at time of run. **The repository index can update over time; never assume the index's SHA256 must remain identical.**
- Package `datahash` and index `Q1` control checksum passed, but index/package signatures were *not yet verified*.

## New checks

The new analyzer uses R3877.24's bounded byte-for-byte comparison, then checks Alpine APKv2 signatures over **compressed gzip members**, without extracting any tar paths to disk:

1. Parse signed `APKINDEX.tar.gz` as a signature gzip stream and an index gzip stream. Authenticate the **second compressed stream** with OpenSSL RSA PKCS#1 v1.5 and the declared algorithm (`RSA` = SHA-1, `RSA256` = SHA-256, `RSA512` = SHA-512).
2. Parse signed `musl-1.2.6-r3.apk` as three streams. Authenticate its **compressed control stream**; R3877.24 independently checks that the control `.PKGINFO`'s SHA-256 datahash matches the compressed data stream.
3. Require signatures to identify a public signing-key filename from a limited **pinned Git repository key set**. Verify the exact key bytes by Git-blob SHA-1, anchored to `alpinelinux/aports` commit `35f5eb2864e50dd4448758d31f3e2a32f733ab84` on `3.24-stable`:
   - `alpine-devel@lists.alpinelinux.org-616adfeb.rsa.pub`: blob `bb15efe96d7c95a0602b243ce0848aa42cf80020`
   - `alpine-devel@lists.alpinelinux.org-6165ee59.rsa.pub`: blob `f2165aebadab1c1e43798f1278c3897d85f16da1`
4. For successful index and APK RSA signatures, report `PASS_PINNED_APORTS_SIGNATURES_AND_PUBLIC_LOADER_MATCH_ONLY`.

Unknown signer, unsigned archive, altered bytes, missing key, changed blob or failed verification => **HOLD**, exit 2. The program never updates or trusts local APK keys automatically. The key pin itself is **not an independently verified trust root**; it relies on the public project's pinned Git source and HTTPS to acquire the keys. Do not confuse this with source-to-binary reproducibility or Amazon vendor-kernel runtime compatibility.

## Run on macOS — reuse existing R3877.24 downloads

```sh
mkdir -p ~/Downloads/pw3-r3877-25
unzip -oq ~/Downloads/pw3-r3877-25-signed-apk-provenance.zip -d ~/Downloads/pw3-r3877-25
cd ~/Downloads/pw3-r3877-25
shasum -a 256 -c SHA256SUMS_R3877_25.txt
python3 -B -m unittest -q test_r3877_24.py test_r3877_25.py
sh FETCH_PINNED_APORTS_KEYS.sh aports-keys

set -o pipefail
python3 -B pw3_r3877_25_signed_apk_provenance.py \
  --apk ~/Downloads/pw3-r3877-24/public-musl/musl-1.2.6-r3.apk \
  --index ~/Downloads/pw3-r3877-24/public-musl/APKINDEX.tar.gz \
  --candidate-loader ~/Downloads/pw3-r3877-23/candidate/loader \
  --key-dir aports-keys | tee r3877_25_result.json
echo "R3877_25_EXIT_CODE=$?"
```

OpenSSL is required as a **Mac host command**. Its input files are temporary and automatically removed. `test_r3877_25.py` generates ephemeral RSA test keys in a host-side temporary directory; the real audit only verifies public keys. No ARM code executes. The tests use synthetic APKv2 streams, not the downloaded real Alpine package; a real package pass requires running the above on Mac.

If the signer is different from the two pinned key names, the intended outcome is HOLD. Do not disable signature checks or use a substituted key; return the classification and we can add a separately pinned legitimate key after checking its source provenance.

## Conclusions remaining unavailable after successful run

`source_to_binary_reproducibility_verified=false`, `target_musl_runtime_verified=false`, `vendor_kernel_dispatch_verified=false`, `recovery_verified=false`, and `immutable_hold=NOT_BOOTABLE`. The stock KOReader ARM soft-float/glibc libraries remain incompatible with direct in-process linking against the Alpine ARM hard-float/musl candidate.

Reference: https://man.archlinux.org/man/apk-v2.5.en and https://man.archlinux.org/man/extra/apk-tools/apk-keys.5.en
