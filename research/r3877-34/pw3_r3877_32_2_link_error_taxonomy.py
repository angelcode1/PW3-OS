#!/usr/bin/env python3
"""R3877.32.2: pinned public Alpine log linker lexer failure classification.

Strictly read-only Mac host diagnostic; uses shlex lexing ONLY. Never evaluates
shell, executes binary, joins command continuation, writes to Kindle, or outputs
untrusted text / paths. A public build log is not an attested builder record.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shlex

import pw3_r3877_31_buildlog_audit as prior
import pw3_r3877_32_1_link_lexical_diagnostic as earlier

MILESTONE = 'R3877.32.2'


def require(test, reason):
    if not test:
        raise prior.AuditHold(reason)


def lexical_failure_kind(error):
    """No raw exception strings can enter a user-facing result."""
    if isinstance(error, ValueError):
        if str(error) == 'No escaped character':
            return 'ESCAPE_AT_END_OF_PRINTED_LINE'
        if str(error) == 'No closing quotation':
            return 'UNTERMINATED_QUOTED_TOKEN'
    return 'OTHER_LEXER_ERROR'


def trace_lexer(s):
    require(isinstance(s, str) and len(s) <= earlier.MAX_LINE_CHARS,
            'LINK_TEXT_INVALID_OR_TOO_LONG')
    lex = shlex.shlex(io.StringIO(s), posix=True)
    lex.whitespace_split = True
    lex.commenters = ''
    count = 0
    failure = None
    failure_char_offset = None
    for _ in range(earlier.MAX_TOKENS + 1):
        try:
            token = lex.get_token()
        except ValueError as exc:
            failure = lexical_failure_kind(exc)
            failure_char_offset = lex.instream.tell()
            break
        if token == lex.eof:
            break
        count += 1
    else:
        raise prior.AuditHold('LINK_TOO_MANY_TOKENS')
    return {
        'error_kind': failure or 'NO_LEXICAL_ERROR',
        'lexer_stopped_at_character_offset': failure_char_offset,
        'printed_line_character_count': len(s),
        'complete_prefix_tokens_before_error': count,
        'printed_line_ends_with_unpaired_backslash': bool(
            (len(s) - len(s.rstrip('\\'))) % 2),
        'printed_line_ends_with_backslash': s.endswith('\\'),
        'end_quote_state': earlier._end_quote_state(s),
        'printed_command_complete_and_executable': False,
    }


def analyze(raw, *, expected_hash=prior.EXPECTED_SHA256,
            expected_length=prior.EXPECTED_BYTES,
            expected_link_hash=earlier.EXPECTED_LINK_LINE_SHA256,
            expected_link_number=earlier.EXPECTED_LINK_LINE_NUMBER):
    # All earlier baseline and per-line pins must pass again.
    baseline = earlier.analyze(raw, expected_hash, expected_length,
                               expected_link_hash, expected_link_number)
    lines = prior.ANSI.sub('', raw.decode('utf-8', 'replace')).splitlines()
    require(0 < expected_link_number <= len(lines), 'LINK_LINE_MISSING')
    s = lines[expected_link_number-1].strip()
    require(hashlib.sha256(s.encode()).hexdigest() == expected_link_hash,
            'LINK_COMMAND_FINGERPRINT_MISMATCH')
    details = trace_lexer(s)
    require(details['complete_prefix_tokens_before_error'] == baseline['complete_prefix_token_count'],
            'LEXER_PREFIX_TOKENS_CHANGED')
    require(details['end_quote_state'] == baseline['end_quote_state'],
            'END_QUOTE_STATE_CHANGED')
    require(details['error_kind'] != 'NO_LEXICAL_ERROR' or baseline['complete_shell_tokenization'],
            'LEXICAL_RESULT_INCONSISTENT')
    require(details['error_kind'] == 'NO_LEXICAL_ERROR' or not baseline['complete_shell_tokenization'],
            'LEXICAL_RESULT_INCONSISTENT')
    return {
        'log_bytes': len(raw),
        'log_sha256': hashlib.sha256(raw).hexdigest(),
        'log_sha256_verified': True,
        'link_line_number': expected_link_number,
        'link_line_sha256': expected_link_hash,
        'link_line_sha256_verified': True,
        'prefix_driver_class': baseline['prefix_driver_class'],
        'allowlisted_prefix_flags': baseline['allowlisted_prefix_flags'],
        'previous_lexical_status': baseline['lexical_result'],
        'prior_r3877_32_1_reconciled': True,
        **details,
        'line_may_be_log_fragment_not_an_argv': True,
        'untrusted_shell_substitutions_evaluated': False,
        'raw_command_lines_disclosed': False,
        'source_paths_disclosed': False,
        'historical_builder_complete_link_invocation_verified': False,
        'historical_builder_cflags_ldflags_verified': False,
        'historical_builder_toolchain_versions_verified': False,
        'source_to_binary_reproducibility_verified': False,
    }


def base():
    o = earlier.base()
    o.update(
        milestone=MILESTONE, result='HOLD',
        historical_builder_complete_link_invocation_verified=False,
        historical_builder_cflags_ldflags_verified=False,
        source_to_binary_reproducibility_verified=False,
        binary_execution_performed=False,
        kindle_ssh_sessions=0,
        firmware_write_performed=False,
        immutable_hold='NOT_BOOTABLE',
    )
    return o


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('log', help='Existing Mac-local R3877.30 public build log')
    a = p.parse_args(argv)
    result = base()
    rc = 2
    try:
        path = Path(a.log)
        require(path.is_file() and not path.is_symlink(),
                'LOG_FILE_MISSING_OR_SYMLINK')
        with path.open('rb') as f:
            raw = f.read(prior.MAX_BYTES + 1)
        result['inventory'] = analyze(raw)
        result['result'] = 'PASS_PINNED_LINK_LEXER_ERROR_TAXONOMY_ONLY'
        rc = 0
    except prior.AuditHold as e:
        result['hold_category'] = str(e)
    except (OSError, ValueError, UnicodeError, OverflowError):
        result['hold_category'] = 'LOG_ANALYSIS_ERROR'
    print(json.dumps(result, indent=2, sort_keys=True))
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
