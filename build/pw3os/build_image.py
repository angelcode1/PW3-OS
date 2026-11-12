#!/usr/bin/env python3
"""Codex full Alpine 3.24.3 image builder. Runs in one pinned Docker environment on CI/Mac."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
import urllib.request
import zipfile
from settings_integration import patch_settings
from codex_home import patch_codex_home
from codex_frontpage import patch_codex_frontpage
from codex_sleep import patch_codex_sleep
from browser_package import require_netsurf, verify_netsurf_closure, verify_browser_staged, NETSURF_PACKAGE

ALPINE = 'https://dl-cdn.alpinelinux.org/alpine/v3.24'
MINI = 'alpine-minirootfs-3.24.3-armv7.tar.gz'
CODEX_UI_UPSTREAM_REF = 'd1fc9d9ef911777fb5db14541fd5b841fd7c1f03'  # v1.2.0
KOREADER_VER = 'v2026.07.1'
KOREADER_ZIP = f'koreader-kindlepw2-{KOREADER_VER}.zip'
KOREADER_SHA = 'ea1f575c54492a2c679d128b7f3210fd7d6a87e5f5a1ff1f7a7fe2080ff68f86'
VPLS = {'web':'engwebp_vpl.zip', 'kjv':'eng-kjv_vpl.zip', 'asv':'eng-asv_vpl.zip'}
PKGS = ['dropbear','dropbear-scp','dropbear-dbclient','busybox-extras',
        'wpa_supplicant','tzdata','curl','ca-certificates','python3',
        'python3-pyc','libstdc++','libgcc','gcompat','font-dejavu',NETSURF_PACKAGE]


def run(*cmd, cwd=None, acceptable=(0,)):
    print('+', ' '.join(map(str,cmd)), flush=True)
    p = subprocess.run([str(x) for x in cmd],cwd=cwd)
    if p.returncode not in acceptable:
        raise RuntimeError(f'Command failed ({p.returncode}): {cmd}')
    return p


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def download(url, path, expected=None):
    path=Path(path)
    if not path.is_file():
        print('DOWNLOAD',url,flush=True)
        path.parent.mkdir(parents=True,exist_ok=True)
        request=urllib.request.Request(url,headers={'User-Agent':'Codex-builder/1'})
        with urllib.request.urlopen(request,timeout=120) as src, path.with_suffix(path.suffix+'.tmp').open('wb') as dest:
            shutil.copyfileobj(src,dest)
        path.with_suffix(path.suffix+'.tmp').replace(path)
    if expected and sha256(path).lower()!=expected.lower():
        raise RuntimeError(f'Checksum mismatch for {path.name}')
    return path


def official_hash(url):
    with urllib.request.urlopen(url+'.sha256',timeout=30) as src:
        text=src.read(2048).decode('ascii')
    match=re.search(r'\b([a-fA-F0-9]{64})\b',text)
    if not match: raise RuntimeError('Missing official Alpine checksum')
    return match.group(1)


def safe_zip_extract(archive, target):
    target=Path(target)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            p=Path(item.filename)
            if p.is_absolute() or '..' in p.parts or not p.parts:
                raise RuntimeError('Unsafe ZIP member: '+item.filename)
            if (item.external_attr>>16)&0o170000==0o120000:
                raise RuntimeError('ZIP symlink not accepted: '+item.filename)
        z.extractall(target)
        # Python ZIP extraction drops the source executable bits: LuaJIT needs
        # its x bit restored or KOReader rejects its own runtime.
        for item in z.infolist():
            if item.is_dir():
                continue
            path = target / item.filename
            perms = (item.external_attr >> 16) & 0o777
            if perms & 0o111:
                current = stat.S_IMODE(path.stat().st_mode)
                path.chmod(current | (perms & 0o111))


def install_pkgs(work,root,upstream):
    idx=[]
    for repo in ('main','community'):
        archive=download(f'{ALPINE}/{repo}/armv7/APKINDEX.tar.gz',work/f'APKINDEX-{repo}.tar.gz')
        with tarfile.open(archive,'r:gz') as tar:
            raw=tar.extractfile('APKINDEX').read()
        fn=work/f'APKINDEX.{repo}'
        fn.write_bytes(raw)
        idx.append(fn)
    require_netsurf(idx)
    res=subprocess.check_output(['python3',str(upstream/'tools/apkdeps.py'),','.join(map(str,idx)),*PKGS],text=True)
    packages=[x for x in res.splitlines() if x.strip()]
    if len(packages)<len(PKGS)//2: raise RuntimeError('Suspiciously small APK dependency closure')
    verify_netsurf_closure(idx,packages)
    for rp in packages:
        repo,name=rp.split('/',1)
        pkg=download(f'{ALPINE}/{repo}/armv7/{name}.apk',work/'apks'/f'{name}.apk')
        run('tar','-xpzf',pkg,'-C',root,'--exclude=.SIGN*','--exclude=.PKGINFO',
            '--exclude=.pre-*','--exclude=.post-*','--exclude=.trigger')
    return packages


def crosscompile(source,output,extra=(),target='arm-linux-musleabihf',freestanding=False):
    output.parent.mkdir(parents=True,exist_ok=True)
    flags=['-nostdlib','-Wl,-e,_start'] if freestanding else ['-static']
    run('zig','cc','-target',target,'-mcpu=cortex_a9',*flags,'-O2',
        '-Wno-unused-function','-Wno-unused-variable',*extra,source,
        *([] if freestanding else ['-lm']),'-o',output)
    output.chmod(0o755)
    desc=subprocess.check_output(['file',str(output)],text=True)
    if 'ARM' not in desc or 'statically linked' not in desc:
        raise RuntimeError('Not a static ARM binary: '+desc)
    print('CROSS_COMPILED',output.name,desc.strip())


def crosscompile_browser_shared(source,output,extra=()):
    """Build a *dynamic* ARMv7 SDL interception library. Never preload at boot."""
    output.parent.mkdir(parents=True,exist_ok=True)
    run('zig','cc','-target','arm-linux.3.0.35-musleabi',
        '-mcpu=cortex_a9','-shared','-fPIC','-O2',
        '-Wno-unused-function',source,*extra,'-ldl','-o',output)
    desc=subprocess.check_output(['file',str(output)],text=True)
    if 'ELF 32-bit' not in desc or 'ARM' not in desc or 'shared object' not in desc:
        raise RuntimeError('Invalid ARM browser capture shared library: '+desc)
    output.chmod(0o755)
    print('CROSS_COMPILED_BROWSER_SHARED',desc.strip())


def install_koreader(work,root,stage):
    dest=root/'opt/koreader'
    release=download('https://github.com/koreader/koreader/releases/download/'
                     +KOREADER_VER+'/'+KOREADER_ZIP,work/KOREADER_ZIP,KOREADER_SHA)
    unpack=work/'koreader-unpack'
    safe_zip_extract(release,unpack)
    matches=list(unpack.rglob('koreader.sh'))
    if not matches: raise RuntimeError('KOReader release does not contain koreader.sh')
    app=sorted(matches,key=lambda p:len(p.parts))[0].parent
    shutil.copytree(app,dest,dirs_exist_ok=True,symlinks=True)
    # Early build failure if the package is unusable; avoid deployment of a
    # KOReader launcher that fails before even executing LuaJIT.
    for name in ('luajit', 'fbink'):
        p = dest/name
        if not p.is_file():
            raise RuntimeError(f'KOReader release missing {name}: {dest}')
        p.chmod(p.stat().st_mode | 0o111)
        if not os.access(p, os.X_OK):
            raise RuntimeError(f'KOReader {name} is not executable after extraction')
    if not (dest/'reader.lua').is_file():
        raise RuntimeError('KOReader release lacks reader.lua in selected app root')
    # Do not patch KOReader release sources: all Codex adaptations are
    # persistent userpatch modules in KO_HOME and an external launcher.
    compat=False
    if stage:
        compat_src=stage/'opt/koreader-compat'
        if compat_src.is_dir():
            shutil.copytree(compat_src,root/'opt/koreader-compat',dirs_exist_ok=True,symlinks=True)
            compat=True
    launcher=root/'usr/local/bin/pw3-koreader'
    project=Path(__file__).resolve().parent
    shutil.copy2(project/'pw3-koreader-managed.sh',launcher)
    launcher.chmod(0o755)
    tools=root/'usr/local/lib/pw3os'
    tools.mkdir(parents=True,exist_ok=True)
    for name,output in (('koreader_update.py','koreader_update.py'),
                        ('2-pw3os-autoupdate.lua','2-pw3os-autoupdate.lua')):
        shutil.copy2(project/name,tools/output)
    (tools/'koreader_update.py').chmod(0o755)
    return compat


def verify_bible_archive(app,work,archive):
    # Catch structural mismatches (including invalid day_start) before publishing any image.
    validator=work/'pw3-bible-host-validator'
    run('cc','-O2','-DPW3_HOST',app/'reader.c','-lm','-o',validator)
    run(validator,archive,'--verify')


def install_bible(repo,work,root,life_apk):
    app=repo/'apps/pw3-bible'
    dest=root/'opt/pw3-bible'
    dest.mkdir(parents=True,exist_ok=True)
    for path in ('run-kindle.sh','online_verse.py','audio_stream.py','audio_control.py',
                 'audio_catalog.py','online-translations.tsv'):
        src=app/path
        if src.is_file(): shutil.copy2(src,dest/path)
    # Preserve font and third-party attribution.
    shutil.copytree(app/'fonts',dest/'fonts',dirs_exist_ok=True)
    shutil.copytree(app/'vendor',dest/'vendor',dirs_exist_ok=True)
    crosscompile(app/'reader.c',dest/'pw3-bible-arm',extra=('-Wno-unused-variable',
                 '-Wno-unused-function'),target='arm-linux.3.0.35-musleabi')
    vpls={}
    for key,filename in VPLS.items():
        vpls[key]=download(f'https://ebible.org/Scriptures/{filename}',work/filename)
    if life_apk:
        cmd=['python3',app/'build.py','--apk',life_apk,'--web',vpls['web'],
             '--kjv',vpls['kjv'],'--asv',vpls['asv'],'--output',dest/'bible.pw3']
        run(*cmd)
        verify_bible_archive(app,work,dest/'bible.pw3')
        return 'full-local-life-bible'
    run('python3',repo/'build/pw3os/public_bible.py','--repo',repo,
        '--web',vpls['web'],'--kjv',vpls['kjv'],'--asv',vpls['asv'],
        '--output',dest/'bible.pw3')
    verify_bible_archive(app,work,dest/'bible.pw3')
    return 'public-domain-WEB-KJV-ASV'


def install_codex_core(repo,work,root):
    upstream=work/'codex-ui-upstream'
    run('git','clone','-q','--no-checkout','https://github.com/pragyaangaur/Inkwell.git',upstream)
    run('git','checkout','-q',CODEX_UI_UPSTREAM_REF,cwd=upstream)
    # ui.h includes "sleep.h" from its own directory. Patch the pinned
    # checkout header directly so Home and every other screen share the same
    # Codex sleep wording; never alter the actual suspend/wake implementation.
    sleep_header=upstream/'src/ui/sleep.h'
    sleep_header.write_text(patch_codex_sleep(sleep_header.read_text()))
    apps=('home','wifi','settings','term','splash')  # No Notes or upstream games
    bindir=root/'usr/local/bin';bindir.mkdir(parents=True,exist_ok=True)
    for name in apps:
        source=upstream/'src/ui'/f'{name}.c'
        patched=work/f'{name}-pw3os.c'
        content = re.sub(r'(?i)inkwell', 'Codex', source.read_text().replace('/mnt/us/linux','/mnt/us/pw3os'))
        if name == 'home':
            content = patch_codex_home(content)
            content = patch_codex_frontpage(content)
        if name == 'settings':
            content = patch_settings(content)
        patched.write_text(content)
        source=patched
        crosscompile(source,bindir/name,extra=('-I'+str(upstream/'src/ui'),
                     '-I'+str(upstream/'third_party/stb')))
    crosscompile(repo/'build/pw3os/puzzles.c',bindir/'pw3-puzzles',
                 extra=('-I'+str(upstream/'src/ui'),'-I'+str(upstream/'third_party/stb')))
    crosscompile(repo/'build/pw3os/games-menu.c',bindir/'pw3-games',
                 extra=('-I'+str(upstream/'src/ui'),'-I'+str(upstream/'third_party/stb')))
    fonts=root/'usr/share/fonts/inkwell';fonts.mkdir(parents=True,exist_ok=True)
    for f in (upstream/'fonts').glob('*.ttf'):shutil.copy2(f,fonts/f.name)
    for f in (upstream/'fonts').glob('*.txt'):shutil.copy2(f,fonts/f.name)
    license_dir=root/'usr/share/licenses/pw3os';license_dir.mkdir(parents=True,exist_ok=True)
    shutil.copy2(upstream/'LICENSE',license_dir/'Codex-UI-Upstream-MIT.txt')
    config=root/'etc/own';config.mkdir(parents=True,exist_ok=True)
    shutil.copy2(upstream/'src/rootfs/etc/own/udhcpd.conf',config/'udhcpd.conf')
    (config/'name').write_text('Codex\n')
    (config/'apps').write_text("# Codex home — Terminal is in Settings; no Notes or upstream games.\nBible|book|/opt/pw3-bible/run-kindle.sh\nKOReader|book|/usr/local/bin/pw3-koreader\nGames|cube|/usr/local/bin/pw3-games\nWi-Fi|wifi|/usr/local/bin/wifi\nSettings|gear|/usr/local/bin/settings\n")
    # Keep upstream license and source provenance while branding the built UI.
    # Source-level path replacements can be added later without importing games.
    return upstream


def package_netsurf_trial(repo, root, destination):
    """Isolated RAM-only NetSurf trial: no system paths overwritten on extraction."""
    # Keep the current Alpine runtime's existing binaries/boot path untouched.
    selected = ('lib', 'usr/lib', 'usr/bin/netsurf-framebuffer',
                'usr/share/netsurf', 'usr/share/fonts', 'usr/share/codex')
    with tarfile.open(destination, 'w:gz', compresslevel=6, dereference=False) as tar:
        for relative in selected:
            path = root / relative
            if not path.exists():
                raise RuntimeError('Standalone NetSurf trial missing: ' + relative)
            tar.add(path, arcname=relative, recursive=True)
        for name, dest in (('codex-browser-trial.sh', 'codex-browser-trial.sh'),
                           ('README-NETSURF-TRIAL.txt', 'README-NETSURF-TRIAL.txt')):
            tar.add(repo / 'build/pw3os' / name, arcname=dest)
    if destination.stat().st_size < 500000:
        raise RuntimeError('NetSurf trial tar unexpectedly small')
    return destination


def assemble_runner(repo,output):
    src=(repo/'build/pw3os/pw3os-boot-once.sh').read_text()
    assert 'alpine-debug.img' in src and 'timeout -t 330' in src
    src=src.replace('alpine-debug.img','alpine-os.img')
    src=src.replace('"$BB" timeout -t 330 "$BB" chroot "$R" /bin/sh /mnt/us/pw3os/PW3-DEBUG-INIT-WIFI42.sh --run',
                    '"$BB" chroot "$R" /sbin/own-init')
    if 'timeout -t 330' in src:raise RuntimeError('Still a short-lived trial, not primary Alpine')
    src=src.replace('RESULT: ALPINE_SSH_DEBUG_SESSION_PASS_STOCK_CONTINUES',
                    'RESULT: PW3OS_PRIMARY_SESSION_CLEANLY_RELEASED')
    src=src.replace('RESULT: ALPINE_SSH_DEBUG_SESSION_ERROR_RC=',
                    'RESULT: PW3OS_PRIMARY_SESSION_ERROR_RC=')
    (output/'pw3os-boot-once.sh').write_text(src)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    repo=Path('/repo')
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    if list(out.iterdir()):
        raise RuntimeError('Output directory must be empty (protect earlier builds)')
    stage=Path('/private-stage') if Path('/private-stage').is_dir() else None
    life_apk=Path('/private/LifeBible.apk') if Path('/private/LifeBible.apk').is_file() else None
    size=int(os.environ.get('PW3_IMAGE_MIB','768'))
    if not 512<=size<=2048:raise RuntimeError('Image size outside 512-2048 MiB')
    with tempfile.TemporaryDirectory(prefix='pw3os-build-') as tmp:
        work=Path(tmp)
        root=work/'rootfs';root.mkdir()
        mini_url=f'{ALPINE}/releases/armv7/{MINI}'
        minirootfs=download(mini_url,work/MINI,official_hash(mini_url))
        run('tar','-xpzf',minirootfs,'-C',root)
        if (root/'etc/alpine-release').read_text().strip()!='3.24.3':
            raise RuntimeError('Alpine 3.24.3 minirootfs version mismatch')
        upstream=install_codex_core(repo,work,root)
        packages=install_pkgs(work,root,upstream)
        browser=verify_browser_staged(root,packages)
        browser_launcher=root/'usr/local/bin/codex-browser'
        shutil.copy2(repo/'build/pw3os/codex-browser.sh',browser_launcher)
        browser_launcher.chmod(0o755)
        # A separate, opt-in *headless* test bridge; never a boot service.
        libdir=root/'usr/local/lib/codex'
        libdir.mkdir(parents=True,exist_ok=True)
        crosscompile_browser_shared(repo/'build/pw3os/codex-sdl-live-capture.c',
                                    libdir/'libcodex-sdl-capture.so')
        shutil.copy2(repo/'build/pw3os/verify_direct_sdl.py',
                     libdir/'verify_direct_sdl.py')
        # Live trial remains off by default. Only an attended standalone
        # command can activate its physical display and touch input gates.
        crosscompile_browser_shared(repo/'build/pw3os/codex-sdl-touch-input.c',
                                    libdir/'libcodex-sdl-touch-input.so',
                                    extra=(str(repo/'build/pw3os/codex-browser-viewport.c'),))
        shutil.copy2(repo/'build/pw3os/codex-browser-live-frames.py',
                     libdir/'codex-browser-live-frames.py')
        live_launcher=root/'usr/local/bin/codex-browser-live-trial'
        shutil.copy2(repo/'build/pw3os/codex-browser-live-trial.sh',live_launcher)
        live_launcher.chmod(0o755)
        # Home tile preview is a *different* lifecycle: Home waits for the
        # child and redraws itself, so never stop or restart Home here.
        home_preview=root/'usr/local/bin/codex-browser-home-preview'
        shutil.copy2(repo/'build/pw3os/codex-browser-home-preview.sh',
                     home_preview)
        home_preview.chmod(0o755)
        # Native grayscale conversion avoids the 1.55-million-pixel
        # Python loop that only published three frames in 30 seconds.
        crosscompile(repo/'build/pw3os/codex-browser-fast-frames.c',
                     root/'usr/local/bin/codex-browser-fast-frames',
                     target='arm-linux.3.0.35-musleabi')
        browser['home_preview_staged']=True
        browser['home_preview_enabled_by_default']=False
        browser['headless_capture_staged']=True
        browser['headless_on_device_verified']=False
        crosscompile(repo/'build/pw3os/codex-display-probe.c',
                     root/'usr/local/bin/codex-display-probe',
                     target='arm-linux.3.0.35-musleabi')
        crosscompile(repo/'build/pw3os/codex-browser-panel-preview.c',
                     root/'usr/local/bin/codex-browser-panel-preview',
                     target='arm-linux.3.0.35-musleabi')
        crosscompile(repo/'build/pw3os/codex-browser-touch-probe.c',
                     root/'usr/local/bin/codex-browser-touch-probe',
                     extra=(str(repo/'build/pw3os/codex-touch-bridge.c'),),
                     target='arm-linux.3.0.35-musleabi')
        smoke_dir=root/'usr/share/codex'
        smoke_dir.mkdir(parents=True,exist_ok=True)
        shutil.copy2(repo/'build/pw3os/browser-smoke.html',smoke_dir/'browser-smoke.html')
        shutil.copy2(repo/'build/pw3os/browser-interactive.html',
                     smoke_dir/'browser-interactive.html')
        package_netsurf_trial(repo,root,out/'codex-netsurf-test-bundle.tar.gz')
        compat=install_koreader(work,root,stage)
        bible_type=install_bible(repo,work,root,life_apk)
        (root/'sbin').mkdir(exist_ok=True)
        shutil.copy2(repo/'build/pw3os/pw3-init.sh',root/'sbin/own-init')
        (root/'sbin/own-init').chmod(0o755)
        for p in ['dev','dev/pts','proc','sys','mnt/us','run','tmp','var/log','root/.ssh']:
            (root/p).mkdir(parents=True,exist_ok=True)
        (root/'tmp').chmod(0o1777)
        (root/'root/.ssh').chmod(0o700)
        (root/'etc/hostname').write_text('pw3os\n')
        (root/'etc/resolv.conf').write_text('nameserver 1.1.1.1\n')
        img=out/'alpine-os.img'
        run('mke2fs','-q','-F','-t','ext3','-L','pw3os',
            '-E','root_owner=0:0','-d',root,img,f'{size}M')
        run('e2fsck','-fn',img,acceptable=(0,))
        # Small on-device overlay: deploy via Alpine SSH without replacing the 768-MiB image.
        for source,destination in ((root/'etc/own/apps',out/'apps'),
                                   (root/'usr/local/bin/home',out/'home'),
                                   (root/'usr/local/bin/pw3-games',out/'pw3-games'),
                                   (root/'usr/local/bin/pw3-koreader',out/'pw3-koreader'),
                                   (root/'usr/local/bin/settings',out/'settings'),
                                   (root/'usr/local/bin/codex-browser',out/'codex-browser'),
                                   (root/'usr/local/lib/codex/libcodex-sdl-capture.so',
                                    out/'libcodex-sdl-capture.so'),
                                   (root/'usr/local/lib/codex/verify_direct_sdl.py',
                                    out/'verify_direct_sdl.py'),
                                   (root/'usr/local/lib/codex/libcodex-sdl-touch-input.so',
                                    out/'libcodex-sdl-touch-input.so'),
                                   (root/'usr/local/lib/codex/codex-browser-live-frames.py',
                                    out/'codex-browser-live-frames.py'),
                                   (root/'usr/local/bin/codex-browser-live-trial',
                                    out/'codex-browser-live-trial'),
                                   (root/'usr/local/bin/codex-browser-home-preview',
                                    out/'codex-browser-home-preview'),
                                   (root/'usr/local/bin/codex-browser-fast-frames',
                                    out/'codex-browser-fast-frames'),
                                   (root/'usr/share/codex/browser-interactive.html',
                                    out/'browser-interactive.html'),
                                   (root/'usr/local/bin/codex-display-probe',out/'codex-display-probe'),
                                   (root/'usr/local/bin/codex-browser-panel-preview',
                                    out/'codex-browser-panel-preview'),
                                   (root/'usr/local/bin/codex-browser-touch-probe',
                                    out/'codex-browser-touch-probe'),
                                   (root/'usr/local/lib/pw3os/koreader_update.py',out/'koreader_update.py'),
                                   (root/'usr/local/lib/pw3os/2-pw3os-autoupdate.lua',out/'2-pw3os-autoupdate.lua')):
            shutil.copy2(source,destination)
        assemble_runner(repo,out)
        shutil.copy2(repo/'build/pw3os/pw3_debugmount.c',out/'pw3_debugmount.c')
        crosscompile(out/'pw3_debugmount.c',out/'pw3-debugmount',target='arm-linux.3.0.35-musleabi',freestanding=True)
        names=['alpine-os.img','pw3-debugmount','pw3os-boot-once.sh','apps','home','pw3-games','pw3-koreader','settings','codex-browser','libcodex-sdl-capture.so','verify_direct_sdl.py','libcodex-sdl-touch-input.so','codex-browser-live-frames.py','codex-browser-live-trial','codex-browser-home-preview','browser-interactive.html','codex-display-probe','codex-browser-panel-preview','codex-browser-touch-probe','codex-netsurf-test-bundle.tar.gz','koreader_update.py','2-pw3os-autoupdate.lua']
        (out/'SHA256SUMS').write_text(''.join(f'{sha256(out/n)}  {n}\n' for n in names))
        manifest={'project':'Codex','alpine':'3.24.3','kernel':'Amazon 3.0.35-lab126',
                  'codex_ui_upstream_commit':CODEX_UI_UPSTREAM_REF,'codex_ui_apps_included':list(('home','wifi','settings','term','splash')),
                  'codex_ui_games_included':[],'pw3_games':['Memory Match','Sudoku'],
                  'home_menu':['Bible','KOReader','Games','Wi-Fi','Settings'],
                  'settings_submenu':['Terminal','Restart','Power off','Stock Kindle UI','Battery','About'],
                  'bible':bible_type,'koreader':KOREADER_VER,'koreader_stage_compat_included':compat,
                  'koreader_runtime_verified':False,'display_runtime_verified':False,
                  'image_mib':size,'alpine_packages':packages,'browser':browser}
        (out/'BUILD-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
        shutil.copy2(repo/'build/pw3os/README-DEPLOY.txt',out/'README-DEPLOY.txt')
    print('RESULT: PW3OS_ALPINE_3243_FULL_IMAGE_BUILT_NOT_INSTALLED')
    print('OUTPUT',out)


if __name__=='__main__':main()
