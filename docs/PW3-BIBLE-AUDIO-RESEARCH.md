# PW3 Bible audio URL research — KJV, CSB, Breathe (6 Nov 2026)

**Status: research only.** Does **not** enable audio playback, decrypt traffic,
copy protected media, or change the Kindle runtime. The existing PW3 boot hold,
reader archive format, and audio-playback verification requirement remain intact.

## Sources and provenance

- User-provided Life Bible v10.2.665 APK: static product catalog IDs
  KJVAUD=8009, CSBAUD=8231, BNLT=8026 (Breathe is New Testament only).
- User-provided Tecarta Bible v8.0.2 APK, JADX excerpt evidence:
  AppSingleton.getVolumeID, AppSingleton.getAudioFileFromServer,
  Audio.getAudioFileHash, DownloadAudioTask, AudioBook.
- User-captured PCAPdroid exports: KJV had plain HTTP MP3 transfers from
  Faith Comes By Hearing; CSB and Breathe delivered encrypted HTTPS through
  cf-audio.tecartabible.com and did not expose audio URL paths.
- Existing apps/pw3-bible/build.py: authoritative *non-consecutive*
  Tecarta book ID mapping for the canonical 66 books.

None of the APKs, packet captures, proprietary media or decompiled code
are included in this repository change.

## Decompiled v8 URL construction

1. getVolumeID(x): subtract 300 for 301..399 and 8301..8399, otherwise
   unchanged. This leaves v10 catalog IDs 8009, 8231 and 8026 unchanged;
   **that does not verify them as v8 server IDs**.
2. Audio.getAudioFileHash(reference, vol, true): SHA-256 of UTF-8
   {resolved_volume}_{tecarta_book_id}_{chapter}_0, Android URL-safe Base64
   (= padding retained). An ordinary chapter path may be
   https://cf-audio.tecartabible.com/{vol}/chapters/{hash}.
3. AppSingleton.getAudioFileFromServer requests
   https://cf-audio.tecartabible.com/{vol}/audio-links/{book_id}_{chapter}.json
   and retrieves its JSON "path" value. The v8 dynamic mode
   (dynamicAudio == 2) passes this URL to the download service.
4. **Special cases exist:** v8 AUDIO_SELECTION == 2 and certain
   audioVolumeId == 8000 branches use voice-specific chapter paths.
   The included code does **not** model these.

No assumption that CSB or Breathe is dynamic is warranted merely because
their network traffic is HTTPS. An HTTP status or catalog listing does not
establish legal access to downloadable audio.

## Corrected book numbering

An earlier experimental CSV generator incorrectly assumed the Old Testament
book IDs were consecutive. The actual canonical 66-book map skips
17, 18, 20, 21, 27, 28, 32 and ends at 73:

| Book | Tecarta book ID |
|---|---:|
| Esther | 19 |
| Psalms | 23 |
| Malachi | 46 |
| Matthew | 47 |
| Acts | 51 |
| James | 66 |
| Jude | 72 |
| Revelation | 73 |

**Do not use the earlier csb_breathe_v8_candidate_paths.csv**: its Old
Testament entries are incorrect. The new generator uses the validated map
and is regression-tested against the project's build.py.

## Offline usage — no root

From the repository root:

```sh
python3 apps/pw3-bible/audio_catalog_cli.py --edition csb --book Acts --chapter 1
python3 apps/pw3-bible/audio_catalog_cli.py --edition breathe --book Acts --chapter 1
python3 apps/pw3-bible/audio_catalog_cli.py --edition csb --csv /tmp/csb-unverified.csv
python3 -m unittest discover -s tests -p 'test_pw3_audio_catalog.py' -v
```

Every CSV candidate is marked **unverified**. There are 2,378 CSB
candidate paths (1,189 chapters x two modes) and 520 Breathe New Testament
candidate paths (260 chapters x two modes), **not** 2,898 proven links.
The default operations perform no network requests.

For a single chapter you are legitimately authorised to access, an explicit
opt-in can check **one** metadata URL:

```sh
python3 apps/pw3-bible/audio_catalog_cli.py \
  --edition csb --book Acts --chapter 1 --scheme dynamic --probe --authorized
```

The opt-in issues one read-only metadata GET (or a HEAD for a static
candidate), follows no redirects, downloads no audio and suppresses resolved
paths and token values. Treat 401/403 as a boundary rather than attempting
to bypass authorisation; 404 may indicate an incorrect ID or mode.

## Remaining gaps before PW3 playback integration

- Validate actual v10 audio mode and server-volume IDs.
- Confirm authorised access, link expiry and signed URL handling.
- Verify stream codecs and an audio output stack on PW3 Alpine.
- Define licensed caching/storage policy; do not bundle recordings.
- Verify speaker, e-ink UI and launcher behaviour on physical PW3 hardware.

**No Kindle player or UI changes should be made based on guessed URLs.**
