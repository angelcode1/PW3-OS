#!/usr/bin/env python3
"""Convert locally supplied Life Bible 10.2.665 assets into the PW3 reader's page archive."""
import argparse
import calendar
from collections import defaultdict
from datetime import date, timedelta
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
import struct
import tempfile
from zipfile import ZipFile
import zlib

ASSETS = "assets/flutter_assets/assets/"
CODES = """GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST
JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL
MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE
1JN 2JN 3JN JUD REV""".split()
NAMES = """Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|1 Samuel|2 Samuel|1 Kings|2 Kings|1 Chronicles|2 Chronicles|Ezra|Nehemiah|Esther|Job|Psalms|Proverbs|Ecclesiastes|Song of Songs|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|1 Corinthians|2 Corinthians|Galatians|Ephesians|Philippians|Colossians|1 Thessalonians|2 Thessalonians|1 Timothy|2 Timothy|Titus|Philemon|Hebrews|James|1 Peter|2 Peter|1 John|2 John|3 John|Jude|Revelation""".split("|")
IDS = [n for n in range(1, 74) if n not in {17, 18, 20, 21, 27, 28, 32}]
BOOKS = dict(zip(IDS, NAMES, strict=True))
BOOK_IDS = dict(zip(CODES, IDS, strict=True))
ABBR = dict(zip(IDS, CODES, strict=True))
DATE0 = date(2026, 1, 1)
DAY_TYPES = ("Daily Verse", "Daily TouchPoint", "Daily Devotional")
RANGE = re.compile(r"(\d+)/(\d+)/(\d+)(?:-(\d+)|_(\d+)/(\d+)/(\d+))?$")
TRANSLATIONS = {"WEB": "World English Bible", "KJV": "King James Version", "ASV": "American Standard Version"}
VPL_CODE = dict(EZE="EZK", JAM="JAS", PHI="PHP", JOE="JOL", JOH="JHN", MAR="MRK", SOL="SNG", NAH="NAM")
VPL_CODE.update({"1JO": "1JN", "2JO": "2JN", "3JO": "3JN"})


def clean(value):
    return " ".join(str(value).split())


