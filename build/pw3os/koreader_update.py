#!/usr/bin/env python3
"""PW3-OS KOReader updater: upstream payload, stable Alpine compatibility.

Runs under Alpine (musl/Python 3), not KOReader's relocated GNU libc.
KOReader's own Exit(85) triggers 'activate' from the persistent launcher.
Original KOReader files are never patched; userpatch lives in KO_HOME.
"""
import fcntl
import gzip
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

HOME = Path("/mnt/us/pw3os/koreader-data")
CACHE = Path("/mnt/us/pw3os/koreader-updater")
RELEASES = Path("/opt/koreader-releases")
CURRENT = Path("/opt/koreader")
STATE = CACHE / "state.json"
PENDING = CACHE / "pending.json"
LOG = CACHE / "events.log"
LOADER = Path("/opt/koreader-compat/gnu/lib/ld-linux.so.3")
GNU_LIB = ":".join((
    "/opt/koreader-compat/gnu/lib",
    "/opt/koreader-compat/app/ffi",
    "/opt/koreader/libs",
    "/opt/koreader/ffi",
))
OTA_BASE = "https://ota.koreader.rocks/"
INDEX = "koreader-kindlepw2-latest-stable.zsync"
NAME_RE = re.compile(r"^koreader-kindlepw2-(v[0-9]{4}\.[0-9]{2}(?:\.[0-9]+)?(?:-[0-9]+-g[0-9a-f]+_[0-9-]+)?)\.targz$")
REV_RE = re.compile(r"^v[0-9]{4}\.[0-9]{2}(?:\.[0-9]+)?(?:-[0-9]+-g[0-9a-f]+_[0-9-]+)?$")
NEEDED = ("luajit", "reader.lua", "koreader.sh", "git-rev",
          "setupkoenv.lua", "frontend/userpatch.lua", "frontend/ui/otamanager.lua")
MAX_PAYLOAD = 300 * 1024 * 1024

def record(event, details=""):
    CACHE.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    with LOG.open("a") as f:
        f.write(f"{now}\t{event}\t{details}\n")
    print(f"RESULT: {event}" + (f" {details}" if details else ""), flush=True)

def hold(reason):
    record("HOLD", reason)
    raise SystemExit(3)

def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".pw3os-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(value, f, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)

def get_json(path):
    return json.loads(path.read_text()) if path.is_file() else {}

def curl(url, dest, timeout=120):
    if not url.startswith(OTA_BASE) or url.count("/") < 3:
        hold("UNTRUSTED_OTA_URL")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".downloading")
    if tmp.exists():
        tmp.unlink()
    command = ["curl", "--fail", "--show-error", "--silent", "--location",
               "--proto", "=https", "--proto-redir", "=https",
               "--connect-timeout", "12", "--max-time", str(timeout),
               "--retry", "2", "--output", str(tmp), url]
    try:
        subprocess.run(command, check=True, timeout=timeout + 50)
        if not tmp.is_file() or tmp.stat().st_size < 100:
            hold("OTA_DOWNLOAD_EMPTY")
        os.replace(tmp, dest)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        hold("OTA_DOWNLOAD_FAILED " + str(e)[:160])
    finally:
        tmp.unlink(missing_ok=True)

def metadata():
    path = CACHE / "latest-stable.zsync"
    curl(OTA_BASE + INDEX, path)
    # A .zsync contains a short ASCII header followed by binary data.
    header = path.read_bytes()[:8192].split(b"\n\n", 1)[0]
    fields = {}
    for raw in header.splitlines():
        if b": " in raw:
            key, val = raw.split(b": ", 1)
            fields[key.decode("ascii")] = val.decode("ascii").strip()
    name = fields.get("Filename", "")
    match = NAME_RE.fullmatch(name)
    if not match or fields.get("Z-URL") != name:
        hold("INVALID_OTA_FILENAME")
    digest = fields.get("SHA-1", "")
    if not re.fullmatch(r"[0-9a-f]{40}", digest):
        hold("INVALID_OTA_SHA1")
    try:
        length = int(fields["Length"])
    except (KeyError, ValueError):
        hold("INVALID_OTA_LENGTH")
    if not (1000000 <= length <= MAX_PAYLOAD):
        hold("INVALID_OTA_SIZE")
    return {"filename": name, "revision": match.group(1),
            "tar_sha1": digest, "tar_size": length}

def installed_revision():
    try:
        return (CURRENT / "git-rev").read_text().strip()
    except OSError:
        return "unknown"

def check():
    meta = metadata()
    current = installed_revision()
    print("CURRENT=" + current)
    print("AVAILABLE=" + meta["revision"])
    print("FILENAME=" + meta["filename"])
    return meta

