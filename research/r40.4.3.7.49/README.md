# R40.4.3.7.49 — .plt+0 prefix-cohort survey (read-only)

**Host-only research. NOT_BOOTABLE.** No stage mutations, guest aliases, ELF/QEMU execution, firmware writes, boot or pruning.

The user-reported R3748 result showed **18** weak PLT slot initial words all numerically equal to `.plt+0` in **nine** requesting ARM ELF files. Twelve sites reused a numeric target within a requester; six were unique within their requester. Those unrelocated words are **not proven executable pointers**, PLT resolver entries, or lazy-binding behavior.

R3749 SHA-pins the original R3748 source (SHA256 `d2628027b1984a78f5ff9c2a1fbc7b0355d380ee00f833c25512b4cba10ee992`) and replays its inherited stage holds, 12 requester/6 provider/18 PLT site and all `.plt+0` baselines. It reads 12–16 bounded, file-backed bytes at the unique executable `.plt` section start for each of nine affected ELF requesters. It categorizes section size, coarse A32 bitfields at each word position, counts distinct byte-identical 12/16-byte prefixes across requester files and returns **only aggregate numbers and category labels**. Raw words, names, paths, addresses, bytes, version strings, fingerprints and decoded instruction streams are not exported.

**Host verification:** 44 new + 400 inherited synthetic tests = **444/444 PASS**, clean-extraction rerun PASS, 42-entry SHA256 manifest PASS and 43-file ZIP integrity PASS. Full runnable source and pinned parent tests are packaged in conversation ZIP `pw3-r3749-plt-zero-prefix-cohort-readonly.zip`, SHA256 `04ec643755a3c52b02814c356fb43f026a93a8f32c51862c52f0777f12355907`. Executable source **not published as GitHub standalone code**, so no GitHub Actions pass is claimed. User Mac-stage R3749 audit has not run.

## macOS without git or gh

Download the ZIP into Downloads, then:

```sh
mkdir -p "$HOME/Downloads/pw3-r3749"
cd "$HOME/Downloads/pw3-r3749"
unzip -o "$HOME/Downloads/pw3-r3749-plt-zero-prefix-cohort-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043749-PLT-ZERO-PREFIX-COHORT-READONLY.py \
  --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
  --parent-dir "$PWD"
```

Send `requester_prefix_window_counts`, `plt_section_size_categories`, `distinct_12_byte_prefix_windows_in_memory`, `distinct_16_byte_prefix_windows_in_memory`, `objects_with_identical_12_byte_window_as_another`, and `a32_encoding_field_categories_by_position`. If the result is HOLD, preserve that hold and do not change source pins or original R13 files.

The original R3745 failure HOLD remains preserved. The absent guest PT_INTERP path, original R26 source provenance, historical inventory hashes, ARM TLS, runtime linker namespace/weak semantics, kernel ABI, recovery and boot are not verified. OpenSSH/SFTP/rsync remain deferred future-image requirements. **NOT_BOOTABLE**.
