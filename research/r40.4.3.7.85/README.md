# R3784 symlink pattern corroboration and R3785 next host test

**Research and educational use only. Immutable NOT_BOOTABLE.**

## User-reported R3784 Mac result

The user verified the candidate Alpine **3.24.3 armv7** archive's release checksum and detached GPG signature, checked the published release-key fingerprint, and replayed the unchanged 515-member source-to-stage inventory. The candidate archive's **83 regular files matched SHA-256**, all **96 directories** and **335 symlink entries** were present, but only **29 symlink target literals** matched exactly. The remaining **306** archive links used absolute targets where stage links used relative targets, yet the two target literals normalized to the **same virtual rootfs-relative lexical path** for all 306.

These observations support a systematic absolute-to-relative symlink conversion. They **do not** establish that the target exists, that the complete symlink chain is resolvable, or that a real guest process interpreted either target using the assumed root namespace. They do not prove the candidate archive was actually used to assemble R13.

A selected-field summary of the user's separately reported offline and online JSON and the immutable safety flags is in `USER-MAC-R3784-SYMLINK-PATTERN-SUMMARY.json`. It is **not** a verbatim copy of the complete user result and GitHub cannot access the user's private stage.

## Next R3785 verifier (host-tested, Mac run pending)

The separately supplied local archive `pw3-r3785-signed-virtual-link-endpoints-readonly.zip`, SHA-256 `4c541460b35e4438f6dfc99c925edfc2833e9e961ceda09b7849af0d45ae81c2`, contains:

- Unmodified, exact-SHA-pinned predecessor R3782, R3783 and R3784 source scripts and tests
- R3785 bounded **virtual rootfs** symlink endpoint resolver and regressions
- Source/usage README, selected R3784 summary, SHA-256 manifest

The assistant-side host suite reported **128/128 synthetic tests PASS** (94 inherited and 34 new), clean extraction, all ZIP manifest hashes verified, and a missing-stage `HOLD`/exit 2 with no network attempt. This is **not** a Mac scan of the user's R13 stage and the independent verification of the candidate against user-stage endpoint semantics remains pending.

R3785 compares terminal entries of paths in two virtual namespaces without ever following a host symlink: `O_DIRECTORY|O_NOFOLLOW` parent FDs, `stat(follow_symlinks=False)`, `readlink(dir_fd=...)`, bounded link-hop count, root-escape and cycle detection. Outputs are aggregate and do not expose private paths, link targets, package names or staged file hashes.

A fully resolved match would extend the prior lexical equivalence finding to **structural virtual endpoint consistency** only. It would not authenticate the original R13 build input, attest release signer identity out of band, establish runtime ELF loader/ABI/TLS, prove kernel/chroot semantics, justify pruning or authorize device actions.

## Safety state

Older R3775 package-level differences remain one regular staged file and three staged symlink target changes versus signed package payloads. The assembled R13 source provenance and historical build commands are not authenticated. No stage changes, guest execution, Kindle device access, firmware writes, mapping, pruning, boot, or recovery actions are authorized. **NOT_BOOTABLE.**
