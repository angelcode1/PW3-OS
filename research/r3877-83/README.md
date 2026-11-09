# R3877.83 — pinned-glibc LuaJIT one-shot test (source package delivered in conversation)

**STATUS:** host-only synthetic regression tests 18/18 PASS. **Kindle execution NOT RUN.** This document records the test plan and references the locally generated source archive; the tested source archive has not been added as separate GitHub source files by this commit.

Test package filename: `pw3-r3877-83-one-shot-glibc-luajit.zip`  
ZIP SHA-256: `bcddf7b82033b647e9e7a2e33545d964a4f548911707ceb4b49bb64f473c9039`  
Seven ZIP members: README, R3877.82 counts-only evidence, R3877.83 Python runner, R3877.83 synthetic tests, and two unchanged pinned R3877.81/R3877.82 parser sources, plus checksum manifest (total seven members).

## Verified existing evidence

R3877.82 identified 13 required GNU symbol-version names, 13 static name matches, zero missing versions, and zero VFP-attribute warnings. All six selected ARM EABI5 ELF objects have soft-float flags; `.ARM.attributes` VFP argument tags were absent. The R82 report retains untrusted/unknown LuaJIT RPATH elements and **does not** prove binding, dynamic loader execution, or complete ABI correctness.

## Test restrictions

The local runner validates the original stage files and their published dependency/ABI metadata. Only upon explicit `--acknowledge-one-shot-kindle-glibc-test` and successful offline review will it SSH into the Kindle, unpack six selected files to an already-mounted executable tmpfs, verify their hashes, and invoke the **relocated** glibc loader with RPATH inhibition, cache inhibition, an explicit library path and `--list`. It must confirm all library mappings are inside the private RAM directory **before** executing the non-graphical LuaJIT `io.write()` test. There are no GUI, hardware, boot, init, chroot, mounts or firmware changes.

Run the bundled README's **`--review-only` first**. No automatic retries. Physical restore and standalone boot remain unverified; `NOT_BOOTABLE` is unchanged.

Source archive is provided separately in this ChatGPT conversation (not in the repository). **Do not replace the user-staged R13 rootfs with the stock Kindle filesystem, commit private libraries or load the KOReader GUI during this test.**
