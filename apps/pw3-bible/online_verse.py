#!/usr/bin/env python3
"""Fetch one public Life Bible chapter for display, never writing downloaded text.

Public endpoint ONLY: https://cf-stream.tecartabible.com/8/<volume>/chapters/<book>_<chapter>.json
The signed CDN is intentionally unsupported. Volume IDs must be in the reviewed
online-translations.tsv installed alongside this script.
"""
import argparse
import gzip
import html
import json
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOST = "https://cf-stream.tecartabible.com"
BASE = Path(__file__).resolve().parent
CATALOG = BASE / "online-translations.tsv"
MAX_REPLY = 1_048_576
BOOK_IDS = frozenset(set(range(1, 74)) - {17, 18, 20, 21, 27, 28, 32})


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def volumes(path=CATALOG):
    result = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) != 3 or not fields[0].isascii() or not fields[0].isdecimal():
            raise ValueError("invalid online-translations.tsv")
        result.add(int(fields[0]))
    return result


def clean_text(text):
    if not isinstance(text, str):
        raise ValueError("verse must be text")
    # 'verses' is plain text in the observed protocol; reject raw tags rather
    # than executing or interpreting HTML in the native Kindle UI.
    text = re.sub(r"<[^>]{0,256}>", "", text)
    return " ".join(html.unescape(text).split())


def url_for(volume, book, chapter, permitted):
    if (volume not in permitted or book not in BOOK_IDS or
            not isinstance(chapter, int) or not 1 <= chapter <= 150):
        raise ValueError("unlisted translation or invalid reference")
    return f"{HOST}/8/{volume}/chapters/{book}_{chapter}.json"


def fetch_verses(volume, book, chapter, permitted, opener=None):
    url = url_for(volume, book, chapter, permitted)
    opener = opener or build_opener(NoRedirect())
    req = Request(url, headers={"Accept": "application/json", "Accept-Encoding": "identity"})
    with opener.open(req, timeout=8) as response:
        if response.status not in (200, 206):
            raise ValueError("unexpected response status")
        content_type = response.headers.get("Content-Type", "").lower()
        if "json" not in content_type:
            raise ValueError("unexpected content type")
        wire = response.read(MAX_REPLY + 1)
        if len(wire) > MAX_REPLY:
            raise ValueError("chapter exceeds response limit")
        if response.headers.get("Content-Encoding", "").lower() == "gzip" or wire[:2] == b"\x1f\x8b":
            import io
            with gzip.GzipFile(fileobj=io.BytesIO(wire)) as decoded:
                wire = decoded.read(MAX_REPLY + 1)
            if len(wire) > MAX_REPLY:
                raise ValueError("chapter exceeds expanded limit")
        data = json.loads(wire.decode("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("verses"), dict):
        raise ValueError("not a chapter with verses")
    result = []
    for number, value in data["verses"].items():
        if (not isinstance(number, str) or not number.isascii() or not number.isdecimal() or
                not 1 <= int(number) <= 199):
            raise ValueError("invalid verse number")
        verse = clean_text(value)
        if not verse or "\t" in verse or "\n" in verse:
            raise ValueError("invalid verse text")
        result.append((int(number), verse))
    result.sort()
    if not result or len({n for n, _ in result}) != len(result):
        raise ValueError("missing or repeated verses")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("volume", type=int)
    parser.add_argument("book", type=int)
    parser.add_argument("chapter", type=int)
    args = parser.parse_args(argv)
    try:
        verses = fetch_verses(args.volume, args.book, args.chapter, volumes())
    except (HTTPError, URLError, OSError, UnicodeError, ValueError, EOFError, json.JSONDecodeError) as exc:
        print(f"Online chapter unavailable: {type(exc).__name__}", file=sys.stderr)
        return 1
    # Only now emit complete output, so a failed parse does not show partial text.
    for number, verse in verses:
        print(f"V\t{number}\t{verse}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
