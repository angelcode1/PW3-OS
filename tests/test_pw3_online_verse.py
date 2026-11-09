"""No-network regression tests for the public-only Bible chapter viewer."""
from io import BytesIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

APP = Path(__file__).resolve().parents[1] / "apps" / "pw3-bible"
sys.path.insert(0, str(APP))
import online_verse


class Response:
    status = 200

    def __init__(self, value, mime="application/json"):
        self.stream = BytesIO(value)
        self.headers = {"Content-Type": mime}

    def read(self, size=-1):
        return self.stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


class Open:
    def __init__(self, value):
        self.value = value
        self.request = None
        self.timeout = None

    def open(self, request, timeout):
        self.request, self.timeout = request, timeout
        return Response(self.value)


class OnlineVerseTests(unittest.TestCase):
    def test_public_url_uses_tecarta_ids_without_hash_or_signed_host(self):
        url = online_verse.url_for(9, 53, 8, {9})
        self.assertEqual(url, "https://cf-stream.tecartabible.com/8/9/chapters/53_8.json")
        self.assertNotIn("cf-signed", url)
        for volume, book, chapter in ((51, 53, 9), (9, 17, 1), (9, 73, 151)):
            with self.assertRaises(ValueError):
                online_verse.url_for(volume, book, chapter, {9})

    def test_fetch_one_chapter_in_memory(self):
        opener = Open(b'{"chapter":"<p>text</p>","verses":{"2":"Second","1":"First &amp; only"},"footnotes":{},"xrefs":{}}')
        entries = online_verse.fetch_verses(9, 53, 8, {9}, opener)
        self.assertEqual(entries, [(1, "First & only"), (2, "Second")])
        self.assertEqual(opener.timeout, 8)
        self.assertEqual(opener.request.get_header("Accept-encoding"), "identity")
        self.assertEqual(opener.request.full_url, "https://cf-stream.tecartabible.com/8/9/chapters/53_8.json")

    def test_rejects_resource_arrays_or_incomplete_json(self):
        for value in (b"[]", b'{"chapters":[]}', b'{"verses":{}}', b'{"verses":{"1":false}}', b'{"verses":{"200":"bad"}}'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                online_verse.fetch_verses(9, 1, 1, {9}, Open(value))

    def test_redirects_are_never_followed(self):
        self.assertIsNone(online_verse.NoRedirect().redirect_request(
            None, None, 302, "redirect", {}, "https://cf-signed.tecartabible.com/8/test"))

    def test_catalogue_allowlist_and_no_disk_storage(self):
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / "catalog.tsv"
            file.write_text("# test\n9\tKJV\tKing James Version\n51\tNLT\tNew Living Translation\n")
            self.assertEqual(online_verse.volumes(file), {9, 51})
            self.assertEqual(sorted(p.name for p in Path(td).iterdir()), ["catalog.tsv"])

    def test_main_emits_only_verses_with_mocked_response(self):
        from contextlib import redirect_stdout
        import io
        output = io.StringIO()
        with patch.object(online_verse, "volumes", return_value={9}), \
             patch.object(online_verse, "build_opener", return_value=Open(b'{"verses":{"1":"Hello World"}}')), \
             redirect_stdout(output):
            self.assertEqual(online_verse.main(["9", "1", "1"]), 0)
        self.assertEqual(output.getvalue(), "V\t1\tHello World\n")


if __name__ == "__main__":
    unittest.main()