class StudyText(HTMLParser):
    """Recover the displayed paragraphs from the study database's HTML fragments."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines = [[]]

    def handle_starttag(self, tag, attrs):
        if tag in {"p", "br", "li", "div"} and self.lines[-1]:
            self.lines.append([])
        elif tag == "span" and self.lines[-1]:
            self.lines[-1].append(" ")

    def handle_endtag(self, tag):
        if tag in {"p", "li", "div"} and self.lines[-1]:
            self.lines.append([])

    def handle_data(self, data):
        self.lines[-1].append(data)

    def paragraphs(self):
        return [line for parts in self.lines if (line := clean("".join(parts)))]


class Pages:
    def __init__(self):
        self.ids = {}
        self.rows = {}

    def reserve(self, key):
        if key not in self.ids:
            self.ids[key] = len(self.ids)
        return self.ids[key]

    def page(self, key, title, rows):
        self.reserve(key)
        if key in self.rows:
            raise ValueError(f"Duplicate page {key}")
        self.rows[key] = [("T", clean(title)), *rows]

    def write(self, path, daily_start):
        records = []
        for key in self.ids:
            lines = []
            for kind, *args in self.rows[key]:
                if kind in {"B", "G"}:
                    label, dest, anchor = args
                    idx = -1 if dest == "today" else self.ids[dest]
                    lines.append(f"{kind}\t{idx}\t{anchor}\t{clean(label)}")
                else:
                    lines.append("\t".join(map(str, (kind, *args))))
            data = ("\n".join(lines) + "\n").encode()
            if len(data) > 1024 * 1024:
                raise ValueError(f"Oversized page {key}")
            records.append(data)
        offset = 16 + 4 * (len(records) + 1)
        offsets = [offset]
        for data in records:
            offsets.append(offsets[-1] + len(data))
        with path.open("wb") as file:
            file.write(struct.pack("<8sII", b"PW3BIB1\0", len(records), daily_start))
            file.write(struct.pack(f"<{len(offsets)}I", *offsets))
            file.writelines(records)


def link(label, key, anchor=0, grid=False):
    return ("G" if grid else "B", label, key, anchor)


def paragraph(value):
    return ("P", clean(value))


def load_translation(path):
    chapters = defaultdict(dict)
    with ZipFile(path) as archive:
        [member] = [x for x in archive.namelist() if x.endswith("_vpl.txt")]
        with archive.open(member) as lines:
            for raw in lines:
                line = raw.decode("utf-8-sig").strip()
                match = re.match(r"([A-Z0-9]{3}) (\d+):(\d+) (.+)", line)
                if not match:
                    continue
                code, chapter, verse, value = match.groups()
                book = BOOK_IDS.get(VPL_CODE.get(code, code))
                if book and int(verse) > 0:
                    key, verse = (book, int(chapter)), int(verse)
                    if verse in chapters[key]:
                        raise ValueError(f"Duplicate verse {key}:{verse} in {path}")
                    chapters[key][verse] = clean(value)
    if {book for book, _ in chapters} != set(IDS) or len(chapters) != 1189:
        raise ValueError(f"{path} yielded {len(chapters)} chapters and {len({b for b, _ in chapters})} books; expected 1189 and 66")
    return dict(sorted(chapters.items()))


def add_bibles(pages, translations):
    pages.page("bibles", "Bible translations", [
        link(f"{key}  |  {TRANSLATIONS[key]}", ("books", key)) for key in translations
    ])
    for key, chapters in translations.items():
        pages.page(("books", key), f"{key} • Choose a book", [
            link("Book grid", ("grid", key)),
            *[link(BOOKS[b], ("chapter", key, b)) for b in IDS]
        ])
        pages.page(("grid", key), f"{key} • Book grid", [
            link("Book list", ("books", key)),
            *[link(ABBR[b], ("chapter", key, b), grid=True) for b in IDS]
        ])
        for book in IDS:
            pages.page(("chapter", key, book), f"{BOOKS[book]} • Chapters", [
                link("Change book", ("books", key)),
                *[link(ch, ("verses", key, book, ch), grid=True) for b, ch in chapters if b == book]
            ])
        order = list(chapters)
        for i, (book, chapter) in enumerate(order):
            verses = chapters[book, chapter]
            read = ("read", key, book, chapter)
            location = f"{BOOKS[book]} {chapter}"
            pages.page(("verses", key, book, chapter), f"{location} • Choose a verse", [
                link("Read from the start", read),
                *[link(verse, read, verse, grid=True) for verse in verses]
            ])
            rows = [link("Choose book, chapter or verse", ("pick", key, book, chapter)),
                    link("Change translation", ("switch", key, book, chapter))]
            pages.page(("pick", key, book, chapter), f"Go to • {location}", [
                link("Book", ("books", key)), link("Chapter", ("chapter", key, book)),
                link("Verse", ("verses", key, book, chapter)),
                link("Translation", ("switch", key, book, chapter))
            ])
            pages.page(("switch", key, book, chapter), f"Translation • {location}", [
                link(TRANSLATIONS[k], ("read", k, book, chapter)) for k, other in translations.items()
                if (book, chapter) in other
            ])
            for step, label in [(-1, "Previous chapter"), (1, "Next chapter")]:
                if 0 <= i + step < len(order):
                    rows.append(link(label, ("read", key, *order[i + step])))
            rows.extend(("V", n, value) for n, value in verses.items())
            if i + 1 < len(order):
                rows.append(link("Next chapter", ("read", key, *order[i + 1])))
            pages.page(read, f"{location} • {key}", rows)


def reference(raw):
    match = RANGE.fullmatch(raw)
    if not match:
        raise ValueError(f"Invalid reference {raw}")
    book, chapter, verse, end, book2, chapter2, verse2 = [int(x or 0) for x in match.groups()]
    if book not in BOOKS or (book2 and book2 not in BOOKS):
        raise ValueError(f"Unknown book in {raw}")
    label = f"{BOOKS[book]} {chapter}:{verse}"
    if end and end != verse:
        label += f"–{end}"
    if book2:
        label += f" – {BOOKS[book2]} {chapter2}:{verse2}"
    return label, book, chapter, verse, (book2 or book, chapter2 or chapter, verse2 or end or verse)


def reference_link(raw, chapters):
    label, b, c, v, _ = reference(raw)
    if (b, c) not in chapters:
        return paragraph(f"{label} (chapter unavailable in WEB)")
    if v not in chapters[b, c]:
        return link(f"{label} (open chapter)", ("read", "WEB", b, c))
    return link(label, ("read", "WEB", b, c), v)


def read_assets(path):
    with ZipFile(path) as apk, tempfile.TemporaryDirectory() as temp:
        daily = json.loads(apk.read(ASSETS + "tricard-2026.json"))
        plans = json.loads(apk.read(ASSETS + "reading-plan-data.json"))
        db = Path(temp) / "study.sqlite"
        db.write_bytes(apk.read(ASSETS + "bible_data.sqlite"))
        with sqlite3.connect(db.as_uri() + "?mode=ro&immutable=1", uri=True) as sql:
            sql.execute("PRAGMA trusted_schema=OFF")
            topics, questions, refs = {}, {}, defaultdict(list)
            for prefix in ("old_", ""):
                topics.update(sql.execute(f"SELECT touchPointId, touchPoint FROM {prefix}touchPoints"))
                order = "insert_order" if not prefix else "questionId"
                for topic, number, title, body in sql.execute(
                    f"SELECT touchPointId, questionId, question, content FROM {prefix}questions ORDER BY {order}"
                ):
                    questions[topic, number] = (title, body)
            for book, chapter, verse, end, number in sql.execute(
                "SELECT book, chapter, verse, endVerse, questionId FROM refs ORDER BY book, chapter, verse"
            ):
                if book in BOOKS and chapter > 0 and verse > 0:
                    refs[number].append(f"{book}/{chapter}/{verse}" + (f"-{end}" if end and end > verse else ""))
    return daily, plans, topics, questions, refs


def add_topics(pages, topics, questions, refs, chapters):
    by_topic, by_letter = defaultdict(list), defaultdict(list)
    for (topic, number), (title, content) in questions.items():
        parser = StudyText()
        if content:
            body = zlib.decompress(content) if isinstance(content, bytes) else content.encode()
            parser.feed(body.decode("utf-8"))
            parser.close()
        heading = clean(title or topics[topic])
        page = ("q", topic, number)
        paragraphs = [paragraph(line) for line in parser.paragraphs()]
        links = [reference_link(ref, chapters) for ref in dict.fromkeys(refs[number])]
        rows = [link(f"All questions on {topics[topic]}", ("topic", topic)), *paragraphs, *links]
        pages.page(page, heading, rows)
        by_topic[topic].append(link(heading, page))
    for topic, title in sorted(topics.items(), key=lambda item: item[1].casefold()):
        pages.page(("topic", topic), title, by_topic[topic])
        letter = title[0].upper()
        by_letter[letter if "A" <= letter <= "Z" else "#"].append(link(title, ("topic", topic)))
    for letter, rows in by_letter.items():
        pages.page(("letter", letter), f"TouchPoints • {letter}", rows)
    pages.page("topics", "TouchPoints • Browse by topic", [
        link(letter, ("letter", letter), grid=True) for letter in sorted(by_letter)
    ])


def add_daily(pages, daily, topics, questions, chapters):
    if set(daily) != {"votd", "tp", "devo"} or any(len(values) != 365 for values in daily.values()):
        raise ValueError("Expected a complete 2026 three-card calendar")
    for month in range(1, 13):
        label = calendar.month_name[month]
        pages.page(("month", month), f"{label} 2026", [
            link(f"{label} {day}", ("day", (date(2026, month, day) - DATE0).days))
            for day in range(1, calendar.monthrange(2026, month)[1] + 1)
        ])
    pages.page("months", "Life Bible • 2026 calendar", [
        link(calendar.month_name[month], ("month", month), grid=True) for month in range(1, 13)
    ])
    unresolved = []
    for n in range(365):
        current = DATE0 + timedelta(days=n)
        label = f"{calendar.month_name[current.month]} {current.day}, 2026"
        pages.page(("day", n), label, [
            *[link(kind, ("card", n, i)) for i, kind in enumerate(DAY_TYPES)],
            *([link("Previous day", ("day", n - 1))] if n else []),
            *([link("Next day", ("day", n + 1))] if n < 364 else []),
            link("2026 calendar", "months")
        ])
        rows = [link("Other cards for this day", ("day", n))]
        for raw in daily["votd"][n].split(";"):
            display, book, chapter, verse, _ = reference(raw)
            rows.append(reference_link(raw, chapters))
            value = chapters.get((book, chapter), {}).get(verse)
            if value:
                rows.append(paragraph(value))
            else:
                unresolved.append((label, display))
        pages.page(("card", n, 0), f"Daily Verse • {label}", rows)
        topic, question = daily["tp"][n]
        title, _ = questions[topic, question]
        pages.page(("card", n, 1), f"Daily TouchPoint • {label}", [
            link("Other cards for this day", ("day", n)),
            link(topics[topic], ("topic", topic)),
            link(title or "Read this TouchPoint", ("q", topic, question))
        ])
        _, _, title, body = daily["devo"][n]
        pages.page(("card", n, 2), f"Daily Devotional • {label}", [
            link("Other cards for this day", ("day", n)), paragraph(title),
            *[paragraph(p) for p in body.splitlines() if p.strip()]
        ])
    return unresolved


def add_plans(pages, plans, chapters):
    sources = {"chron-tyndale": "Tyndale chronological sequence", "chron-recap": "Bible Recap chronological sequence"}
    pages.page("plans", "Reading Plans", [
        *[link(title, ("plan", key)) for key, title in sources.items()],
        link("Bible in 365 days • local plan", ("plan", "365"))
    ])
    order = list(chapters)
    chapter_index = {chapter: i for i, chapter in enumerate(order)}
    for key, title in sources.items():
        hrefs = plans[key]["hrefs"]
        pages.page(("plan", key), title, [
            paragraph("Passage order from the app. Each selection opens the reading in WEB."),
            *[link(f"Readings {i+1}–{min(i+30, len(hrefs))}", ("plan-group", key, i))
              for i in range(0, len(hrefs), 30)]
        ])
        for i in range(0, len(hrefs), 30):
            pages.page(("plan-group", key, i), f"{title} • {i+1} onward", [
                link(reference(raw)[0], ("plan-reading", key, n))
                for n, raw in enumerate(hrefs[i:i + 30], i)
            ])
        for n, raw in enumerate(hrefs):
            label, book, chapter, first, end = reference(raw)
            start_index = chapter_index[book, chapter]
            stop_index = chapter_index[end[:2]]
            navigation = []
            if n:
                navigation.append(link("Previous reading", ("plan-reading", key, n - 1)))
            if n + 1 < len(hrefs):
                navigation.append(link("Next reading", ("plan-reading", key, n + 1)))
            rows = [reference_link(raw, chapters), *navigation]
            for b, ch in order[start_index:stop_index + 1]:
                if stop_index != start_index:
                    rows.append(paragraph(f"{BOOKS[b]} {ch}"))
                for verse, value in chapters[b, ch].items():
                    if (book, chapter, first) <= (b, ch, verse) <= end:
                        rows.append(paragraph(f"{verse}  {value}"))
            if len(rows) == 1 + len(navigation):
                rows.append(paragraph("No matching verse text in this WEB edition."))
            pages.page(("plan-reading", key, n), f"{label} • Reading {n + 1}", [*rows, *navigation])
    pages.page(("plan", "365"), "Bible in 365 days", [
        paragraph("An offline plan generated in Bible order."),
        *[link(month, ("local-month", i)) for i, month in enumerate(calendar.month_name) if i]
    ])
    for month in range(1, 13):
        month_rows = []
        for day in range(1, calendar.monthrange(2026, month)[1] + 1):
            n = (date(2026, month, day) - DATE0).days
            batch = order[n * len(order) // 365:(n + 1) * len(order) // 365]
            title = f"Day {n+1} • {BOOKS[batch[0][0]]} {batch[0][1]}"
            month_rows.append(link(title, ("plan-day", n)))
            pages.page(("plan-day", n), title, [
                link(f"{BOOKS[book]} {chapter}", ("read", "WEB", book, chapter)) for book, chapter in batch
            ])
        pages.page(("local-month", month), f"Bible in 365 days • {calendar.month_name[month]}", month_rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apk", type=Path, required=True)
    ap.add_argument("--web", type=Path, required=True)
    ap.add_argument("--kjv", type=Path, required=True)
    ap.add_argument("--asv", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    translations = {key: load_translation(getattr(args, key.lower())) for key in TRANSLATIONS}
    daily, plans, topics, questions, refs = read_assets(args.apk)
    web = translations["WEB"]
    expected = {(book, chapter) for book in IDS for chapter in range(1, len(plans[str(book)]))}
    if set(web) != expected:
        raise ValueError("APK chapter lengths do not match the WEB canon")
    pages = Pages()
    pages.reserve("home")
    start = pages.reserve(("day", 0))
    for day in range(365):
        pages.reserve(("day", day))
        for kind in range(3):
            pages.reserve(("card", day, kind))
    [vision] = [i for i, title in topics.items() if title.casefold() == "vision"]
    pages.page("home", "Bible on Paperwhite", [
        link("Bible • Book, chapter, verse", "bibles"),
        link("Daily Verse", "today", 1), link("Daily TouchPoint", "today", 2),
        link("Daily Devotional", "today", 3), link("TouchPoint • Vision", ("topic", vision)),
        link("Reading Plans", "plans"), link("TouchPoints • All topics", "topics"),
        link("Browse the 2026 daily archive", "months")
    ])
    add_bibles(pages, translations)
    add_topics(pages, topics, questions, refs, web)
    unresolved = add_daily(pages, daily, topics, questions, web)
    add_plans(pages, plans, web)
    for key, data in translations.items():
        print(f"{key}: {len(data)} chapters, {sum(map(len, data.values()))} verses")
    print(f"365 daily verses, 365 devotional excerpts, 365 verified daily TouchPoints; {len(topics)} topics, {len(questions)} study entries")
    print(f"Reading plan ranges: {len(plans['chron-tyndale']['hrefs'])} Tyndale, {len(plans['chron-recap']['hrefs'])} Bible Recap")
    print(f"{len(pages.ids)} pages; unresolved WEB daily reference numbers: {unresolved}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pages.write(args.output, start)


if __name__ == "__main__":
    main()
