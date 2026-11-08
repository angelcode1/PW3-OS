"""Host tests: no recorded audio is fetched or stored."""
import importlib.util
from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "apps" / "pw3-bible"
sys.path.insert(0, str(APP))
import audio_stream as stream


class Response:
    status = 200
    def __init__(self, data, mime="application/json"):
        self.io = BytesIO(data)
        self.headers = {"Content-Type": mime}
    def read(self, n=-1):
        return self.io.read(n)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class Opener:
    def __init__(self, metadata, media_mime="audio/mpeg"):
        self.requests = []
        self.metadata = metadata
        self.media_mime = media_mime
    def open(self, req, timeout):
        self.requests.append((req.get_method(), req.full_url))
        if req.get_method() == "HEAD":
            return Response(b"", self.media_mime)
        return Response(self.metadata)


class StreamTests(unittest.TestCase):
    def test_all_three_editions_have_candidate_urls(self):
        self.assertIn("/8009/audio-links/51_1.json", stream.candidate_urls("kjv", 51, 1)[0])
        self.assertIn("/8231/audio-links/51_1.json", stream.candidate_urls("csb", 51, 1)[0])
        self.assertIn("/8026/audio-links/51_1.json", stream.candidate_urls("breathe", 51, 1)[0])
        with self.assertRaises(ValueError):
            stream.candidate_urls("breathe", 1, 1)

    def test_dynamic_metadata_returns_stream_only(self):
        url = "http://cloud.faithcomesbyhearing.com/path/chapter.mp3"
        opener = Opener(json_bytes(url))
        self.assertEqual(stream.resolve_stream("kjv", 51, 1, opener), url)
        self.assertEqual(len(opener.requests), 1)
        self.assertEqual(opener.requests[0][0], "GET")

    def test_other_host_cannot_be_injected_by_remote_metadata(self):
        opener = Opener(json_bytes("https://evil.example.org/audio"))
        url = stream.resolve_stream("csb", 51, 1, opener)
        self.assertEqual(url, stream.candidate_urls("csb", 51, 1)[1])
        self.assertEqual([method for method, _ in opener.requests], ["GET", "HEAD"])

    def test_breathe_nt_remains_enabled(self):
        opener = Opener(b'{"path":"https://cf-audio.tecartabible.com/8026/audio.mp3"}')
        self.assertEqual(stream.resolve_stream("breathe", 47, 1, opener),
                         "https://cf-audio.tecartabible.com/8026/audio.mp3")

    def test_missing_media_fails_closed(self):
        opener = Opener(b"{}", "application/json")
        self.assertIsNone(stream.resolve_stream("breathe", 47, 1, opener))
        self.assertEqual([m for m, _ in opener.requests], ["GET", "HEAD"])

    def test_invalid_paths_are_rejected(self):
        for path in ("file:///tmp/audio.mp3", "http://127.0.0.1/x", "https://evil.example.org/x",
                     "https://user:password@cloud.faithcomesbyhearing.com/x"):
            self.assertFalse(stream.accepted_dynamic_media(path))


def json_bytes(url):
    import json
    return json.dumps({"path": url}).encode("utf-8")


if __name__ == "__main__":
    unittest.main()
