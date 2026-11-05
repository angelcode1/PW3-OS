# R40.4.3.7.34 — future-image guest interpreter mapping *simulation* (read-only)

**Research/education only. Original stage unchanged. NOT_BOOTABLE.**

The user's R4043733 Mac audit reported 12 ELF `PT_INTERP` references to **one** absent guest interpreter path, whose parent is one component below guest `/`. A single same-basename static ELF-header-compatible alternative lives under a different guest branch four parent components deep. The original and alternate do not share a parent component. Original R13 stage count/ELF and ABI checks were independently classified earlier, but a candidate at the wrong path is **not the interpreter Linux chooses**.

R3734 is an in-memory **mapping design check**, not an installation or image-building tool. It imports the exact SHA-256 pinned R3733 source, which verifies the pinned R3726 and R3727 sources and replays the original 83 ELF / 19 PT_INTERP / 7 present / 12 absent and 1446 regular/335 symlink stage counts. It then separately re-identifies the same unique candidate from the read-only inventory, verifies that the missing guest leaf really is absent, and checks that the missing and alternate parent directories contain no symlink components. Finally it calculates **only in memory** a prospective *relative guest symlink target* and simulates whether it would reach that candidate without escaping the modeled guest root.

The output contains no private guest paths, file contents, or target strings. **`FUTURE_IMAGE_GUEST_ALIAS_SIMULATION_ONLY` does not mean the mapping is approved, created or runtime-tested.** Parent/source ABI and dependency holds persist. A future *separately assembled, licensed, SHA-pinned independent image* would require a separately authorized package-layout decision and complete offline integration, kernel, recovery and security review; **do not use the output to create a symlink, copy any loader, or edit the original R13 stage**.

## No-git Mac commands

Download `pw3-r3734-future-mapping-simulation-readonly.zip` into `~/Downloads`, then:

```sh
mkdir -p "$HOME/Downloads/pw3-r3734"
cd "$HOME/Downloads/pw3-r3734"
unzip -o "$HOME/Downloads/pw3-r3734-future-mapping-simulation-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r4043734.py' -v
python3 -B R4043734-FUTURE-MAPPING-SIMULATION-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

The included R3726, R3727 and R3733 scripts are exact pinned source copies; do not replace or weaken them to force a PASS. If the output says `HOLD`, keep the hold and send only the category. The expected synthetic tests are **16 OK**. The real user's stage output is unknown until run.

The final-image OpenSSH, SFTP and rsync acceptance requirements are maintained separately in `docs/PW3-REMOTE-TRANSFER-PLAN.md` and remain deferred. No firmware, rootfs writes, image installation, physical device, boot or pruning. **NOT_BOOTABLE.**