def verified_tar(tarball, meta):
    digest = hashlib.sha1()
    length = 0
    # zsync SHA-1/Length describe the *uncompressed* tar, not the gzip
    # bytes. Published .tar.xz SHA-256 sidecars are stale for this build.
    try:
        with gzip.open(tarball, "rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                length += len(chunk)
                if length > MAX_PAYLOAD:
                    hold("OTA_TAR_OVERSIZED")
                digest.update(chunk)
    except (OSError, EOFError) as e:
        hold("OTA_GZIP_DAMAGED " + str(e)[:100])
    if length != meta["tar_size"] or digest.hexdigest() != meta["tar_sha1"]:
        hold("OTA_UNCOMPRESSED_TAR_CHECKSUM_MISMATCH")
    record("OTA_TAR_VERIFIED", meta["revision"])

def unpack(tarball, dest):
    if dest.exists():
        hold("STAGING_PATH_ALREADY_EXISTS")
    dest.mkdir(parents=True)
    total = 0
    entries = 0
    try:
        with tarfile.open(tarball, "r:gz") as t:
            for member in t:
                entries += 1
                if entries > 20000:
                    hold("EXCESSIVE_TAR_MEMBERS")
                p = PurePosixPath(member.name)
                if p.is_absolute() or ".." in p.parts or not p.parts:
                    hold("UNSAFE_TAR_PATH")
                if p.parts[0] not in ("koreader", "extensions"):
                    hold("UNEXPECTED_TAR_ROOT")
                if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                    hold("UNSAFE_TAR_MEMBER")
                if not (member.isdir() or member.isfile()):
                    hold("UNSUPPORTED_TAR_MEMBER")
                if p.parts[0] != "koreader" or len(p.parts) == 1:
                    continue
                target = dest.joinpath(*p.parts[1:])
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    total += member.size
                    if total > MAX_PAYLOAD:
                        hold("EXCESSIVE_TAR_PAYLOAD")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with t.extractfile(member) as inf, target.open("wb") as outf:
                        shutil.copyfileobj(inf, outf, 1024 * 1024)
                    target.chmod(member.mode & 0o777)
        for name in NEEDED:
            if not (dest / name).is_file():
                hold("MISSING_UPDATE_RUNTIME " + name)
        for name in ("luajit", "fbink"):
            file = dest / name
            if not file.is_file():
                hold("MISSING_UPDATE_BINARY " + name)
            file.chmod(file.stat().st_mode | 0o111)
        record("OTA_EXTRACTION_VERIFIED", str(entries))
    except BaseException:
        shutil.rmtree(dest, ignore_errors=True)
        raise

def smoke(candidate):
    if not LOADER.is_file():
        hold("GNU_COMPAT_RUNTIME_MISSING")
    # The installed private GNU loader remains outside /opt/koreader.
    libraries = GNU_LIB.replace("/opt/koreader/libs", str(candidate / "libs")).replace(
        "/opt/koreader/ffi", str(candidate / "ffi"))
    env = os.environ.copy()
    env.update({"LD_LIBRARY_PATH": libraries, "HOME": "/root",
                "KO_HOME": str(HOME), "LC_ALL": "C"})
    commands = [
        [str(LOADER), "--library-path", libraries, str(candidate / "luajit"), "-v"],
        [str(LOADER), "--library-path", libraries, str(candidate / "luajit"),
         "-e", 'require("setupkoenv"); require("userpatch"); print("PASS")'],
    ]
    for cmd in commands:
        result = subprocess.run(cmd, cwd=candidate, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, timeout=45)
        if result.returncode != 0:
            record("CANDIDATE_RUNTIME_TEST_FAILED", result.stdout[-500:])
            hold("CANDIDATE_RUNTIME_INCOMPATIBLE")
    record("CANDIDATE_GNU_LUAJIT_PASS")

def stage():
    CACHE.mkdir(parents=True, exist_ok=True)
    RELEASES.mkdir(parents=True, exist_ok=True)
    meta = metadata()
    if meta["revision"] == installed_revision():
        record("KOREADER_ALREADY_CURRENT")
        return
    target = RELEASES / meta["revision"]
    if not REV_RE.fullmatch(meta["revision"]):
        hold("UNSAFE_RELEASE_NAME")
    if PENDING.exists():
        old = get_json(PENDING)
        if old.get("revision") == meta["revision"] and Path(old.get("candidate", "")).is_dir():
            record("OTA_ALREADY_STAGED", meta["revision"])
            return
        hold("OTHER_OTA_PENDING")
    if target.exists():
        hold("RELEASE_TARGET_ALREADY_EXISTS")
    tarball = CACHE / meta["filename"]
    curl(OTA_BASE + meta["filename"], tarball, timeout=600)
    verified_tar(tarball, meta)
    # Fail safely instead of removing the running app when the ext3 image
    # lacks capacity to hold both old and candidate directories.
    disk = shutil.disk_usage(RELEASES)
    if disk.free < meta["tar_size"] + 24 * 1024 * 1024:
        hold("INSUFFICIENT_ALPINE_SPACE " + str(disk.free))
    temp = RELEASES / (".stage-" + meta["revision"])
    unpack(tarball, temp)
    smoke(temp)
    os.rename(temp, target)
    atomic_json(PENDING, {"candidate": str(target), "revision": meta["revision"],
                          "filename": meta["filename"], "sha1": meta["tar_sha1"]})
    record("KOREADER_STAGED_READY_FOR_EXIT_85", meta["revision"])
    # Keep the compressed archive on the userstore until switch is healthy.

def link_current(target):
    tmp = Path("/opt/.koreader-next")
    if tmp.exists() or tmp.is_symlink():
        tmp.unlink()
    os.symlink(str(target), tmp)
    os.replace(tmp, CURRENT)

def activate():
    pending = get_json(PENDING)
    candidate = Path(pending.get("candidate", ""))
    if not pending or candidate.parent != RELEASES or not candidate.is_dir():
        hold("NO_VALID_PENDING_UPDATE")
    smoke(candidate)
    old_state = get_json(STATE)
    if old_state.get("phase") == "first-launch":
        hold("PREVIOUS_FIRST_LAUNCH_NOT_VERIFIED")
    # Persist rollback intent before moving any directories.
    if CURRENT.is_symlink():
        previous = CURRENT.resolve(strict=True)
        atomic_json(STATE, {"phase": "installing", "previous": str(previous),
                            "candidate": str(candidate)})
        link_current(candidate)
    elif CURRENT.is_dir():
        previous = RELEASES / ("original-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"))
        atomic_json(STATE, {"phase": "installing", "previous": str(previous),
                            "candidate": str(candidate)})
        os.rename(CURRENT, previous)
        link_current(candidate)
    else:
        hold("CURRENT_KOREADER_MISSING")
    atomic_json(STATE, {"phase": "first-launch", "previous": str(previous),
                        "candidate": str(candidate)})
    PENDING.unlink()
    record("KOREADER_SWITCHED_FIRST_LAUNCH", pending["revision"])

