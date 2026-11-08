"""Host regression checks for the opt-in Bluetooth-only audio controller."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "apps" / "pw3-bible"
sys.path.insert(0, str(APP))
spec = importlib.util.spec_from_file_location("audio_control", APP / "audio_control.py")
audio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio)


class AudioPlayerTests(unittest.TestCase):
    def test_fail_closed_without_adapter(self):
        with patch.object(audio.os, "listdir", side_effect=FileNotFoundError()):
            self.assertIsNone(audio.sink())
            self.assertFalse(audio.ready())

    def test_only_bluez_sink_is_selected(self):
        class Completed:
            returncode = 0
            stdout = ("0\talsa_output.pci-0000\tmodule-alsa\n"
                      "1\tbluez_output.AA_BB_CC.a2dp_sink\tmodule-bluez\n")
        with patch.object(audio.os, "listdir", return_value=["hci0"]):
            with patch.object(audio.subprocess, "run", return_value=Completed()):
                self.assertEqual(audio.sink(), "bluez_output.AA_BB_CC.a2dp_sink")

    def test_media_manifest_whitelist_and_breathe_ot_hold(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "audio.tsv"
            path.write_text("csb\t51\t1\tedl://bad\n"
                            "kjv\t51\t1\thttps://media.example.org/audio.mp3\n"
                            "breathe\t1\t1\thttps://media.example.org/ot.mp3\n")
            with patch.object(audio, "MANIFEST", path):
                self.assertIsNone(audio.find_audio("csb", 51, 1))
                self.assertEqual(audio.find_audio("kjv", 51, 1),
                                 "https://media.example.org/audio.mp3")
                self.assertIsNone(audio.find_audio("breathe", 1, 1))
                self.assertIsNone(audio.find_audio("csb", 51, 2))

    def test_no_manifest_resolves_stream_on_demand(self):
        with patch.object(audio, "MANIFEST", Path("/definitely/not/pw3-audio-links.tsv")):
            with patch.object(audio, "resolve_stream", return_value="https://cf-audio.tecartabible.com/8009/test") as resolve:
                self.assertEqual(audio.find_audio("kjv", 51, 1), "https://cf-audio.tecartabible.com/8009/test")
                resolve.assert_called_once_with("kjv", 51, 1)

    def test_local_audio_files_are_not_accepted(self):
        self.assertFalse(audio.approved_media("./audio/chapter.mp3"))

    def test_breathe_nt_stream_fallback(self):
        with patch.object(audio, "MANIFEST", Path("/definitely/not/pw3-audio-links.tsv")):
            with patch.object(audio, "resolve_stream", return_value="https://cf-audio.tecartabible.com/8026/test") as resolve:
                self.assertIsNotNone(audio.find_audio("breathe", 47, 1))
                resolve.assert_called_once_with("breathe", 47, 1)
                self.assertIsNone(audio.find_audio("breathe", 1, 1))

    def test_rejects_non_bluetooth_output_and_missing_player(self):
        class Completed:
            returncode = 0
            stdout = "0\talsa_output.pci-0000\tmodule-alsa\n"
        with patch.object(audio.os, "listdir", return_value=["hci0"]):
            with patch.object(audio.subprocess, "run", return_value=Completed()):
                self.assertFalse(audio.ready())


if __name__ == "__main__":
    unittest.main()
