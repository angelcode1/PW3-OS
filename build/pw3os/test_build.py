import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
BUILD=ROOT/'build/pw3os'
class TestBuild(unittest.TestCase):
    def test_sources_present(self):
        for name in ('build_image.py','puzzles.c','public_bible.py','pw3-init.sh',
                     'pw3os-boot-once.sh','pw3_debugmount.c','README-DEPLOY.txt'):
            self.assertTrue((BUILD/name).is_file(),name)
    def test_games_are_ours_not_inkwell(self):
        s=(BUILD/'build_image.py').read_text()
        self.assertIn("'pw3-puzzles'",s)
        self.assertNotIn("'chess','doom'",s)
        for banned in ('build-doom.sh','build-llm.sh','build-ui.sh'):
            self.assertNotIn("run('sh',upstream/'"+banned,s)
    def test_uses_actual_feature_bible(self):
        s=(BUILD/'build_image.py').read_text()
        self.assertIn("apps/pw3-bible",s)
        self.assertIn('public_bible.py',s)
        self.assertIn('3.24.3',s)
    def test_startup_not_bounded_to_three_minutes(self):
        s=(BUILD/'build_image.py').read_text()
        self.assertIn('"$BB" chroot "$R" /sbin/own-init',s)
        self.assertIn("timeout -t 330",s) # match removal before final script output
        self.assertIn('One-shot', (BUILD/'README.md').read_text().replace('one-shot','One-shot'))
    def test_hash(self):
        spec=importlib.util.spec_from_file_location('b',BUILD/'build_image.py')
        b=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(b)
        self.assertEqual(len(b.KOREADER_SHA),64)
        self.assertEqual(b.INKWELL_REF,'d1fc9d9ef911777fb5db14541fd5b841fd7c1f03')

if __name__=='__main__':unittest.main()