def recover():
    state = get_json(STATE)
    if CURRENT.is_dir():
        return
    previous = Path(state.get("previous", ""))
    if state.get("phase") in ("installing", "first-launch") and previous.is_dir():
        link_current(previous)
        record("KOREADER_RECOVERED_PREVIOUS")
        return
    hold("CURRENT_MISSING_NO_SAFE_RECOVERY")

def finish(success):
    state = get_json(STATE)
    if state.get("phase") != "first-launch":
        return False
    previous = Path(state.get("previous", ""))
    if not previous.is_dir():
        hold("PREVIOUS_BACKUP_MISSING")
    if not success:
        if CURRENT.is_symlink():
            link_current(previous)
            atomic_json(STATE, {"phase": "rolled-back", "previous": str(previous),
                                "failed": state["candidate"]})
            record("KOREADER_FIRST_LAUNCH_ROLLED_BACK")
            return True
        hold("CANNOT_ROLLBACK_NONLINK_CURRENT")
    atomic_json(STATE, {"phase": "healthy", "previous": str(previous),
                        "active": state["candidate"]})
    record("KOREADER_UPDATE_ACCEPTED")
    return False

def manual_rollback():
    state = get_json(STATE)
    previous = Path(state.get("previous", ""))
    if not previous.is_dir():
        hold("NO_PREVIOUS_RELEASE")
    if not CURRENT.is_symlink():
        hold("CURRENT_NOT_MANAGED")
    link_current(previous)
    atomic_json(STATE, {"phase": "rolled-back", "previous": str(previous)})
    record("KOREADER_MANUALLY_ROLLED_BACK")

def main():
    if len(sys.argv) != 2 or sys.argv[1] not in (
        "check", "stage", "activate", "recover", "first-launch-ok",
        "first-launch-failed", "rollback", "status"):
        raise SystemExit("Usage: pw3-ko-update check|stage|activate|recover|first-launch-ok|first-launch-failed|rollback|status")
    CACHE.mkdir(parents=True, exist_ok=True)
    op = sys.argv[1]
    if op == "check":
        check()
    elif op == "stage":
        stage()
    elif op == "activate":
        activate()
    elif op == "recover":
        recover()
    elif op == "first-launch-ok":
        finish(True)
    elif op == "first-launch-failed":
        finish(False)
    elif op == "rollback":
        manual_rollback()
    elif op == "status":
        print(json.dumps({"installed": installed_revision(),
                          "state": get_json(STATE), "pending": get_json(PENDING)}, indent=2))

if __name__ == "__main__":
    main()
