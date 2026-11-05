# R40.4.3.7.45 — weak ARM PLT/GOT initial-word preflight

**Research only; read-only; NOT_BOOTABLE.** The R3744 user Mac audit found **62** targeted weak-symbol relocation sites: **44 R_ARM_GLOB_DAT** original zero-word sites, and **18 R_ARM_JUMP_SLOT** original nonzero-word PLT sites. All are writable and outside GNU RELRO. All 12 requesters contain PT_GNU_RELRO and zero advertise NOW.

R3745 is a new separately packaged Python diagnostic. It pins the unmodified R3744 source SHA256 `2fed6996817186156200f126cd69ffb9a326062721d2730b03636097daceae9d`, inherits all earlier source pins, and replays the R3744 static Mac-stage baseline. It then reads only bounded ELF32 ARM program headers, DT_JMPREL and DT_PLTGOT metadata. For the 18 targeted weak-symbol PLT slots it classifies the *original, unrelocated* word by whether its numeric value, optionally masked for a low ARM/Thumb marker bit, lies in the requesting ELF's own executable PT_LOAD, non-executable PT_LOAD, outside or in overlapping memory regions. It also categorizes the DT_PLTGOT value as absent, in writable/nonwritable PT_LOAD, or outside/ambiguous.

**These categories never prove a word is a pointer, nor PLT disassembly, lazy binding, unresolved-weak semantics, Linux 3.0.35 ABI, loader search, symbol resolution or boot readiness.** No addresses, words, ELF bytes, symbol names, file paths or guest strings are printed. The original guest interpreter pathname is still absent; no mapping, stage edits, ELF execution, QEMU, firmware write, boot or pruning is authorized.

The tested offline ZIP is `pw3-r3745-weak-plt-initial-word-readonly.zip` SHA256 `84fe5a61bcd18e5ded5543540e3a485cd95c270a947723e28d66abe9feba2710`. Source SHA256 `c3b95955df80e896196887fe922acd253d26948728939f1ea8349782feb73794`, test SHA256 `b517d2ae494bea90c73aa3df52b52225e535786597cdff1df477d0f223069848`. The ZIP contains **31 members**: pinned parent scripts, current source, tests, README, release status, workflow *source* and checksum manifest. **35 new tests plus 218 inherited tests: 253/253 PASS**, including clean extraction and checksum verification. The complete runnable Python source is included in the conversation ZIP but **not yet separately published to GitHub**, and **no CI run is claimed**.

## Mac commands — no git or gh

Download the ZIP into `~/Downloads` then:

```sh
mkdir -p "$HOME/Downloads/pw3-r3745"
cd "$HOME/Downloads/pw3-r3745"
unzip -o "$HOME/Downloads/pw3-r3745-weak-plt-initial-word-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043745-WEAK-PLT-INITIAL-TARGET-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send `targeted_weak_plt_sites`, `weak_plt_initial_target_categories_by_group`, `requester_dt_pltgot_categories`, or the `hold_category` if refused. Do not modify any source pin or stage file to force a pass. Original R26 provenance, historical inventory hashes, ARM TLS, Linux kernel ABI and recovery remain held. OpenSSH, SFTP and rsync remain requirements for a separately validated future image. **NOT_BOOTABLE.**
