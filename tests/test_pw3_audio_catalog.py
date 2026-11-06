"""Offline regression tests for the Tecarta v8 research-only resolver."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import csv

APP = Path(__file__).resolve().parents[1] / "apps" / "pw3-bible"
sys.path.insert(0, str(APP))
import audio_catalog as audio  # noqa: E402


class TecartaAudioTests(unittest.TestCase):
    def test_matches_reader_book_ids_exactly(self):
        # Prevent the earlier incorrect sequential 1..39 OT mapping from recurring.
        spec = importlib.util.spec_from_file_location("pw3_bible_build", APP / "build.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        self.assertEqual(list(audio.BOOK_IDS), build.IDS)
        self.assertEqual(list(audio.NAMES), build.NAMES)
        self.assertEqual(audio.book_id_for("Esther"), 19)
        self.assertEqual(audio.book_id_for("Psalms"), 23)
        self.assertEqual(audio.book_id_for("Matthew"), 47)
        self.assertEqual(audio.book_id_for("Acts"), 51)
        self.assertEqual(audio.book_id_for("Jude"), 72)
        self.assertEqual(audio.book_id_for("Revelation"), 73)

    def test_volume_id_conversion_boundaries(self):
        for value, expected in [(300, 300), (301, 1), (399, 99),
                                (400, 400), (8009, 8009), (8026, 8026),
                                (8231, 8231), (8300, 8300), (8301, 8001),
                                (8399, 8099), (8400, 8400)]:
            self.assertEqual(audio.volume_id(value), expected)

    def test_static_hash_and_dynamic_path(self):
        token = "ZB8_p6753oHUPcohVTAqWEeSq4Ho-VCY5a-UvYTlM_w="
        self.assertEqual(audio.audio_url(8231, 51, 1, "static"),
                         f"{audio.BASE}/8231/chapters/{token}")
        self.assertEqual(audio.audio_url(8231, 51, 1, "dynamic"),
                         f"{audio.BASE}/8231/audio-links/51_1.json")
        self.assertEqual(len(token), 44)

    def test_candidate_counts_and_breathe_testament(self):
        self.assertEqual(len(list(audio.candidates("kjv"))), 2378)
        self.assertEqual(len(list(audio.candidates("csb"))), 2378)
        breathe = list(audio.candidates("breathe"))
        self.assertEqual(len(breathe), 520)
        self.assertEqual(breathe[0].book, "Matthew")
        self.assertEqual(breathe[-1].book, "Revelation")
        self.assertTrue(all(item.book_id >= 47 for item in breathe))

    def test_rejects_sparse_gaps_and_incorrect_chapters(self):
        for bad in (17, 18, 20, 21, 27, 28, 32):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                audio.book_id_for(bad)
        for book, ch in [(audio.book_id_for("Psalms"), 151), (51, 29), (72, 2), (47, 0)]:
            with self.subTest(book=book, chapter=ch), self.assertRaises(ValueError):
                audio.audio_url(8231, book, ch, "dynamic")

    def test_cli_csv_is_offline_and_correct(self):
        cli = str(APP / "audio_catalog_cli.py")
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "candidates.csv"
            run = subprocess.run([sys.executable, cli, "--edition", "breathe", "--csv", str(dst)],
                                 check=True, capture_output=True, text=True)
            self.assertIn("offline", run.stdout)
            with dst.open(newline="", encoding="utf-8") as fp:
                rows = list(csv.DictReader(fp))
            self.assertEqual(len(rows), 520)
            self.assertEqual(rows[0]["tecarta_book_id"], "47")
            self.assertTrue(all(row["verification"].startswith("UNVERIFIED") for row in rows))
            bad = subprocess.run([sys.executable, cli, "--edition", "csb", "--book", "Acts",
                                  "--chapter", "1", "--probe", "--scheme", "dynamic"],
                                 capture_output=True)
            self.assertNotEqual(bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()
