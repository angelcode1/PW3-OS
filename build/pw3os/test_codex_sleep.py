"""Regression checks for the shared PW3 Codex sleep-screen branding."""
import unittest
from pathlib import Path
from codex_sleep import (
    patch_codex_sleep, OLD_TITLE, NEW_TITLE, OLD_HINT, NEW_HINT
)

HERE = Path(__file__).resolve().parent


class TestCodexSleep(unittest.TestCase):
    def setUp(self):
        self.source = (
            '#include "eink.h"\n'
            'static void draw_night(void) {\n'
            '    ' + OLD_TITLE + '\n'
            '    ' + OLD_HINT + '\n'
            '}\n'
            'static void sleep_now(void) {\n'
            '    draw_night();\n'
            '    refresh_all();\n'
            '    fputs("mem\\n", fopen("/sys/power/state", "w"));\n'
            '    unsnap(&page);\n'
            '    refresh_all();\n'
            '}\n'
            '__attribute__((constructor)) static void sleep_install(void) { idle_hook = sleep_now; }\n'
        )

    def test_only_the_two_text_strings_change(self):
        result = patch_codex_sleep(self.source)
        self.assertIn('Codex is closed', result)
        self.assertIn("press power to turn the page", result)
        self.assertNotIn('Inkwell is asleep', result)
        self.assertNotIn('press the power button to wake', result)
        self.assertEqual(result.replace(NEW_TITLE, OLD_TITLE)
                               .replace(NEW_HINT, OLD_HINT), self.source)
        self.assertIn('fputs("mem\\n"', result)
        self.assertIn('unsnap(&page)', result)
        self.assertIn('refresh_all()', result)

    def test_fails_closed_for_modified_or_duplicated_upstream(self):
        for invalid in (
            self.source.replace('Inkwell is asleep', 'changed upstream'),
            self.source.replace('press the power button to wake', 'updated'),
            self.source + OLD_TITLE,
            self.source + OLD_HINT,
            ''
        ):
            with self.subTest(invalid=invalid[:40]):
                with self.assertRaises(ValueError):
                    patch_codex_sleep(invalid)

    def test_builder_patches_same_source_directory_not_boot_hook(self):
        builder = (HERE/'build_image.py').read_text()
        self.assertIn("sleep_header=upstream/'src/ui/sleep.h'", builder)
        self.assertIn('patch_codex_sleep(sleep_header.read_text())', builder)
        self.assertLess(builder.index('patch_codex_sleep(sleep_header.read_text())'),
                        builder.index("apps=('home','wifi','settings','term','splash')"))
        self.assertNotIn("codex_sleep.py", (HERE/'pw3-init.sh').read_text())
        self.assertNotIn("codex_sleep.py", (HERE/'pw3os-boot-once.sh').read_text())


if __name__ == '__main__':
    unittest.main()
