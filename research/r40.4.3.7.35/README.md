# R40.4.3.7.35 — static ELF PT_LOAD preflight, read-only

**Status: 18 local synthetic host tests PASS. User Mac stage audit NOT RUN. NOT_BOOTABLE.**

The R3734 user-reported in-memory guest mapping simulation reached the one alternate interpreter candidate lexically, with one parent ascent and six components, **without applying any mapping or writing any stage file**. The twelve requesting PT_INTERP segments still share one absent guest interpreter pathname. Numeric ARM attributes and ELF headers were only static candidates, not proof of Linux 3.0.35 compatibility or a working runtime loader.

R3735 adds a read-only static ELF32 ARM program-header audit. It SHA-256 pins the unchanged R3734 source (`3187922ba12b662081c2e8a0324b5d1df90ff1c4d62969444f7d557c4402bf66`), inherits the R3733/R3727/R3726 pins, replays the R3734 baseline, and inspects the one candidate and twelve requesting ELF files for:

- `PT_LOAD` file bounds and 32-bit virtual-address overflow;
- `p_align` power-of-two and file-offset/virtual-address congruence;
- entry point within an executable `PT_LOAD`;
- writable+executable load-segment counts;
- `PT_DYNAMIC` inside a file-backed `PT_LOAD` range;
- aggregate source structural categories without guest path or ELF strings.

These are **new static classification categories**, not kernel-loader emulation, runtime execution, ABI proof, image approval or a proposed modification of the original stage. No firmware, hardware, networking, QEMU or original-rootfs writes occur.

The locally verified conversation ZIP is `pw3-r3735-pt-load-readonly.zip` with SHA-256 `bb57c817848f39e378343ce9b0ea076fd993089379adaaff41e00e4d028d395a`. Its Python source SHA is `59c5154cdc63d44e0cc0ef51bff820715be6b2d5a9fe8a40b2cd50216ae83d4d`; test source SHA is `9b6143ea6c99f89fdabc40583882f20f09dd54317752acadb2882ee29e795315`. **The source and test files are in the conversation ZIP, not published in this GitHub commit. No GitHub Actions result is claimed.**

## Mac execution without git or gh

Download the R3735 ZIP into `~/Downloads`, then:

```bash
mkdir -p "$HOME/Downloads/pw3-r3735"
cd "$HOME/Downloads/pw3-r3735"
unzip -o "$HOME/Downloads/pw3-r3735-pt-load-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r4043735.py' -v
python3 -B R4043735-PT-LOAD-PREFLIGHT-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$HOME/Downloads/pw3-r3734"
```

The parent R3734 directory must already contain its exact R3734 and R3733/R3727/R3726 sources; the R3735 ZIP does not repackage them. A `HOLD` means retain the refusal and report its category; never alter the original rootfs, SHA pins, or source files to force a PASS.

The future independent-image OpenSSH, SFTP and rsync package requirements remain deferred until full validation. `NOT_BOOTABLE`.
