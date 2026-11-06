#!/usr/bin/env python3
"""Offline Tecarta v8 audio URL *candidates*, not a media downloader.

Only evidence-backed client-side v8 formats are implemented here. The v10
Life Bible product IDs, catalogue flags, resource availability, entitlements,
and any expiring / signed URLs have NOT been verified against a live server.
No networking occurs on import or when building a catalog.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from typing import Iterator

BASE = "https://cf-audio.tecartabible.com"
# The reader's book order and Tecarta IDs must stay in sync with build.py.
NAMES = (
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Songs", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel",
    "Amos", "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk",
    "Zephaniah", "Haggai", "Zechariah", "Malachi", "Matthew", "Mark",
    "Luke", "John", "Acts", "Romans", "1 Corinthians", "2 Corinthians",
    "Galatians", "Ephesians", "Philippians", "Colossians",
    "1 Thessalonians", "2 Thessalonians", "1 Timothy", "2 Timothy",
    "Titus", "Philemon", "Hebrews", "James", "1 Peter", "2 Peter",
    "1 John", "2 John", "3 John", "Jude", "Revelation",
)
# Seven gaps are deliberate: Tecarta's IDs are NOT sequential 1..66.
SKIPPED_TECARTA_IDS = frozenset({17, 18, 20, 21, 27, 28, 32})
BOOK_IDS = tuple(i for i in range(1, 74) if i not in SKIPPED_TECARTA_IDS)
CHAPTER_COUNTS = (
    50, 40, 27, 36, 34, 24, 21, 4, 31, 24, 22, 25, 29, 36, 10, 13,
    10, 42, 150, 31, 12, 8, 66, 52, 5, 48, 12, 14, 3, 9, 1, 4, 7,
    3, 3, 3, 2, 14, 4, 28, 16, 24, 21, 28, 16, 16, 13, 6, 6, 4,
    4, 5, 3, 6, 4, 3, 1, 13, 5, 5, 3, 5, 1, 1, 1, 22,
)
assert len(NAMES) == len(BOOK_IDS) == len(CHAPTER_COUNTS) == 66
assert sum(CHAPTER_COUNTS[:39]) == 929 and sum(CHAPTER_COUNTS[39:]) == 260
NAME_TO_INDEX = {name.casefold().replace(" ", ""): i for i, name in enumerate(NAMES)}
INDEX_BY_TECARTA_ID = {book_id: i for i, book_id in enumerate(BOOK_IDS)}

# Observed static catalogue records (Life Bible v10.2.665), NOT v8 audio-server
# confirmations or proof of access to downloadable media.
PRODUCT_IDS = {"kjv": 8009, "csb": 8231, "breathe": 8026}


@dataclass(frozen=True)
class Candidate:
    edition: str
    book: str
    book_id: int
    chapter: int
    scheme: str
    url: str


def volume_id(raw: int) -> int:
    """AppSingleton.getVolumeID(), as extracted from Tecarta Bible v8.0.2."""
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        raise ValueError("volume ID must be a positive integer")
    return raw - 300 if 301 <= raw <= 399 or 8301 <= raw <= 8399 else raw


def book_id_for(name_or_id: str | int) -> int:
    """Resolve a canonical 66-book name or a *canonical* Tecarta book ID."""
    if isinstance(name_or_id, bool):
        raise ValueError("invalid book")
    if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdecimal()):
        book_id = int(name_or_id)
        if book_id not in INDEX_BY_TECARTA_ID:
            raise ValueError("not a canonical 66-book Tecarta ID")
        return book_id
    if not isinstance(name_or_id, str):
        raise ValueError("invalid book")
    idx = NAME_TO_INDEX.get(name_or_id.casefold().replace(" ", ""))
    if idx is None:
        raise ValueError("unknown book")
    return BOOK_IDS[idx]


def validate_chapter(book_id: int, chapter: int) -> None:
    if book_id not in INDEX_BY_TECARTA_ID:
        raise ValueError("not a canonical Tecarta book ID")
    if isinstance(chapter, bool) or not isinstance(chapter, int) or not 1 <= chapter <= CHAPTER_COUNTS[INDEX_BY_TECARTA_ID[book_id]]:
        raise ValueError("chapter out of range for this book")


def audio_url(volume: int, book_id: int, chapter: int, scheme: str) -> str:
    """Construct an *unverified* v8 URL. Never assume playable or public."""
    validate_chapter(book_id, chapter)
    vol = volume_id(volume)
    if scheme == "static":
        # Audio.getAudioFileHash(ref, volume, true): SHA256 of UTF-8 id_book_chapter_0
        digest = hashlib.sha256(f"{vol}_{book_id}_{chapter}_0".encode("utf-8")).digest()
        token = base64.urlsafe_b64encode(digest).decode("ascii")  # Android URL_SAFE retains '=' padding.
        return f"{BASE}/{vol}/chapters/{token}"
    if scheme == "dynamic":
        # AppSingleton.getAudioFileFromServer, whose JSON 'path' is the audio URL.
        return f"{BASE}/{vol}/audio-links/{book_id}_{chapter}.json"
    raise ValueError("scheme must be static or dynamic")


def candidates(edition: str) -> Iterator[Candidate]:
    """Enumerate both *possible* v8 paths; does not choose dynamicAudio mode."""
    if edition not in PRODUCT_IDS:
        raise ValueError("edition must be kjv, csb, or breathe")
    first = 39 if edition == "breathe" else 0  # Breathe is NT-only.
    for idx in range(first, len(NAMES)):
        for chapter in range(1, CHAPTER_COUNTS[idx] + 1):
            for scheme in ("static", "dynamic"):
                yield Candidate(edition, NAMES[idx], BOOK_IDS[idx], chapter, scheme,
                                audio_url(PRODUCT_IDS[edition], BOOK_IDS[idx], chapter, scheme))
