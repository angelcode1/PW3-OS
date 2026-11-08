# Optional Bluetooth Audio — PW3 Bible Reader

**Implementation stage: host-integrated, hardware unverified.** The existing
Paperwhite 3 boot hold remains in effect. This is an optional user-space audio
controller; it does not start Bluetooth, install packages or change the kernel.

## Availability and interface

The native reader checks \`python3 ./audio_control.py ready\` when it launches.
The helper returns success only when all of the following exist:

- An enumerated Linux Bluetooth controller under \`/sys/class/bluetooth/hci*\`.
- An actual \`bluez_output.*\` sink reported by \`pactl list short sinks\`.
- An installed \`mpv\` executable.

On a chapter **reading** page, and only when the check succeeds, a framed
**Audio: KJV Drama ▼** selector and **Play/Pause** appear above the passage.
The dropdown exposes **KJV Drama, CSB** in the Old Testament and **KJV Drama,
CSB, Breathe NLT** in the New Testament. The 66-book mapping comes from
\`build.py\`, with the established gaps in Tecarta's numeric IDs.

The UI is a native e-ink popup, not an HTML dropdown. Changing chapter,
leaving a reading page, changing recording or exiting terminates playback.
Play starts \`mpv\`; Pause/Resume uses mpv's Unix-domain JSON IPC with a private
0700 runtime directory. The output is forced to the enumerated Bluetooth
PulseAudio-compatible sink; there is **no speaker fallback**. A failure leaves
the player stopped and displays “Audio unavailable.” New Bluetooth
connections require restarting the reader to re-run the visibility check.

This does **not** claim the Paperwhite 3 has onboard Bluetooth. The 2015
device predates modern Kindle built-in Bluetooth. A supported external radio,
kernel drivers, BlueZ, PulseAudio-compatible Bluetooth routing and media
decoder may be necessary. These components have **not** been tested on PW3
Alpine, nor has actual Kindle hardware playback been demonstrated.

## Media manifest (no copyrighted recordings shipped)

The controller **does not construct live URLs from guessed Tecarta IDs** and
does not call Tecarta's server, download libraries, defeat access controls or
interpret signed-link metadata. It plays only chapter sources explicitly
configured in \`audio-links.tsv\`, expected alongside the executable:

```text
kjv<TAB>51<TAB>1<TAB>https://example.org/authorised/acts-1.mp3
csb<TAB>51<TAB>1<TAB>./audio/authorised-csb-acts-1.mp3
breathe<TAB>51<TAB>1<TAB>./audio/authorised-breathe-acts-1.mp3
```

Use actual tab characters, not literal \`<TAB>\`. Relative files must live
under \`./audio/\`; HTTPS or HTTP URLs must be plain media URLs (never mpv
pseudo-protocols). Prefer HTTPS when possible. Do not commit secrets, expiring
signed links or redistributed licensed media.

An opt-in \`audio-links.example.tsv\` lists four KJV sample chapter links
observed in PCAPdroid; they are not tested in CI and are not presumed licensed
for redistribution. To enable **only** those sample links after independent
authorisation/availability verification:

```sh
cd /opt/pw3-bible
cp audio-links.example.tsv audio-links.tsv
python3 audio_control.py ready
# Exit 0 means a connected Bluetooth sink and player were found.
python3 audio_control.py play kjv 51 1
python3 audio_control.py pause
python3 audio_control.py resume
python3 audio_control.py stop
```

**CSB and Breathe remain source-unverified.** They are selectable to match
the requested UI, but Play fails closed unless a licensed playable media
source has been configured for that chapter.

## Build and dependency boundaries

The reader \`build.py\` now adds one \`A\tbook_id\tchapter\` metadata row to
each Bible reading page in the \`bible.pw3\` archive. The new binary accepts
older archives, but archives containing \`A\` rows require the updated binary.
**Rebuild the reader binary and archive together** before an on-device trial.
Other reader pages contain no audio metadata and never show these controls.

Host verification:

```sh
cc -O2 -Wall -Wextra -DPW3_HOST apps/pw3-bible/reader.c -o /tmp/pw3-reader-host
python3 -m unittest discover -s tests -p 'test_pw3_audio_player.py' -v
python3 -m unittest discover -s tests -p 'test_pw3_audio_archive.py' -v
```

Additional required on-device packages/services *if compatible with the
staged PW3 Alpine userspace*: Python 3, BlueZ, PulseAudio/PipeWire Pulse
compatibility, \`pactl\`, an A2DP output module, and mpv with Pulse output and
the needed media codecs. Installation should not be attempted while the PW3
Alpine boot hold is active.

**Known gaps:** no actual Bluetooth adapter/output proof on PW3; no entitlement
or stable chapter URLs established for CSB/Breathe; no automatic next-chapter
playback; no synchronised verse highlighting; no audio UI in the host terminal
preview; no bundled recordings; audio connection is rechecked on launch,
not continuously. This is a gated integration, not a device-certified feature.

## Streaming-only update (8 November 2026)

Audio recordings are **not** bundled with the Kindle image, stored as files,
or committed to GitHub. The player invokes `audio_stream.py` at Play time for
KJV Drama (8009), CSB (8231), and Breathe NLT (8026). Breathe remains a
selectable **New Testament** source. It first checks the source-derived v8
`audio-links/{book}_{chapter}.json` metadata URL, then checks a hashed
chapter candidate using HEAD if necessary. Playback starts only after a
recognized stream is returned. No media bytes are fetched by the resolver.
The host player uses mpv with `--cache=no`; decoding will naturally buffer
small amounts in RAM. This is not a promise of zero in-memory buffering.

A user-provided `audio-links.tsv` can still override one chapter with a
**stream URL only**, not a local file. Existing `./audio/...` entries are
rejected. None of the candidates are evidence of entitlement, and the server
may reject an edition or chapter. Breathe is **enabled in the UI**, but actual
8026 playback has not been confirmed by live test. The code does not silently
substitute another edition or make a local recording copy.

**Important:** PW3 device Bluetooth and mpv output remain unverified and the
existing hardware boot hold has not been lifted. Test on an appropriate host
or after the separately approved hardware preflight.

Host checks: `python3 -m unittest discover -s tests -p 'test_pw3_audio_stream.py' -v`.
