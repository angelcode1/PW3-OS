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
    def test_public_archive_header_is_valid_for_reader(self):
        self.assertIn('pages.write(output, 1)',(BUILD/'public_bible.py').read_text())
        self.assertIn("verify_bible_archive(app,work,dest/'bible.pw3')",(BUILD/'build_image.py').read_text())
    def test_pts_mount_and_cleanup_both_present(self):
        s=(BUILD/'pw3os-boot-once.sh').read_text()
        helper=(BUILD/'pw3_debugmount.c').read_text()
        self.assertIn('B_PTS=1',s)
        self.assertIn('umount "$R/dev/pts"',s)
        self.assertIn('bind /dev/pts "$R/dev/pts"',s)
        self.assertIn('same(source,"/dev/pts")',helper)
    def test_requested_home_menu_and_games_chooser(self):
        s=(BUILD/'build_image.py').read_text()
        self.assertIn("'home_menu':['Bible','KOReader','Games','Wi-Fi','Settings']",s)
        self.assertIn('Games|cube|/usr/local/bin/pw3-games',s)
        self.assertNotIn('Notes|page|/usr/local/bin/notes',s)
        self.assertNotIn('Terminal|terminal|/usr/local/bin/term',s)
        self.assertIn("'settings_submenu':['Terminal'",s)
        self.assertNotIn('Memory Match|cube|/usr/local/bin/pw3-puzzles match',s)
        self.assertIn("games-menu.c",s)
        self.assertIn("exec ./luajit ./reader.lua",s)
    def test_cleanup_keeps_current_image(self):
        s=(BUILD/'REMOVE-LEGACY-IMAGES.sh').read_text()
        self.assertIn('--remove-legacy-after-stock',s)
        self.assertIn('ACTIVE_RUNNER_NOT_POINTING_TO_ALPINE_OS',s)
        self.assertIn('RESULT: LEGACY_ALPINE_IMAGES_REMOVED_CURRENT_ALPINE_OS_PRESERVED',s)
        self.assertNotIn('rm "$D/alpine-os.img"',s)
    def test_terminal_is_inside_settings(self):
        import sys
        sys.path.insert(0, str(BUILD))
        from settings_integration import patch_settings
        src = '''#include "ui.h"
static rect restart_btn, off_btn, kindle_btn;
int bw = (W - 2 * MARGIN - 40) / 2;
off_btn = (rect){MARGIN + bw + 40, 210, bw, 110};
pill(off_btn, "Power off", 0);
else if (hit(off_btn, e.x, e.y)) press_on(off_btn);
if (hit(off_btn, e.x, e.y)) return 12;
int main(void) {
Inkwell on Alpine %s
'''
        adjusted = patch_settings(src)
        for phrase in ('terminal_btn', 'launch_terminal()', 'execl("/usr/local/bin/term"',
                       'input_drain();', 'PW3-OS on Alpine %s'):
            self.assertIn(phrase, adjusted)
        self.assertRaises(ValueError, patch_settings, 'broken upstream')
    def test_hash(self):
        spec=importlib.util.spec_from_file_location('b',BUILD/'build_image.py')
        b=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(b)
        self.assertEqual(len(b.KOREADER_SHA),64)
        self.assertEqual(b.INKWELL_REF,'d1fc9d9ef911777fb5db14541fd5b841fd7c1f03')

if __name__=='__main__':unittest.main()
