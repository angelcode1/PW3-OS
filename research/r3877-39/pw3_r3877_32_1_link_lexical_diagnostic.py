#!/usr/bin/env python3
"""R3877.32.1: locate a lexical parse failure in one hash-pinned public link line.

Host-only analysis. Never executes, evaluates, rewrites, expands, or prints the
original command; paths, macros and shell script content stay on the Mac.
A lexical prefix is NOT a complete or proven historical link invocation.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shlex

import pw3_r3877_31_buildlog_audit as prior
import pw3_r3877_32_log_command_shapes as earlier

MILESTONE = 'R3877.32.1'
EXPECTED_LINK_LINE_NUMBER = 1666
EXPECTED_LINK_LINE_SHA256 = '1082a4442e1edcdcdedcda614abceae9d08961b69bd7bb0c09c2010dbefe6dcd'
MAX_LINE_CHARS = 15000
MAX_TOKENS = 2048
MAX_REPORTED_FLAGS = 32
ABI_PREFIXES = ('-mfloat-abi=', '-mfpu=', '-march=', '-mabi=', '-mcpu=', '-mtune=')


def require(ok, name):
    if not ok:
        raise prior.AuditHold(name)


def _end_quote_state(s):
    """Deterministic lexical hint only, not an executable shell parser."""
    state = 'none'
    escaped = False
    for c in s:
        if escaped:
            escaped = False
        elif c == '\\' and state != 'single':
            escaped = True
        elif c == "'" and state == 'none':
            state = 'single'
        elif c == "'" and state == 'single':
            state = 'none'
        elif c == '"' and state == 'none':
            state = 'double'
        elif c == '"' and state == 'double':
            state = 'none'
    return state


def _tool_class(prefix):
    # Only the first 14 complete tokens are considered for a driver label.
    for token in prefix[:14]:
        if not earlier.TOOL_TOKEN.fullmatch(token):
            continue
        name = token.rsplit('/', 1)[-1].lower()
        m = earlier.DRIVER.fullmatch(name)
        if m:
            suffix = m.group(1).lower()
            return ('target-prefixed-' if suffix != name else '') + suffix
    return 'driver_unresolved'


def summarize_link(s):
    require(isinstance(s, str) and len(s) <= MAX_LINE_CHARS, 'LINK_TEXT_INVALID_OR_TOO_LONG')
    # shlex only lexes strings. It does not execute substitutions or shell commands.
    lexer = shlex.shlex(io.StringIO(s), posix=True)
    lexer.whitespace_split = True
    lexer.commenters = ''
    tokens = []
    failure = False
    for _ in range(MAX_TOKENS + 1):
        try:
            tok = lexer.get_token()
        except ValueError:
            failure = True
            break
        if tok == lexer.eof:
            break
        tokens.append(tok)
    else:
        raise prior.AuditHold('LINK_TOO_MANY_TOKENS')
    require(len(tokens) <= MAX_TOKENS, 'LINK_TOO_MANY_TOKENS')
    quote = _end_quote_state(s)
    # If a quoting error occurred, prefix-derived flags are explicitly partial.
    if failure:
        lex_status = ('UNTERMINATED_' + quote.upper() + '_QUOTE'
                      if quote in ('single', 'double') else 'SHELL_TOKENIZATION_ERROR')
    else:
        lex_status = 'TOKENIZED_WITH_SHLEX_NOT_SHELL_SEMANTICS'
    flags = sorted({t for t in tokens if earlier.SAFE_FLAG.fullmatch(t)})
    require(len(flags) <= MAX_REPORTED_FLAGS, 'TOO_MANY_ALLOWLISTED_FLAGS')
    # Textual matches are recorded separately from verified token boundaries.
    textual_flags = sorted({t for t in prior.OPT.findall(s) if earlier.SAFE_FLAG.fullmatch(t)})
    require(len(textual_flags) <= MAX_REPORTED_FLAGS, 'TOO_MANY_TEXTUAL_FLAGS')
    return {
        'lexical_result': lex_status,
        'end_quote_state': quote,
        'complete_shell_tokenization': not failure,
        'complete_prefix_token_count': len(tokens),
        'prefix_driver_class': _tool_class(tokens),
        'allowlisted_prefix_flags': flags,
        'allowlisted_textual_flags_unverified_as_tokens': textual_flags,
        'explicit_arm_abi_flags_in_prefix': [x for x in flags if x.startswith(ABI_PREFIXES)],
        'link_input_files_and_paths_not_emitted': True,
        'untrusted_command_substitutions_not_evaluated': True,
        'source_paths_disclosed': False,
        'raw_command_lines_disclosed': False,
        'full_link_invocation_verified': False,
    }


def analyze(raw, expected_hash=prior.EXPECTED_SHA256,
            expected_length=prior.EXPECTED_BYTES,
            expected_link_hash=EXPECTED_LINK_LINE_SHA256,
            expected_link_number=EXPECTED_LINK_LINE_NUMBER,
            expected_compile_count=1428):
    # R3877.32 re-verifies hash, exact file length and previous line counts.
    baseline = earlier.analyze(raw, expected_hash, expected_length)
    require(baseline['prior_r3877_31_counts_reconciled'], 'PRIOR_COUNTS_NOT_RECONCILED')
    require(baseline['likely_compile_line_count'] == expected_compile_count,
            'COMPILE_COUNT_CHANGED')
    require(baseline['likely_link_line_count'] == 1, 'LINK_COUNT_CHANGED')
    hashes = baseline['link_command_fingerprints']
    require(len(hashes) == 1 and hashes[0]['line_number'] == expected_link_number,
            'LINK_LINE_NUMBER_CHANGED')
    require(hashes[0]['printed_command_sha256'] == expected_link_hash,
            'LINK_COMMAND_FINGERPRINT_MISMATCH')
    lines = prior.ANSI.sub('', raw.decode('utf-8', 'replace')).splitlines()
    require(len(lines) >= expected_link_number, 'LINK_LINE_MISSING')
    line = lines[expected_link_number-1].strip()
    require(hashlib.sha256(line.encode()).hexdigest() == expected_link_hash,
            'LINK_COMMAND_FINGERPRINT_MISMATCH')
    result = summarize_link(line)
    result.update({
        'log_sha256': expected_hash,
        'log_bytes': len(raw),
        'prior_r3877_32_counts_reconciled': True,
        'target_link_line_number': expected_link_number,
        'target_printed_link_sha256': expected_link_hash,
        'printed_log_not_authenticated_or_runtime_attested': True,
        'historical_builder_linker_binary_and_version_verified': False,
        'historical_builder_complete_CFLAGS_LDFLAGS_verified': False,
        'source_to_binary_reproducibility_verified': False,
    })
    return result


def base():
    o = earlier.base()
    o.update(milestone=MILESTONE, result='HOLD',
             historical_builder_complete_link_invocation_verified=False,
             historical_builder_toolchain_versions_verified=False,
             source_to_binary_reproducibility_verified=False,
             binary_execution_performed=False)
    return o


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('log', help='Mac-local R3877.30 musl-armv7-build.log')
    args = p.parse_args(argv)
    result = base(); rc = 2
    try:
        path = Path(args.log)
        require(path.is_file() and not path.is_symlink(), 'LOG_FILE_MISSING_OR_SYMLINK')
        with path.open('rb') as f:
            raw = f.read(prior.MAX_BYTES + 1)
        result['inventory'] = analyze(raw)
        result['result'] = 'PASS_PINNED_LINK_LEXICAL_DIAGNOSTIC_ONLY'
        rc = 0
    except prior.AuditHold as e:
        result['hold_category'] = str(e)
    except (OSError, ValueError, UnicodeError):
        result['hold_category'] = 'LOG_ANALYSIS_ERROR'
    print(json.dumps(result, sort_keys=True, indent=2))
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
