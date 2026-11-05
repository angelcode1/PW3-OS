# R40.4.3.7.39 — Static SONAME and transitive basename graph audit

**Host-only research. NOT_BOOTABLE.**

The user's R3738 audit found 12 requesting ELF objects with 19 DT_NEEDED
edges spanning six distinct basename literals, each with exactly one
regular ELF-header-compatible same-basename candidate. This does not
establish the dynamic loader's actual search path or symbol closure.

R3739 replays the SHA-pinned R3738 source and inherited R3737→R3736→
R3735→R3734→R3733→R3727→R3726 parent chain, requiring the same
12/19/6 stage baseline. It examines the six direct provider candidates'
bounded DT_SONAME and DT_NEEDED metadata and recursively examines only
unique regular header-compatible same-basename provider candidates,
with hard graph limits of 128 nodes and 1024 edges.

It aggregates SONAME equal/different/undeclared, transitive provider
missing/ambiguous/symlink/path-bearing categories, and graph cycles
(strongly connected components). It prints no guest paths, library
names, SONAME strings, symbol names, dynamic source strings or source
bytes. It does not execute ELF files, create symlinks, install
packages, modify rootfs, run QEMU, access the PW3, boot, flash or prune.

**Important:** A graph with no unresolved basename category would NOT
prove transitive runtime dependencies, loader search semantics,
symbol version matching, TLS support or kernel compatibility.
R3737's 632 undefined referenced symbol records and TLS relocation
types 17/18/19 remain unresolved. The single required guest
interpreter path remains absent. Original R26 source authentication,
historical hashes, hardware/recovery and future-image boot are held.
The future OpenSSH/SFTP/rsync package reservation is unchanged.

**Local:** 18 synthetic Python regression tests PASS; checksum/ZIP
integrity and clean-extraction tests PASS. The actual user Mac stage
has NOT been run for R3739. This release's Python source and tests are
in the downloadable chat ZIP (SHA256
`813423f20680e846dac1732cb75c3eb36f2eba0fedad383880dd865832f81999`),
not yet published as separate GitHub source. Do not claim CI PASS.

## Mac usage (no git or gh)

Download `pw3-r3739-transitive-soname-readonly.zip` to Downloads:

```sh
mkdir -p "$HOME/Downloads/pw3-r3739"
cd "$HOME/Downloads/pw3-r3739"
unzip -o "$HOME/Downloads/pw3-r3739-transitive-soname-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r4043739.py' -v
python3 -B R4043739-NEEDED-TRANSITIVE-SONAME-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send JSON `provider_soname_categories`, `provider_needed_basename_candidate_categories`,
`transitive_graph_regular_files_seen` and `provider_graph_cycles`.
If output is HOLD, preserve that hold. **NOT_BOOTABLE.**

## User Mac result

The user reported `STATIC_SONAME_AND_TRANSITIVE_BASENAME_GRAPH_CLASSIFIED_ONLY` with **12** requesting ELF objects, **19** direct DT_NEEDED edges and **six distinct library names**. All six direct, unique provider candidate files have SONAME matching their requested name; six provider ELF files were scanned, with **seven additional DT_NEEDED edges** and one regular header-compatible basename candidate for each. Graph cycles: **zero**. SHA-pinned R3738 and older source checks replayed. No private names or paths were exported. This is not proof of Linux loader search paths, real symbol version resolution, TLS or transitive runtime dependency closure. The exact interpreter pathname remains absent, and the staged rootfs remains untouched. The reported JSON is preserved in `USER-MAC-AUDIT-RESULT.json`. **NOT_BOOTABLE**.
