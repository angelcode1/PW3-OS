# Bible on Paperwhite 3

This is a standalone offline reader for the Paperwhite 3 Alpine project. The source includes the C reader, a font, and a host-side importer. Build the ARMv7 executable and generate the content archive locally. It uses the Paperwhite 3 framebuffer and touch input.

## What's in the reader

| Screen | Content |
| --- | --- |
| Bible | World English Bible (WEB), King James Version (KJV), and American Standard Version (ASV), each with 66 books and 1,189 chapters. Choose a translation, then select a book in list or grid view, a chapter, and a verse. The reading header opens the passage menu. |
| Daily Verse | The APK's 365 date-based 2026 selections, linked to their passages and displayed using WEB text. |
| Daily TouchPoint | All 365 daily topic and question pairs from the 2026 calendar, joined to the APK study database. |
| Daily Devotional | The APK's 365 devotional titles and excerpts for 2026. |
| TouchPoint • Vision | A shortcut to the APK's Vision topic. |
| Reading Plans | The APK's Tyndale and Bible Recap chronological sequences, with 796 and 305 passage ranges respectively. A separately generated Bible-in-365-days plan follows Bible order. |
| TouchPoints | 610 topics and 5,351 study entries from the APK's current and legacy tables, with scripture links where available. |

The daily buttons use the device's local month and day to open the corresponding **2026 archive** entry. In another year they still show the 2026 content, and February 29 opens February 28. The calendar lets you pick any available date.

The three Bible texts are public-domain editions from eBible.org. The APK supplied the selections and study content, while installed or purchased Life Bible translations, full devotional books, account data, online plans, and prior plan progress were outside the supplied APK. The KJV source edition includes the Apocrypha. This package selects the same 66 books as the WEB and ASV data. The study text is formatted as readable paragraphs for e-ink.

## Try the reader on your Mac

Generate `bible.pw3` using the importer below, then open Terminal in `apps/pw3-bible`.

```sh
cc -O2 -Wall -Wextra -DPW3_HOST reader.c -o reader-host
./reader-host bible.pw3 --verify
./reader-host bible.pw3 --date 11-06
```

Enter the number beside a link. Use `b` to go back, `h` for Home, and `q` to quit. Omit `--date 11-06` to use the local calendar.

## Launch on Alpine after boot validation

The current PW3 Alpine staging image is under its boot hold. The reader is a separate bundle. Once the image is validated, put the app folder with the locally built executable and content archive on an executable filesystem accessible from inside Alpine, for example `/opt/pw3-bible`. Run this in the Alpine environment where the reader has access to the PW3 framebuffer and touch devices:

```sh
cd /opt/pw3-bible
chmod +x pw3-bible-arm
sh run-kindle.sh
```

Tap a button to navigate. Swipe left or right or tap Previous and Next to turn a screen. Tap the heading on a Bible passage to reopen its navigation menu. Exit returns to the process that launched the reader. A launcher entry can invoke `/opt/pw3-bible/run-kindle.sh` after the direct launch is tested.

## Rebuild from the source APK

To generate `bible.pw3`, Python 3.8 or newer takes the APK and the eBible VPL archives:

```sh
curl -fL https://ebible.org/Scriptures/engwebp_vpl.zip -o web.zip
curl -fL https://ebible.org/Scriptures/eng-kjv_vpl.zip -o kjv.zip
curl -fL https://ebible.org/Scriptures/eng-asv_vpl.zip -o asv.zip

python3 build.py --apk '/path/to/Life Bible v10.2.665.apk' \
  --web web.zip --kjv kjv.zip --asv asv.zip --output bible.pw3
./reader-host bible.pw3 --verify
```

Rebuild the Kindle executable with Zig 0.14.1:

```sh
zig cc -target arm-linux.3.0.35-musleabi -mcpu=cortex_a9 -O2 -static \
  -Wall -Wextra -Wno-unused-function -Wno-unused-variable \
  reader.c -lm -o pw3-bible-arm
```

## Sources and validation

- The Life Bible 2026 calendar, study database, and reading-plan indexes came from the supplied Life Bible v10.2.665 APK.
- Bible sources are [WEB](https://ebible.org/details.php?id=engwebp), [KJV](https://www.ebible.org/find/details.php?id=eng-kjv), and [ASV](https://www.ebible.org/find/details.php?id=eng-asv).
- The e-ink and touch layer is based on [Inkwell](https://github.com/pragyaangaur/Inkwell/tree/d1fc9d9ef911777fb5db14541fd5b841fd7c1f03), with a bundled-font path and an explicit 16-byte Linux 3.0 evdev record. The font is Inter. Third-party notices are included.
- Host verification covered archive parsing, daily calendar routing, Bible navigation and verse jumps, Vision, and reading-plan ranges. The ARM executable was inspected for its architecture, soft-float ABI, and static linking. Actual Kindle framebuffer, touch and launcher behavior remain to be verified on the device.

## Import locally downloaded Jesus Calling readings

Build the archive with the same APK and Bible archives as above, adding
`--jesus-calling-dir "$HOME/Downloads/lifebible-samples"` to the `build.py` command.
That folder must contain `1306.sqlite` and `1306/data/Devos/`. The importer
requires all 261 numbered readings, follows the explicit database links, and
extracts display text from the local HTML. It adds the numbered readings and
Scripture anchors to the archive. Keep the downloaded files and generated archive
local.

In the Mac preview, open **Library → Devotional Bibles → Jesus Calling Devotional Bible**. Compare Days 1
and 261 with Life Bible offline, open Day 1's Genesis 1:1 link, and press `b` to
return to the reading.

## Library categories

The Library lists Bible Translations, Commentaries, Study Bibles, Devotional
Bibles, The One Year Devotions, and Once-A-Day Devotionals in Life Bible's order.
Categories with no imported titles say so. Audio Bibles requires a verified
playback path on PW3 Alpine. The One
Year Devotions includes The One Year Bible's 365-day Scripture schedule from the
APK, with passage links into WEB. The other reading plans remain on Home.

Rebuild the archive to update the menus. The existing reader executable can
open the rebuilt archive.
