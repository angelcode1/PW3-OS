#!/usr/bin/env python3
"""Build verified PW3 archives from a full local Life Bible backup."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("backup", "apk", "web", "kjv", "asv", "reader", "output-dir"):
        parser.add_argument("--" + option, required=True, type=Path)
    parser.add_argument("--jesus-calling-dir", type=Path)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()
    backup = args.backup.resolve()
    if not backup.is_dir() or args.batch_size < 1:
        parser.error("supply an existing backup folder and a positive batch size")
    volumes = sorted(
        (path for path in backup.glob("*.sqlite")
         if path.is_file() and path.stem.isascii() and path.stem.isdecimal()),
        key=lambda path: (int(path.stem), path.name),
    )
    if not volumes:
        parser.error("backup contains no numbered SQLite files")
    for option in ("apk", "web", "kjv", "asv", "reader"):
        if not getattr(args, option).is_file():
            parser.error(f"--{option} must point to an existing file")

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    importer = Path(__file__).resolve().with_name("build.py")
    base = [sys.executable, str(importer)]
    for option in ("apk", "web", "kjv", "asv"):
        base.extend(("--" + option, str(getattr(args, option).resolve())))
    verified, failed = [], []

    def build_batch(group, name):
        log = output / f"{name}.log"
        final = output / f"{name}.pw3"
        ids = ", ".join(path.stem for path in group)
        with tempfile.TemporaryDirectory(dir=output) as temp:
            staging = Path(temp)
            archive = staging / "bible.pw3"
            command = [*base, "--life-bible-dir", temp, "--output", str(archive)]
            for path in group:
                (staging / path.name).symlink_to(path.resolve())
                companion = backup / path.stem
                if companion.is_dir():
                    (staging / path.stem).symlink_to(companion.resolve(), target_is_directory=True)
            if args.jesus_calling_dir and any(path.stem == "1306" for path in group):
                command.extend(("--jesus-calling-dir", str(args.jesus_calling_dir.resolve())))
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            log.write_bytes(result.stdout)
            if result.returncode:
                limit = any(message in result.stdout for message in
                            (b"100,000-page limit", b"2 GiB limit"))
                if limit and len(group) > 1:
                    middle = len(group) // 2
                    print(f"{name}: over capacity; splitting {ids}", flush=True)
                    build_batch(group[:middle], name + "a")
                    build_batch(group[middle:], name + "b")
                    return
                failed.append((name, ids))
                print(f"{name}: build failed for {ids}; see {log.name}", flush=True)
                return
            with log.open("ab") as handle:
                check = subprocess.run([str(args.reader.resolve()), str(archive), "--verify"],
                                       stdout=handle, stderr=subprocess.STDOUT)
            if check.returncode:
                failed.append((name, ids))
                print(f"{name}: verification failed; see {log.name}", flush=True)
                return
            shutil.move(str(archive), str(final))
        verified.append((name, ids))
        print(f"{name}: verified {ids}; see {log.name} for import coverage", flush=True)

    for start in range(0, len(volumes), args.batch_size):
        build_batch(volumes[start:start + args.batch_size],
                    f"bible-{start // args.batch_size + 1:02d}")
    print(f"Verified archives: {len(verified)}; failed batches: {len(failed)}")
    print(f"Archives and per-volume logs: {output}")
    return bool(failed)


if __name__ == "__main__":
    sys.exit(main())
