#!/usr/bin/env python3
"""Use the repository's real BibleReader schema; offline public Bibles, no proprietary APK."""
import argparse
import importlib.util
from pathlib import Path


def build(repo: Path, web: Path, kjv: Path, asv: Path, output: Path) -> int:
    source = repo / 'apps/pw3-bible/build.py'
    spec = importlib.util.spec_from_file_location('pw3_bible_importer', source)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    translations = {key: module.load_translation(path) for key, path in
                    [('WEB', web), ('KJV', kjv), ('ASV', asv)]}
    pages = module.Pages()
    pages.reserve('home')
    pages.page('home', 'PW3 Bible Reader', [
        module.link('Bible translations — WEB, KJV, ASV', 'bibles'),
        module.paragraph('Public-domain Bible edition. Life Bible study materials can be added locally.')
    ])
    module.add_bibles(pages, translations)
    output.parent.mkdir(parents=True, exist_ok=True)
    # The reader requires day_start >= 1; public-only archives contain no today links.
    pages.write(output, 1)
    print(f'PUBLIC_BIBLE_ARCHIVE_PAGES={len(pages.ids)}')
    return len(pages.ids)


def main():
    parser = argparse.ArgumentParser()
    for flag in ('repo','web','kjv','asv','output'):
        parser.add_argument('--'+flag, type=Path, required=True)
    args = parser.parse_args()
    build(args.repo, args.web, args.kjv, args.asv, args.output)


if __name__ == '__main__':
    main()
