#!/usr/bin/env python3
"""Read-only offline catalog generator and optional one-request metadata checker.

NO mass probing. NO media downloads. NO redirects. NO credentials or bypass.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from audio_catalog import PRODUCT_IDS, audio_url, book_id_for, candidates


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_one(url: str, scheme: str) -> int:
    """One HEAD (static) or small JSON GET (dynamic); never read audio payload."""
    method = "GET" if scheme == "dynamic" else "HEAD"
    req = Request(url, method=method, headers={"Accept": "application/json"})
    try:
        resp = build_opener(NoRedirect()).open(req, timeout=10)
    except HTTPError as e:
        print("HTTP status:", e.code)
        if e.code in (301, 302, 303, 307, 308):
            print("Redirect received; not followed or displayed")
        return 1
    except (URLError, TimeoutError, OSError) as e:
        print("Network error:", type(e).__name__)
        return 2
    with resp:
        print("HTTP status:", resp.status)
        print("Content-Type:", resp.headers.get("Content-Type", "unspecified"))
        if method == "HEAD":
            return 0
        raw = resp.read(8193)
        if len(raw) > 8192:
            print("Metadata exceeds 8192-byte limit; omitted")
            return 3
        try:
            value = json.loads(raw)
        except (ValueError, UnicodeError):
            print("Response is not JSON")
            return 3
        if not isinstance(value, dict):
            print("Response was not a JSON object")
            return 3
        print("JSON keys:", ", ".join(sorted(str(k) for k in value)))
        print("Audio path present:", isinstance(value.get("path"), str) and bool(value["path"]))
        print("Any signed/path/token value is intentionally not printed")
        return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--edition", required=True, choices=sorted(PRODUCT_IDS))
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--csv", help="Generate full unverified v8 candidates offline to this file")
    group.add_argument("--book", help="Single canonical book name or Tecarta ID")
    p.add_argument("--chapter", type=int, help="Required with --book")
    p.add_argument("--scheme", choices=("static", "dynamic", "both"), default="both")
    p.add_argument("--probe", action="store_true", help="Send exactly one HEAD or JSON GET request")
    p.add_argument("--authorized", action="store_true", help="Confirm legitimate access to the specific resource")
    a = p.parse_args(argv)
    if a.csv:
        if a.chapter is not None or a.probe or a.authorized:
            p.error("--csv is strictly offline; omit --chapter, --probe and --authorized")
        with open(a.csv, "w", newline="", encoding="utf-8") as fp:
            w = csv.writer(fp)
            w.writerow(("edition", "book", "tecarta_book_id", "chapter", "scheme", "candidate_url", "verification"))
            for candidate in candidates(a.edition):
                if a.scheme == "both" or candidate.scheme == a.scheme:
                    w.writerow((candidate.edition, candidate.book, candidate.book_id,
                                candidate.chapter, candidate.scheme, candidate.url,
                                "UNVERIFIED_V8_FORMAT_WITH_V10_ID"))
        print("Wrote offline candidate catalog:", a.csv)
        return 0
    if a.chapter is None:
        p.error("--chapter is required with --book")
    try:
        requested_book_id = book_id_for(a.book)
    except ValueError as exc:
        p.error(str(exc))
    if a.edition == "breathe" and requested_book_id < 47:
        p.error("Breathe Bible in this catalog is New Testament only")
    if a.probe and (not a.authorized or a.scheme == "both"):
        p.error("--probe requires --authorized and one --scheme (static or dynamic)")
    if a.authorized and not a.probe:
        p.error("--authorized may be used only with --probe")
    try:
        urls = [(s, audio_url(PRODUCT_IDS[a.edition], requested_book_id, a.chapter, s))
                for s in (("static", "dynamic") if a.scheme == "both" else (a.scheme,))]
    except ValueError as exc:
        p.error(str(exc))
    print("Only v8 algorithm confirmed; current v10 URLs and authorization UNVERIFIED")
    for scheme, url in urls:
        print(f"{scheme} candidate: {url}")
    if a.probe:
        return check_one(urls[0][1], urls[0][0])
    print("No network requests sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
