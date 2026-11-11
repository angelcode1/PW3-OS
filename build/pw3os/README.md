# PW3-OS — integrated Alpine 3.24.3 image builder

Build **our** Kindle OS from the existing PW3-OS `feature/pw3-bible-reader` source, using upstream Inkwell's *hardware/UI/startup reference*, not its games or application suite. This is a source build, not a stock firmware flash.

## Build on Mac

Docker Desktop, Colima, or OrbStack must be running. From the cloned `PW3-OS` repository (check out `feature/pw3-bible-reader` or the integration branch containing this builder):

```sh
sh build/pw3os/build-mac.sh
```

Artifacts appear under `out/pw3os/`. The build downloads official Alpine 3.24.3 ARMv7, resolves Alpine APK dependencies, builds Inkwell home/Wi-Fi/settings/terminal/splash without games or notes, compiles our e-ink BibleReader and two puzzle modes with pinned Zig 0.14.1, downloads public WEB/KJV/ASV verse archives, and bundles official KOReader `kindlepw2` v2026.07.1.

For the compatibility runtime already on your Mac, use:

```sh
export PW3_STAGE="$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs"
sh build/pw3os/build-mac.sh
```

This copies `opt/koreader-compat` if present. Its presence **does not guarantee live KOReader success**. To build with locally obtained Life Bible study content, set `PW3_LIFE_APK` to a local APK path. It is only mounted into the Mac Docker build, never committed or sent to GitHub. Avoid uploading proprietary APK/content or personal material to public Actions.

Use `PW3_OUTPUT=/path/to/empty/directory` to select another destination. The builder refuses to overwrite nonempty output directories.

## GitHub Actions

The `PW3-OS Alpine 3.24.3 image with Bible, KOReader and puzzles` workflow runs the **same Dockerfile and Python build script**. It builds a public-domain Bible-only image because the private Life Bible APK and your R13 stage are not in GitHub. The build uploads a SHA-verified 768-MiB ext3 image, an adapted one-shot runner and restricted mount helper as a downloadable Actions artifact.

On `feature/pw3-bible-reader`, push changes to this directory to trigger CI. After the workflow exists on `main`, it can also be run with **Actions → Run workflow**. Check the run status and uploaded artifact; publishing a workflow does not constitute a passing build.

## Included apps

- PW3-OS BibleReader: repository C app, public offline WEB/KJV/ASV, optional richer local Life Bible content
- KOReader: official KindlePW2 bundle, plus optional local dual-libc runtime
- **Games folder** with our Memory Match and Sudoku; future games can be added to this chooser
- Home order: Bible, KOReader, Games / Wi-Fi, Settings. Terminal is inside Settings.
- Inkwell-derived essential utilities: home launcher, Wi-Fi, settings (including Terminal), terminal binary, splash (MIT attribution)
- Alpine Wi-Fi (`wpa_supplicant`), Dropbear SSH on 2223, persistent logs in userstore

**No Inkwell Doom, Minecraft, Chess, TriKing, Quill or upstream game files.**

## Boot/recovery

Reuse the **existing verified one-shot Upstart hook** on the Kindle. Do not overwrite Amazon bootloader/kernel/partitions. The image is a new separate file (`alpine-os.img`). Do not switch it in until the earlier Batch 4.4 cleanup and stock fallback are confirmed. See `README-DEPLOY.txt` in the generated artifact. The graphical and KOReader integration remain unverified on physical hardware.

Upstream references: [Inkwell v1.2.0](https://github.com/pragyaangaur/Inkwell/tree/v1.2.0) (MIT); [KOReader v2026.07.1](https://github.com/koreader/koreader/releases/tag/v2026.07.1); [Alpine Linux 3.24.3](https://dl-cdn.alpinelinux.org/alpine/v3.24/releases/armv7/).

## Live application overlay

GitHub Actions publishes `pw3os-apps-overlay` with `apps`, `pw3-games`, `pw3-koreader`, and `settings`. Deploy to the **running** Alpine system over SSH (port 2223) after backing up `/etc/own/apps` and `/usr/local/bin/pw3-koreader`. Change the menu by restarting home, or at next boot. The Games chooser returns to itself when either puzzle exits. The KOReader launcher now executes its Lua runtime directly rather than Amazon's cvm/msg startup wrapper; runtime ABI support still needs device evidence. Never deploy this overlay over stock SSH into an unmounted Alpine image.

## Menu simplification

The home screen shows Bible, KOReader, Games, Wi-Fi, Settings (five items). The Settings screen has a Terminal button next to Restart and Power off; it preserves stock Kindle recovery and Battery/About. Notes is not built. Deploy the overlay files to running Alpine over SSH without replacing the 768-MiB image.

## GNU soft-float KOReader ABI

The official kindlepw2 LuaJIT binary is an ARM soft-float EABI executable that needs `/lib/ld-linux.so.3`, not Alpine's musl loader. A default public GitHub Actions build **does not include this GNU runtime** and KOReader cannot run until it is provided. The existing local R13 stage at `$HOME/Downloads/pw3-os-r13-alpine-dual-libc-fix/stage-r13-fixed/rootfs/opt/koreader-compat` includes a tested relocated GNU loader. The KOReader launcher runs that loader explicitly from `/opt/koreader-compat/gnu/lib/ld-linux.so.3` with `--library-path`, rather than altering `/lib` or starting Amazon's framework. Deploy R13 privately to Alpine over SSH and verify `luajit -v` first. Do not commit proprietary Kindle files into this repo.
