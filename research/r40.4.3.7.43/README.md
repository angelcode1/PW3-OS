# R40.4.3.7.43 — Additional staged ELF name-candidate survey (read-only)

**Standalone source-only research. NOT_BOOTABLE.**

R3742's Mac audit identified **33** GNU-index-0 weak undefined symbols and **two** GNU-index-1 weak undefined symbols without a name candidate among the six staged direct provider ELFs. This does not establish missing runtime symbols. R3743 is a bounded read-only survey of **additional** staged ELF32 ARM objects and already identified 12 requesting ELF objects for export-name matches to those 35 references.

The independent Python script SHA-256-pins the unchanged R3742 source `4d118c49...b86715ed`, inherits R3741.1 and its original R3741 HOLD and earlier source pins, and requires replay of R3742's 42 weak local-index references, 58 relocation sites and 33+2 unmatched-name categories. The scanner skips symlink files/directories, reads ELF headers and defined externally visible dynamic symbols, and reports **only aggregate category counts**; library paths, symbol names and version strings remain private in memory. Unparseable ELF32 dynamic files are counted explicitly. It does **not** prove loader namespaces, symbol version compatibility, actual weak binding behavior, kernel ABI, TLS support, or symbol resolution. It never runs staged binaries, writes to the R13 stage, creates aliases, accesses PW3 hardware, writes firmware, installs packages, boots or prunes.

**Local host tests:** 32 R3743 tests and 131 inherited tests passed (163 total). ZIP integrity and checksum verification passed. The user's actual R13 Mac stage has **not** been run for this milestone.

**Standalone offline ZIP:** `pw3-r3743-additional-weak-export-scan-readonly.zip` (SHA-256 `6a6787ecd55d21b7c6789d8929cb8984f0c62d3867c14dc2260226d007014fa5`), available in the original ChatGPT conversation. The tested new source and tests are in the ZIP, **not committed to GitHub in this metadata-only release record**. No GitHub Actions pass is claimed.

## Mac use without git or gh

Download the ZIP to `~/Downloads`, then:

```sh
mkdir -p "$HOME/Downloads/pw3-r3743"
cd "$HOME/Downloads/pw3-r3743"
unzip -o "$HOME/Downloads/pw3-r3743-additional-weak-export-scan-readonly.zip"
shasum -a 256 -c SHA256SUMS
python3 -B -m unittest discover -s . -p 'test_r40437*.py' -v
python3 -B R4043743-STAGED-ELF-WEAK-EXPORT-SURVEY-READONLY.py \
 --rootfs "$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs" \
 --parent-dir "$PWD"
```

Send the JSON `additional_name_candidate_categories`, `additional_name_candidate_categories_by_target_group`, `additional_scan_counters`, or `hold_category`. Original interpreter mapping, runtime proof, R26 provenance, historical hashes and all hardware/boot/prune gates remain held. OpenSSH/SFTP/rsync remain deferred final-image requirements. **NOT_BOOTABLE.**
