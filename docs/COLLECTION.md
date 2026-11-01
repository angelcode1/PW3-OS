# Read-only Kindle PW3 evidence collector — verified v6

**Use `tools/pw3_collect_v6_hostcap.py`, not the old `tools/collect_pw3_readonly.py`.**
The old version requires remote `dd` and fails on the observed Kindle BusyBox environment. V6 bounds output on the Mac and has a successful real SSH capture dated 2026-11-01.

## Verify before connecting

```sh
python3 tools/pw3_collect_v6_hostcap.py --version
python3 tools/pw3_collect_v6_hostcap.py
python3 -m unittest discover -s tests -p 'test_collector_v6.py' -v
```

The version must be `PW3-V6-HOSTCAP-20261101`. Dry run is the default and does not connect. The unit tests are local-only and do not contact the Kindle.

## Optional, explicit read-only capture

Only if SSH is already enabled on the Kindle:

```sh
python3 tools/pw3_collect_v6_hostcap.py \
  --host 192.168.8.102 --port 2222 --collect \
  --out ~/Downloads/pw3-readonly-evidence-new.zip
```

Use the Kindle's current host address. SSH may prompt for a password for each probe. The output path must not already exist: no capture is overwritten.

The fixed allowlist performs 17 commands using read-only `uname`, `cat` and `ls`; the Mac enforces a 32768-byte stdout limit and creates the ZIP and manifest locally. No remote `head`, `grep`, `dd`, `sed`, `awk`, temporary files, or privilege-changing install commands are needed. The optional `--include-init-scripts` flag is **off by default**; those files may contain secrets and must be reviewed before sharing.

## Verified 2026-11-01 result

The v6 evidence ZIP contained **17 successful diagnostic captures and zero reported errors**. All 17 per-entry SHA-256 hashes matched, and ZIP integrity passed. The observed hardware interfaces are summarized in [PW3 hardware evidence](PW3-HARDWARE-EVIDENCE-V6.md).

This validates read-only enumeration, **not** device operation, firmware changes, KOReader on-device startup, EPDC refresh or power controls.

**Never publish raw device evidence in this public GitHub repository.** Review captures for identifiers or secrets before sharing anywhere. No personal documents, proprietary firmware, credentials, or private keys are intentionally captured; actual output can still contain sensitive local information.

**Safety hold:** `NO_FIRMWARE_WRITES_HOLD; NO_BOOT_ACTIONS; NO_HARDWARE_ACTIONS; NOT_BOOTABLE`. Do not enable SSH or change stock firmware solely for research. The R22 application integration work remains inside offline Docker/QEMU.
