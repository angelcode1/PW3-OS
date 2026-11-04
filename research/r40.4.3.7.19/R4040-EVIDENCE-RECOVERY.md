# R40.4.3.7.19 — recover missing R40.4.0 static evidence

The user ran locator V2: original audit SHA pin matched and `R4040_SUMMARY=NOT_FOUND_HOLD`. This is a source-evidence retrieval HOLD, **not** evidence of a changed 2,070-entry stage: original R26 content PASS and R3718.1 synthetic ARM PASS remain separately valid.

Host-tested recovery ZIP `pw3-os-r40.4.3.7.19-r4040-recovery-noclobber.zip`, SHA-256 `6b951e5523adfb8e74779bb87bf205a525e75503d275dba4f118a401cff7174b`, source `R4043719-RECOVER-R4040-NOCLOBBER.sh` SHA-256 `261dff52064e2b2afe0bf843aa71d9a1598135d1134de54807eaa339e684af30`. ZIP integrity, clean extract manifest, shell syntax and 20/20 local host tests passed; **Mac recovery NOT RUN**.

The runner's `check` mode only verifies existing source pins and local private evidence with no network or file writes. `run` requires those gates, clones public source at exact pinned commit `e66aedfd459563692dd0488cd0da3cb33fa110ec` into a fresh no-overwrite Downloads folder, verifies original R40.4.0 source/test manifest, and runs unmodified `r404/static_graph.py` with original R26/401/402/403 inputs to generate new summary/private graph locally. It then reruns unchanged R3719 audit with explicit new filenames. It does not fabricate the missing original graph, and may HOLD when private crosswalks are missing.

All source, private input, guest trace and graph paths remain on the Mac. No stage changes, QEMU run, boot, firmware writes, physical device access or pruning. 1,101 unobserved staged regular files and 976 historic UNKNOWN_HOLD retained; unauthenticated R26 provenance and incomplete loader/decoder closure still unresolved. Research/educational purposes only. **NOT_BOOTABLE**.
