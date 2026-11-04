# R40.4.3.7.12.1 — source-only inherited preflight classifier

Research and educational only. NO_QEMU, NOT_BOOTABLE.

The user reported a generic source-preflight HOLD in R40.4.3.7.12 without a diagnostic category. This package runs the **unchanged** R3712 original verification code read-only, printing only a fixed allowlisted gate, method and refusal reason. It does not change original guest, reviewer, prior releases, source stage or Docker image. It does not launch QEMU, Docker, boot or access hardware.

Artifact: pw3-os-r40.4.3.7.12.1-preflight-doctor.zip, SHA-256 bff12d068e2233f8f5dce966f6d4c8448b0e95a00bf511399a08a1fa089086b3, 5,481 bytes, 5 members, 4 SHA-256 manifest payloads. ZIP CRC PASS and clean extraction 9/9 host tests PASS, shell wrapper syntax PASS.

Mac:
```sh
cd "$HOME/Downloads"
unzip -n pw3-os-r40.4.3.7.12.1-preflight-doctor.zip -d pw3-os-r40.4.3.7.12.1-preflight-doctor
DIAG="$HOME/Downloads/pw3-os-r40.4.3.7.12.1-preflight-doctor"
sh "$DIAG/RUN-R4043712-PREFLIGHT-DOCTOR-MAC.sh" test
sh "$DIAG/RUN-R4043712-PREFLIGHT-DOCTOR-MAC.sh" diagnose
```

Send only the fixed classification line. Do not delete old results, replace original staged source, relax any verifier, or start QEMU until the hold is identified. Prior 347 observed stage regular opens not recomputed; 1,101 unobserved regular stage files and 976 historical UNKNOWN_HOLD records retained. No authenticated R26 provenance, complete dependency closure, physical touch, boot or firmware write. NOT_BOOTABLE.
