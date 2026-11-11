PW3-OS Alpine 3.24.3 image — direct integration candidate
=========================================================
Built from the official Alpine 3.24.3 armv7 minirootfs, Inkwell v1.2.0
MIT-licensed e-ink UI/network design, the PW3-OS BibleReader source on
feature/pw3-bible-reader, KOReader kindlepw2 v2026.07.1, and original
PW3-OS Memory Match and Sudoku code. NO Inkwell games, Doom, Minecraft,
Chess, Quill, or models are included.

BUILD STATUS AND TESTING
------------------------
This is an integration candidate, NOT a flashed or hardware-proven image.
The existing Kindle Amazon bootloader/kernel/firmware are untouched.
Inkwell's own original system is hardware-proven upstream; this assembled
PW3-OS image, games, BibleReader, and KOReader launcher still require testing.
Official KOReader's GNU/softfloat ABI is not solved merely by including gcompat;
if building on Mac, PW3_STAGE can supply the project's separate GNU compatibility
runtime from the R13 stage. The CI build bundles the official KOReader release
but DOES NOT claim KOReader will launch until live verification.

FILES
-----
* alpine-os.img            New 768 MiB ext3 image; NOT your working alpine-debug.img
* alpine-os.img hash       In SHA256SUMS
* pw3os-boot-once.sh       Candidate one-shot runner adapted from validated Batch 4.4
* pw3-debugmount           Restricted ARM static mount helper source in bundle
* BUILD-MANIFEST.json      Source versions, app list, runtime caveats

DEVICE STAGING — ATTENDED AND REVERSIBLE
----------------------------------------
1. Before touching any running boot script, verify the existing Batch 4.4
   post-boot log reports a clean ext3/loop release and port 2223 firewall
   rule removal. Do not proceed after uncertain cleanup.
2. Verify local SHA256SUMS. Copy ONLY alpine-os.img to
   /mnt/base-us/pw3os/ via stock USB mass storage, eject safely.
   The image is separate from the known-good alpine.img and alpine-debug.img.
3. Over stock SSH, copy only pw3os-boot-once.sh as
   /mnt/base-us/pw3os/pw3os-boot-once.sh.candidate; compare local/remote
   SHA-256; do not overwrite ATTENDED-LIVE-ALPINE.sh automatically.
4. Copy your EXISTING public SSH key (not the private key) from your Mac
   to /mnt/base-us/pw3os/authorized_keys, preserving your working wifi.conf.
   Never put credentials into GitHub Actions or the public repository.
5. Only after independently verifying images, mount-helper, logs and stock
   fallback, back up ATTENDED-LIVE-ALPINE.sh and substitute the candidate.
   Rename/adjust the new SHA256 manifest to alpine-os.img and verify it.
   The installed Upstart hook remains ONE-SHOT and consumes BOOT_ALPINE_ONCE.
6. First boot is an ATTENDED full Alpine UI session. When the launcher exits,
   the wrapper must release every mount/loop and remove its temporary port
   2223 firewall rule; uncertain cleanup must not continue stock startup.
   After a successful one-shot run, the next reboot returns to stock unless
   explicitly rearmed. Do NOT remove Amazon partitions or boot files.

RUNTIME
-------
PW3-OS graphical menu, ordered in three columns:
Bible | KOReader | Notes
Games | Terminal | Wi-Fi
Settings
Games opens our Memory Match and Sudoku applications. The current userstore wifi.conf and authorized_keys
are loaded at boot. Dropbear listens on wlan0:2223 (public-key-only).
Persistent init logs: /mnt/base-us/pw3os/logs/alpine-own-init.log
Heartbeats: /mnt/base-us/pw3os/logs/heartbeat.log
Upstart runner logs: /mnt/base-us/pw3os/boot-once.log

WARNING: The supplied runner is adapted from the previously successful
short SSH sessions but is now unbounded and starts a graphical application.
The ability to resume stock after LONG-RUNNING Alpine and USB operations
has not been independently verified. This archive is not an automatic
firmware installer and does not replace an independent rescue mechanism.

LEGACY IMAGE CLEANUP
--------------------
Legacy `alpine.img` and `alpine-debug.img` are not used by this boot runner.
Remove them only after a successful stock reboot and verified release of the
new Alpine image, loop mount and temporary SSH firewall rule. Do not remove
any image that is still referenced by an installed fallback/Upstart script.
The original Amazon root/kernel and recovery must remain intact.
