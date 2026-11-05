# PW3-OS — OpenSSH/SFTP/rsync final-image integration gate

**User-requested final-image requirement; NOT installed or tested on PW3. Status: DEFERRED_UNTIL_VALIDATED. NOT_BOOTABLE.**

## Requested packages

For the eventual independent **Alpine ARMv7** userspace, include from one selected, pinned Alpine repository/architecture/release (no mixing releases):

- `openssh` — modern OpenSSH suite, client and server meta package.
- `openssh-server` — explicit `sshd` server dependency for remote access.
- `openssh-sftp-server` — working SFTP subsystem for macOS modern `scp` without `-O`, plus interactive `sftp`.
- `rsync` — incremental transfers of ebooks and documents over SSH. It must exist on **both** the macOS sending host and PW3 target.
- If OpenRC is the selected init system, review `openssh-server-common-openrc` and its service setup/host-key generation as an appropriate dependency. Do not blindly install an init system or start network services in current stage.

Alpine's `openssh` meta package already depends on OpenSSH client/server and SFTP server in documented ARMv7 releases; the explicit subpackage names here serve as **acceptance checks** in case package layouts change. OpenSSH `scp` has used SFTP by default since 9.0; the requested workflow is `scp -r ~/Books/ user@pw3:/home/user/Books/` (without `-O`) once the system is safely running. For syncing, use `rsync -av --progress ~/Books/ user@pw3:/home/user/Books/`, without `--delete` by default.

## Do not install until all applicable gates pass

1. Preserve the current original R13 staged rootfs and existing SHA-pinned evidence; prepare a **separate** versioned, reproducible image assembled from licensed packages. No stock Kindle partition modifications or original stage writes.
2. Select an exact Alpine release and ARMv7 ABI, fetch **pinned** `.apk` packages/dependencies from trusted sources and record repository signatures, SHA256, licenses and transitive runtime closure. Check musl/glibc isolation; do not assume a modern Alpine build runs on the retained Linux **3.0.35-lab126** kernel.
3. In an isolated offline ARM/QEMU clone, validate `sshd` ELF PT_INTERP, ABI and dependency closure; `sshd -t` configuration syntax; SFTP server availability; `rsync --version`; DNS/network assumptions and supported kernel syscalls. No live PW3 network or physical device operations are authorized by current milestones.
4. Test an **authorized isolated guest** with generated ephemeral keys and a non-root account: key-based SSH login, SFTP upload/download, `scp` **without** `-O`, and repeated `rsync` upload with evidence that unchanged EPUB/PDF files are not retransferred. Check file permissions, special filenames, storage bounds, and clean service shutdown. Never embed private host keys or user credentials in image artifacts.
5. Independently validate PW3 boot/recovery, physical Wi-Fi/power/display compatibility, authenticated provenance, image reproducibility and device security; only after explicit authorization and safe recovery proof may the *final* isolated image enable `sshd` at boot. Do not preconfigure password/root access, expose a network service, or silently enable it on stock firmware.

## Config and security acceptance

- Use dedicated unprivileged account with protected ebook destination and `authorized_keys`; disable root SSH login and password authentication by default, subject to recovery design.
- Provision SSH host keys uniquely per device at first authorized startup, never embed shared keys in images.
- Verify `Subsystem sftp` points to the installed server or supported `internal-sftp` and permits SFTP-based `scp`; enabling an SSH shell alone is **not** evidence.
- Prefer `rsync -av --progress` over `rsync --delete`; incremental transfers require `rsync` on both endpoints. Consider power/battery and low-storage/flash-wear bounds.
- Service manager startup and user provisioning must be deterministic and separately tested.

The package request is an **acceptance requirement**, not a package install command for the user's current stage. `image_integrated=false`, `boot_authorized=false`, `device_access_authorized=false`, `firmware_write_authorized=false`, `prune_authorized=false`. **NOT_BOOTABLE**.

References:
- https://wiki.alpinelinux.org/wiki/Setting_up_a_SSH_server
- https://pkgs.alpinelinux.org/package/v3.22/main/armv7/openssh
- https://pkgs.alpinelinux.org/package/v3.24/main/armv7/rsync
- https://www.openssh.org/releasenotes.html
