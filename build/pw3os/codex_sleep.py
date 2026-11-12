"""Scoped branding of the pinned Inkwell sleep screen for Codex.

The shared sleep.h is included from upstream ui.h, so patch that checkout's
header before compiling any app; -I overrides cannot replace quoted includes
from ui.h's own directory. Preserve power/suspend/wake/refresh behaviour.
"""

OLD_TITLE = 'text_center(&f_serif_italic, 78, W / 2, H - 250, "Inkwell is asleep", 0xF0);'
NEW_TITLE = 'text_center(&f_serif_italic, 78, W / 2, H - 250, "Codex is closed", 0xF0);'
OLD_HINT = 'text_center(&f_ui, 32, W / 2, H - 140, "press the power button to wake", 0xB0);'
NEW_HINT = 'text_center(&f_ui, 32, W / 2, H - 140, "press power to turn the page", 0xB0);'


def patch_codex_sleep(source: str) -> str:
    """Fail closed if the pinned upstream sleep artwork/text has changed."""
    if source.count(OLD_TITLE) != 1 or source.count(OLD_HINT) != 1:
        raise ValueError("Pinned Inkwell sleep screen text anchors changed")
    result = source.replace(OLD_TITLE, NEW_TITLE, 1).replace(OLD_HINT, NEW_HINT, 1)
    # A sleep-screen copy edit must not touch power, suspend, redraw or input.
    if result.replace(NEW_TITLE, OLD_TITLE, 1).replace(NEW_HINT, OLD_HINT, 1) != source:
        raise ValueError("Sleep screen patch changed unexpected bytes")
    return result
