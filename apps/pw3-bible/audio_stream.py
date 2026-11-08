#!/usr/bin/env python3
"""Resolve a single Bible chapter audio stream at Play time.

No recording is downloaded to disk, pre-cached, or shipped. Lookups are limited
to one explicitly requested chapter. All three editions remain selectable;
unknown/denied endpoints fail closed. This is not a subscription bypass.
"""
import base64
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = "https://cf-audio.tecartabible.com"
VOLUMES = {"kjv": 8009, "csb": 8231, "breathe": 8026}
BOOK_IDS = frozenset(set(range(1, 74)) - {17, 18, 20, 21, 27, 28, 32})
MAX_METADATA = 8192


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def accepted_dynamic_media(value):
    """Constrain URLs returned by Tecarta metadata to recognized audio hosts."""
    if not isinstance(value, str) or len(value) > 4096:
        return False
    if any(ord(char) < 33 or ord(char) == 127 for char in value):
        return False
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
        return False
    return (
        host == "cf-audio.tecartabible.com"
        or host == "cloud.faithcomesbyhearing.com"
        or host.endswith(".faithcomesbyhearing.com")
    )


def candidate_urls(edition, book, chapter):
    if edition not in VOLUMES or book not in BOOK_IDS or not 1 <= chapter <= 150:
        raise ValueError("unsupported edition or chapter")
    if edition == "breathe" and book < 47:
        raise ValueError("Breathe NLT is New Testament only")
    volume = VOLUMES[edition]
    text = ("%s_%s_%s_0" % (volume, book, chapter)).encode("utf-8")
    digest = hashlib.sha256(text).digest()
    token = base64.urlsafe_b64encode(digest).decode("ascii")
    return (
        "%s/%d/audio-links/%d_%d.json" % (BASE, volume, book, chapter),
        "%s/%d/chapters/%s" % (BASE, volume, token),
    )


def resolve_stream(edition, book, chapter, opener=None):
    """Return a streaming media URL or None; NEVER fetch the media payload."""
    try:
        dynamic, static = candidate_urls(edition, book, chapter)
    except (TypeError, ValueError):
        return None
    opener = opener or build_opener(NoRedirect())
    try:
        req = Request(dynamic, headers={"Accept": "application/json"})
        with opener.open(req, timeout=8) as response:
            if response.status != 200:
                return None
            raw = response.read(MAX_METADATA + 1)
            if len(raw) <= MAX_METADATA:
                value = json.loads(raw.decode("utf-8"))
                if isinstance(value, dict) and accepted_dynamic_media(value.get("path")):
                    return value["path"]
    except (HTTPError, URLError, OSError, TimeoutError, UnicodeError, ValueError):
        pass

    # A HEAD request checks one hashed v8 media candidate without reading audio.
    try:
        req = Request(static, method="HEAD")
        with opener.open(req, timeout=8) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if response.status in (200, 206) and (
                content_type.startswith("audio/")
                or content_type.startswith("application/octet-stream")
            ):
                return static
    except (HTTPError, URLError, OSError, TimeoutError):
        pass
    return None
