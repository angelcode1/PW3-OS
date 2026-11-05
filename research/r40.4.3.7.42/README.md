# R40.4.3.7.42 — Weak local-version undefined relocation context (read-only)

**Host-only research and education. NOT_BOOTABLE. Original R13 stage unchanged.**

## Starting evidence

The user-reported R3741.1 Mac result reclassified 632 relocation-referenced
undefined dynamic-symbol entries from 12 ARM ELFs. There are **588 explicit GNU
version requirements**, **42 local version index-0 entries** (`STB_WEAK`,
`STT_NOTYPE`, hidden bit clear) and **2 global/unversioned references**. Of the
nonlocal references, 508 had one GNU version-name candidate, 80 multiple, and
2 had no provider name candidate among the six staged libraries. These are
static name/version candidate counts and do not establish symbol resolution.

## What this program does

- Verifies SHA-256 of unchanged R3741.1 source, inherits original R3741 HOLD,
  and replays the original R3740/R3739/older pinned Mac stage baselines.
- Reads bounded, file-backed ELF32 ARM DT_REL, DT_RELA and DT_JMPREL tables in
  12 requesting ELFs; cross-checks the prior 3,499 total relocation sites.
- Maps relocation records to the 42 `VERSYM=0` weak undefined symbol records;
  reports numeric relocation type counts, table categories, number of objects
  affected, and whether their *names* have zero/one/multiple staged provider
  export-name candidates (without performing symbol lookup).
- Separately counts binding, symbol type, version-index grouping, relocation
  types and affected files for the two entries whose names have no candidate
  among the six staged provider objects.
- Prints **only numerical and categorical aggregates**. No guest paths,
  library names, version strings, symbol names, symlink targets, source ELF
  bytes or user-identifying paths are emitted.

**Interpretation:** Even a reference marked `STB_WEAK` does not prove that a
runtime loader will choose a zero value, that the referencing relocation type
can legally accept an unresolved value, or that a candidate export will be
selected. This diagnostic neither applies relocations nor executes any ELF.
Index-zero weak references continue to be **review only**. The two absent-name
candidates are absent only from the six staged direct providers, not proven
absent from all possible runtime namespaces. This does not validate TLS,
interposition, real DT_RPATH search, full dependency closure, original R26
provenance, Linux 3.0.35 ABI, recovery or boot.

## Run on a Mac without git or gh

Download `pw3-r3742-weak-relocation-context-readonly.zip` into `~/Downloads`, then:

```sh
mkdir -p "$HOME/Downloads/pw3-r3742"
cd "$HOME/Downloads/pw3-r3742"
unzip -o "$HOME/Downloads/pw3-r3742-weak-relocation-context-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r4043742.py' -v
python3 -B -m unittest discover -s . -p 'test_r4043741_1.py' -v
python3 -B -m unittest discover -s . -p 'test_r4043741.py' -v
python3 -B -m unittest discover -s . -p 'test_r4043740.py' -v
python3 -B -m unittest discover -s . -p 'test_r4043739.py' -v
python3 -B -m unittest discover -s . -p 'test_r4043738.py' -v
python3 -B R4043742-UNRESOLVED-WEAK-RELOCATION-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Expected synthetic tests: 23 + 24 + 27 + 23 + 18 + 16 = **131 PASS**.
The real Mac stage R3742 result has NOT been run or inspected by this agent.
If a `HOLD` occurs, do not modify parent hashes or stage files to force it
through; send the hold category only.

OpenSSH server, SFTP server and rsync remain deferred to a future validated,
independent image. No guest alias applied, no file writes, QEMU, ARM ELF
execution, Kindle access, firmware, boot or pruning. **NOT_BOOTABLE.**
