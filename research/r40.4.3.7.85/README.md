# R3785 — User Mac result: signed Alpine virtual symlink endpoints

**Research and educational purposes only. No guest execution, stage writes, hardware actions, mapping, pruning or boot. Immutable NOT_BOOTABLE.**

## Verifications reported by the user (offline and online, exit 2 each)

- R3785 offline returned `R3785_VIRTUAL_ENDPOINT_OFFLINE_PREFLIGHT_NO_FETCH` and made no network request.
- R3785 online reran the R3782–R3784 pinned chain, checked Alpine **3.24.3 armv7** minirootfs's SHA-256 release record, GPG signature and published release-key fingerprint, and reproduced the baseline of 515 archive entries (83 regular bytes matching staged files, 96 directories present, 335 symlink entries).
- The 306 archive/stage symlink literals that differed (archive absolute vs stage relative) all resolved in the bounded virtual namespace resolver to the **same normalized final virtual path and endpoint type**: **305 regular files and one directory**. The 29 literally identical symlink members are omitted from the difference-specific resolver classification.
- **Zero** unresolved endpoints, different resolved virtual paths, cycles and root escapes. One archive and one stage traversal required multi-hop resolution. Host OS symlinks were **not followed**.
- The user-reported JSON is summarized in `USER-MAC-R3785-SELECTED-RESULT.json`; it is **not** the full original result. GitHub CI has no access to the user's original R13 stage or the downloaded signed upstream tar.

## Precise interpretation

This closes the previously observed 306 symlink-literal deviations as **structurally equivalent in the tested virtual rootfs namespace**. The original `complete_minrootfs_member_overlap` flag still reports false because the 306 *literal* targets differ. That boolean must **not** be re-labelled as true; instead, report virtual endpoint equivalence separately.

The GPG key fingerprint was compared against an Alpine-published value, but the release signer identity was **not** attested out-of-band. More importantly, exact source-to-stage overlap does **not prove** this Alpine candidate was the original R13 build input, nor authenticate the locally assembled R13 image. No guest runtime/chroot resolution, ELF loader, TLS, kernel ABI, hardware compatibility, recovery or boot status is proven.

The unrelated four APK-signed-payload disagreements from R3775 remain historical: **one regular file, three symlink target literals**. Whether the three package-level symlinks are among the 306 upstream-minirootfs conversions remains to be tested with appropriately authenticated original package payloads, if further testing is justified.

## Source bundle

The R3785 synthetic-host-test ZIP `pw3-r3785-signed-virtual-link-endpoints-readonly.zip` is identified by SHA256 `4c541460b35e4438f6dfc99c925edfc2833e9e961ceda09b7849af0d45ae81c2` (128/128 prior assistant host tests). The user-run results have now validated its online virtual endpoint inspection on the user's Mac. This evidence-only PR does not commit the ZIP or private stage.

**Current:** `HOLD` / `ORIGINAL_R13_IMAGE_PROVENANCE_UNAUTHENTICATED_HOLD` / `NOT_BOOTABLE`.
