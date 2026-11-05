# R40.4.3.7.52 — PLT low12 arithmetic and entire-section dynamic relocation survey

**Research and educational purposes only. NOT_BOOTABLE.** No stage modifications, guest mapping, symlinks, ELF/QEMU execution, firmware, boot or pruning.

## Verified R3751 Mac result

The user-reported R3751 audit found 18 weak-PLT slot original words at `.plt+0` across nine requester ELFs. All nine first64-byte `.plt` windows had the same first four 32-bit words. The other 12 positions differed: nine only in the lower 12-bit partition and three in the upper 20-bit partition too. No `DT_REL`, `DT_RELA`, or `DT_JMPREL` dynamic relocation record targeted the first64 bytes. These facts are **static file observations**, not proof of actual ARM decoding, code pointers, dynamic symbol resolution, or working loader binding. Original stage and historical R3745 HOLD preserved. See `research/r40.4.3.7.51/USER-MAC-AUDIT-RESULT.json`.

## Next diagnostic

The SHA-pinned R3752 source (SHA256 `442559ec2637ba53be7c750582a74babf2845de6ccf3bf8f58d3ef6180fd1a4d`) requires the unchanged R3751 source SHA256 `715384dd671927da24f51808f63a15c5e8aadb0c984050331beea508ccc0af79`, replays earlier baselines and preserves the original R3745 HOLD. It analyzes only the same nine staged ELF32 ARM requesters using the pinned no-follow reader:

- Counts per WORD4–WORD15 diversity of numeric lower12 bits, and of the lower12 bits after subtracting `.plt` and `DT_PLTGOT` VAs. These are **arbitrary arithmetic correlations only**; they are not decoded ARM immediates or verified GOT offsets or runtime pointers.
- Checks the **entire bounded file-backed executable `.plt` section** (up to 1 MiB) for dynamic relocation targets from `DT_REL`, `DT_RELA` and `DT_JMPREL`. Reports table occurrences separately if two descriptors overlap; checks `DT_TEXTREL` and `DF_TEXTREL` flags. Zero relocation targets does not exclude link-time edits or runtime behavior.
- Exports aggregate counts/categories only. No raw words, bytes, addresses, names, paths, private hashes, symbol versions, or source contents.

**Host verification:** 62 new plus 556 inherited synthetic tests = **618/618 PASS** from a clean extracted ZIP. The 49-file ZIP integrity and all 48 file checksums passed. This is not a real Mac-stage pass. Full runnable code is in the downloadable conversation ZIP, **not separately published to GitHub**. No R3752 Actions pass is claimed.

## macOS runbook — no git or gh

Download `pw3-r3752-plt-low12-and-entire-reloc-readonly.zip` into `~/Downloads`, then:

```sh
mkdir -p ~/Downloads/pw3-r3752
cd ~/Downloads/pw3-r3752
unzip -o ~/Downloads/pw3-r3752-plt-low12-and-entire-reloc-readonly.zip
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043752-PLT-LOW12-CORRELATION-AND-FULL-RELOC-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send `arithmetic_low12_diversity_by_word_position`, `constant_low12_relationship_position_counts`, `entire_dot_plt_dynamic_relocation_target_sites`, `entire_dot_plt_dynamic_relocation_tables`, `requester_dt_textrel_objects`, `requester_df_textrel_flag_objects`. On HOLD, send its category and preserve the original stage and source pins.

Original R26 provenance, historical hashes, runtime loader namespace, interpreter path, ABI, TLS, recovery, firmware and boot authorization remain unverified or forbidden. OpenSSH/SFTP/rsync remain deferred to a separately validated image. **NOT_BOOTABLE**.
