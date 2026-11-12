"""Adapt pinned upstream home branding without changing its rotating footer phrases."""
import re

def patch_codex_home(source: str) -> str:
    source = re.sub(r'(?i)inkwell', 'Codex', source)
    # Preserve the upstream footers verbatim until the user supplies new phrases.
    if 'static const char *const footers[]' not in source:
        raise ValueError('upstream home footer table changed')
    if 'for (const char *p = "INKWELL"' in source:
        raise ValueError('original wordmark remains')
    return source
